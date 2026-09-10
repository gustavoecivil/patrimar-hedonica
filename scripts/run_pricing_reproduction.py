#!/usr/bin/env python3
"""Executa scripts/pricing_reproduction_engine.py contra o schema v2
real (`core`/`pricing`/`raw`/`staging`), a partir de um ruleset privado
fornecido por argumento (Fase 3C).

Nenhuma fórmula, constante ou valor privado está neste arquivo — ele
só sabe: onde buscar cada tipo de insumo declarado em `ruleset.inputs`
(coluna de `core.units`, célula de `raw.cells` por linha de origem, ou
`pricing.parameters`/`pricing.calibration_entries`), como montar a
tabela de calibração a injetar em tempo de execução, e como persistir
o resultado — sempre distinguindo `REPRODUCED_PRICE`
(`result_origin='SYSTEM_CALCULATED'`) de `SOURCE_REFERENCE_PRICE`
(`result_origin='IMPORTED_REFERENCE'`, Fase 3B, NUNCA sobrescrito).

Separação estrutural CALCULATION vs. VALIDATION (Passo 12): a função
`load_calculation_inputs()` só lê `core.*`/`pricing.parameters`/
`pricing.calibration_entries`/`raw.cells` — nunca
`pricing.unit_price_results`. Só depois que `ReproductionEngine.compute()`
já retornou é que `load_source_reference_prices()` é chamada. Nenhuma
variável do resultado do cálculo é usada para decidir o que buscar na
referência (e vice-versa).

Modos: --mode dry-run (conta candidatos, não escreve), --mode summary
(relatório read-only), --mode apply (calcula, persiste, compara).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest_xlsx_postgres as ing  # noqa: E402
import pricing_reproduction_engine as engine_mod  # noqa: E402

sql_str = ing.sql_str
sql_num = ing.sql_num


def ruleset_version_of(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest[:16]}"


def fetch_developments(psql_bin: str) -> list[dict]:
    return ing.run_query_csv(psql_bin, "SELECT id, business_key FROM core.developments ORDER BY business_key;")


def fetch_units_with_lineage(psql_bin: str, development_id: str) -> list[dict]:
    return ing.run_query_csv(
        psql_bin,
        "SELECT u.id AS unit_id, u.unit_code, u.closed_area_m2, u.open_terrace_area_m2, u.position_code, "
        "t.business_key AS tower_key, "
        "sc.source_workbook_id, sc.source_sheet_id, sc.source_row "
        "FROM core.units u JOIN staging.unit_candidates sc ON sc.promoted_entity_id = u.id "
        "LEFT JOIN core.towers t ON t.id = u.tower_id "
        f"WHERE u.development_id = {sql_str(development_id)} ORDER BY sc.source_row;",
    )


def fetch_raw_columns_by_row(psql_bin: str, sheet_id: str, columns: list[str]) -> dict[int, dict[str, str]]:
    # Escopado por sheet_id (nunca só workbook_id): um workbook tem várias
    # abas, e a mesma letra de coluna (ex.: "H") existe em mais de uma aba
    # com conteúdo completamente diferente — filtrar só por workbook_id
    # misturava linhas de abas distintas sob a mesma chave row_number,
    # produzindo valores "implausíveis" que na verdade vinham de outra aba
    # (achado real da Fase 3D, corrigindo uma conclusão errada da Fase 3C).
    col_list = ", ".join(sql_str(c) for c in columns)
    rows = ing.run_query_csv(
        psql_bin,
        "SELECT rc.row_number, rc.column_letters, COALESCE(rc.raw_value, rc.cached_value) AS value_text "
        "FROM raw.cells rc "
        f"WHERE rc.sheet_id = {sql_str(sheet_id)} AND rc.column_letters IN ({col_list});",
    )
    by_row: dict[int, dict[str, str]] = {}
    for r in rows:
        by_row.setdefault(int(r["row_number"]), {})[r["column_letters"]] = r["value_text"]
    return by_row


def fetch_parameters(psql_bin: str, development_id: str) -> dict[str, str]:
    rows = ing.run_query_csv(
        psql_bin,
        "SELECT p.key, p.numeric_value FROM pricing.parameters p "
        "JOIN pricing.parameter_sets ps ON ps.id = p.parameter_set_id "
        "JOIN pricing.scenarios sc ON sc.id = ps.scenario_id "
        f"WHERE sc.development_id = {sql_str(development_id)};",
    )
    return {r["key"]: r["numeric_value"] for r in rows}


def fetch_calibration_table(psql_bin: str, development_id: str, dimension: str) -> dict[str, str]:
    rows = ing.run_query_csv(
        psql_bin,
        "SELECT ce.category_key, ce.factor FROM pricing.calibration_entries ce "
        "JOIN pricing.calibration_sets cs ON cs.id = ce.calibration_set_id "
        "JOIN pricing.scenarios sc ON sc.id = cs.scenario_id "
        f"WHERE sc.development_id = {sql_str(development_id)} AND cs.code = {sql_str(dimension)};",
    )
    return {r["category_key"]: r["factor"] for r in rows}


HLOOKUP_RE = re.compile(
    r"HLOOKUP\([^,]+,\s*'?([^'!]+)'?!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)\s*,\s*'?([^'!]+)'?!\$([A-Z]+)\$(\d+)",
)


def fetch_composite_lookup_table_from_formula(
    psql_bin: str, workbook_id: str, formula_sheet: str, formula_column: str, anchor_row: int,
) -> dict[str, str] | None:
    """Reconstrói genericamente uma tabela de busca (chave->fator) a
    partir de uma fórmula HLOOKUP real, sem conhecer de antemão nem a
    aba nem o range nem a célula de índice — tudo isso é PARSEADO da
    própria fórmula (evidência DIRECT, Fase 3D Passo 3/12), nunca
    hardcoded. `formula_sheet`/`formula_column`/`anchor_row` (onde ler a
    fórmula original) vêm do ruleset privado, nunca deste código.

    Reaproveita o mesmo padrão já comprovado para o índice de linha do
    VLOOKUP de pavimento (Fase 3A): a célula de índice costuma ser uma
    fórmula auto-documentada (`ROWS(...)`/`COLUMNS(...)`) que sempre
    resolve para a borda do range — por isso a linha/coluna de fator é
    sempre recalculada a partir do range + índice, nunca fixada."""
    formula_rows = ing.run_query_csv(
        psql_bin,
        "SELECT rc.formula_expression FROM raw.cells rc JOIN raw.sheets s ON s.id=rc.sheet_id "
        f"WHERE s.workbook_id={sql_str(workbook_id)} AND s.sheet_name={sql_str(formula_sheet)} "
        f"AND rc.column_letters={sql_str(formula_column)} AND rc.row_number={sql_num(anchor_row)};",
    )
    if not formula_rows or not formula_rows[0].get("formula_expression"):
        return None
    m = HLOOKUP_RE.search(formula_rows[0]["formula_expression"])
    if not m:
        return None
    range_sheet, col_a, row_a, col_b, row_b, idx_sheet, idx_col, idx_row = m.groups()
    row_a, row_b, idx_row = int(row_a), int(row_b), int(idx_row)

    idx_cell_rows = ing.run_query_csv(
        psql_bin,
        "SELECT COALESCE(raw_value, cached_value) AS value_text FROM raw.cells rc "
        "JOIN raw.sheets s ON s.id=rc.sheet_id "
        f"WHERE s.workbook_id={sql_str(workbook_id)} AND s.sheet_name={sql_str(idx_sheet)} "
        f"AND rc.column_letters={sql_str(idx_col)} AND rc.row_number={sql_num(idx_row)};",
    )
    if not idx_cell_rows or not idx_cell_rows[0]["value_text"]:
        return None
    row_index = int(float(idx_cell_rows[0]["value_text"]))
    factor_row = row_a + row_index - 1

    col_start = ing.ax.col_letters_to_index(col_a)
    col_end = ing.ax.col_letters_to_index(col_b)
    grid_rows = ing.run_query_csv(
        psql_bin,
        "SELECT rc.row_number, rc.column_letters, rc.column_index, "
        "COALESCE(rc.raw_value, rc.cached_value) AS value_text FROM raw.cells rc "
        "JOIN raw.sheets s ON s.id=rc.sheet_id "
        f"WHERE s.workbook_id={sql_str(workbook_id)} AND s.sheet_name={sql_str(range_sheet)} "
        f"AND rc.row_number IN ({sql_num(row_a)}, {sql_num(factor_row)}) "
        f"AND rc.column_index BETWEEN {sql_num(col_start)} AND {sql_num(col_end)};",
    )
    header_by_col, factor_by_col = {}, {}
    for r in grid_rows:
        rn = int(r["row_number"])
        if rn == row_a:
            header_by_col[r["column_letters"]] = r["value_text"]
        elif rn == factor_row:
            factor_by_col[r["column_letters"]] = r["value_text"]

    table = {}
    for col, key in header_by_col.items():
        if key and col in factor_by_col and factor_by_col[col] not in (None, ""):
            table[key] = factor_by_col[col]
    return table or None


def _numeric_or_none(text: str | None) -> str | None:
    """Retorna o texto original se ele parece um numero (para o motor
    converter em Decimal), ou None se for vazio/nao-numerico -- nunca
    assume que texto nao-numerico significa zero (achado real desta
    fase: algumas linhas da area de dados contem rotulos de secao em
    vez de valor de area, ver reproduction-run-summary.md)."""
    if text is None or text == "":
        return None
    try:
        float(text)
    except ValueError:
        return None
    return text


def load_calculation_inputs(psql_bin: str, development_id: str, ruleset: engine_mod.Ruleset,
                             variant: str) -> tuple[list[dict], dict]:
    """FASE DE CALCULO. Nunca consulta pricing.unit_price_results nem
    qualquer tabela de comparação/referência."""
    unit_rows = fetch_units_with_lineage(psql_bin, development_id)
    params = fetch_parameters(psql_bin, development_id)
    dev_business_key = next((d["business_key"] for d in fetch_developments(psql_bin) if d["id"] == development_id), None)

    h_i_confirmation = ruleset.data.get("development_column_confirmations", {}).get(
        "balcony_and_ancillary_area_columns_H_I", {})
    h_i_confirmed = dev_business_key in h_i_confirmation.get("confirmed_for_business_keys", [])

    implicit_tower_keys = ruleset.data.get("implicit_tower_key_by_development", {})
    implicit_tower_key = implicit_tower_keys.get(dev_business_key)

    by_sheet: dict[str, dict[int, dict[str, str]]] = {}
    units: list[dict] = []
    non_numeric_h_i = 0
    for u in unit_rows:
        sheet_id = u["source_sheet_id"]
        if sheet_id not in by_sheet:
            by_sheet[sheet_id] = fetch_raw_columns_by_row(psql_bin, sheet_id, ["H", "I", "AB"])
        row_cells = by_sheet[sheet_id].get(int(u["source_row"]), {})
        if h_i_confirmed:
            balcony = _numeric_or_none(row_cells.get("H"))
            ancillary = _numeric_or_none(row_cells.get("I"))
            if row_cells.get("H") not in (None, "") and balcony is None:
                non_numeric_h_i += 1
            if row_cells.get("I") not in (None, "") and ancillary is None:
                non_numeric_h_i += 1
        else:
            # cabecalho de H/I nao confirmado para este desenvolvimento (ver
            # development_column_confirmations no ruleset) -- nunca usado no
            # calculo, mesmo que a celula tenha um valor numerico aparente.
            balcony, ancillary = None, None
        override_raw = row_cells.get("AB")
        override_val = _numeric_or_none(override_raw)
        units.append({
            "unit_id": u["unit_id"],
            "group_id": development_id,
            "closed_area": u["closed_area_m2"],
            "terrace_area": u["open_terrace_area_m2"],
            "balcony_area_derived": balcony,
            "ancillary_area_derived": ancillary,
            "unit_code_raw": u["unit_code"],
            "position_code_raw": u["position_code"],
            "tower_key_raw": u["tower_key"] if u.get("tower_key") not in (None, "") else implicit_tower_key,
            "UNCOVERED_AREA_FACTOR": params.get("UNCOVERED_AREA_FACTOR"),
            "TARGET_PRICE_PER_M2": params.get("TARGET_PRICE_PER_M2"),
            "override_amount_derived": override_val if override_val is not None else ("0" if override_raw in (None, "") else None),
            "_source_row": int(u["source_row"]),
        })

    floor_table = fetch_calibration_table(psql_bin, development_id, "FLOOR")
    ruleset.rules["floor_factor"]["operands"]["table"] = floor_table
    floor_defaults = ruleset.data.get("floor_missing_key_defaults_by_development", {})
    ruleset.rules["floor_factor"]["operands"]["missing_key_defaults"] = floor_defaults.get(dev_business_key, {})

    position_rule = ruleset.rules.get("position_factor", {})
    formula_source = position_rule.get("formula_source")
    if formula_source and position_rule.get("status") == "ACTIVE" and unit_rows:
        position_table = fetch_composite_lookup_table_from_formula(
            psql_bin, unit_rows[0]["source_workbook_id"],
            formula_source["sheet"], formula_source["column"], int(unit_rows[0]["source_row"]),
        )
        position_rule["operands"]["table"] = position_table or {}

    anomaly = ruleset.rules["floor_factor"].get("anomaly_pr018")
    row_overrides: dict[str, str] = {}
    if anomaly and variant == "as_implemented_in_source" and dev_business_key == anomaly["affected_development_business_key"]:
        affected_rows = set(anomaly["affected_source_rows"])
        forced_key = anomaly["forced_category_key"]
        for u in units:
            if u["_source_row"] in affected_rows:
                row_overrides[u["unit_id"]] = forced_key
    ruleset.rules["floor_factor"]["operands"]["row_key_overrides"] = row_overrides

    meta = {"dev_business_key": dev_business_key, "anomaly_rows_overridden": len(row_overrides),
            "parameters_used": params, "non_numeric_h_i_cells": non_numeric_h_i, "h_i_confirmed": h_i_confirmed}
    return units, meta


def load_source_reference_prices(psql_bin: str, development_id: str) -> dict[str, dict]:
    """FASE DE VALIDACAO — só chamada DEPOIS do cálculo já ter sido
    produzido. Nunca lida antes nem durante o cálculo."""
    rows = ing.run_query_csv(
        psql_bin,
        "SELECT upr.unit_id, upr.system_calculated_price, upr.system_calculated_price_per_m2, upr.run_id "
        "FROM pricing.unit_price_results upr "
        "JOIN pricing.runs r ON r.id = upr.run_id "
        "JOIN pricing.scenarios sc ON sc.id = r.scenario_id "
        f"WHERE sc.development_id = {sql_str(development_id)} AND upr.result_origin = 'IMPORTED_REFERENCE';",
    )
    return {r["unit_id"]: r for r in rows}


def classify_match(delta_abs: Decimal | None, delta_pct: Decimal | None) -> str:
    if delta_abs is None:
        return "BLOCKED"
    if delta_abs == 0:
        return "EXACT"
    if abs(delta_abs) <= Decimal("0.01"):
        return "WITHIN_1_CENT"
    if abs(delta_abs) <= Decimal("1.00"):
        return "WITHIN_1_REAL"
    if delta_pct is not None and abs(delta_pct) <= Decimal("0.0001"):
        return "WITHIN_0_01_PERCENT"
    return "DIVERGENT"


def cmd_dry_run(args) -> int:
    psql_bin = ing.find_psql()
    ruleset_path = Path(args.ruleset)
    ruleset = engine_mod.Ruleset.from_file(str(ruleset_path))
    print("=== DRY RUN — nenhuma escrita no banco ===")
    print(f"ruleset_version={ruleset_version_of(ruleset_path)} variant={args.variant}")
    for dev in fetch_developments(psql_bin):
        units, meta = load_calculation_inputs(psql_bin, dev["id"], ruleset, args.variant)
        print(f"development={dev['business_key']} units={len(units)} "
              f"anomaly_rows_overridden={meta['anomaly_rows_overridden']} "
              f"parameters_available={sorted(meta['parameters_used'].keys())}")
    return 0


def cmd_summary(args) -> int:
    psql_bin = ing.find_psql()
    rows = ing.run_query_csv(
        psql_bin,
        "SELECT match_classification, count(*) AS n FROM pricing.reproduction_comparisons "
        "GROUP BY match_classification ORDER BY 1;",
    )
    for r in rows:
        print(f"match_classification={r['match_classification']} n={r['n']}")
    if not rows:
        print("nenhuma comparacao de reproducao registrada ainda")
    return 0


def cmd_apply(args) -> int:
    psql_bin = ing.find_psql()
    ruleset_path = Path(args.ruleset)
    ruleset_version = ruleset_version_of(ruleset_path)

    overall_counts = {"units_total": 0, "units_calculated": 0, "units_blocked": 0}

    for dev in fetch_developments(psql_bin):
        development_id = dev["id"]

        existing = ing.run_query_csv(
            psql_bin,
            f"SELECT id, status FROM audit.reproduction_runs WHERE development_id={sql_str(development_id)} "
            f"AND ruleset_version={sql_str(ruleset_version)};",
        )
        if existing and existing[0]["status"] == "COMPLETED":
            print(f"ALREADY_REPRODUCED development={dev['business_key']} ruleset_version={ruleset_version}")
            continue

        ruleset = engine_mod.Ruleset.from_file(str(ruleset_path))
        units, meta = load_calculation_inputs(psql_bin, development_id, ruleset, args.variant)

        # ---- FASE DE CALCULO (sem qualquer leitura de referencia) ----
        engine = engine_mod.ReproductionEngine(ruleset)
        result = engine.compute(units)

        if existing:
            reproduction_id = existing[0]["id"]
            ing.run_query_csv(
                psql_bin,
                f"UPDATE audit.reproduction_runs SET status='RUNNING', started_at=now(), completed_at=NULL "
                f"WHERE id={sql_str(reproduction_id)};",
            )
        else:
            rows = ing.run_query_csv(
                psql_bin,
                "INSERT INTO audit.reproduction_runs (id, development_id, ruleset_version, mapping_version, status, started_at) "
                f"VALUES (gen_random_uuid(), {sql_str(development_id)}, {sql_str(ruleset_version)}, "
                f"{sql_str(args.mapping_version)}, 'RUNNING', now()) RETURNING id;",
            )
            reproduction_id = rows[0]["id"]

        run_code = f"REPRODUCTION-{args.variant.upper()}-{ruleset_version.split(':')[-1]}"
        scenario_sub = (f"(SELECT id FROM pricing.scenarios WHERE development_id={sql_str(development_id)} "
                         f"AND code='IMPORTED_REFERENCE')")
        run_sub = (f"(SELECT id FROM pricing.runs WHERE scenario_id={scenario_sub} "
                   f"AND run_type='REPRODUCTION_VALIDATION_RUN' AND code={sql_str(run_code)})")

        lines = ["BEGIN;"]
        lines.append(
            "INSERT INTO pricing.runs (id, scenario_id, parameter_set_id, code, status, run_type, engine_version, "
            "started_at, completed_at) "
            f"SELECT gen_random_uuid(), {scenario_sub}, "
            f"(SELECT id FROM pricing.parameter_sets WHERE scenario_id={scenario_sub} "
            f"AND code='IMPORTED_PARAMETERS'), "
            f"{sql_str(run_code)}, 'COMPLETED', 'REPRODUCTION_VALIDATION_RUN', "
            f"{sql_str('pricing_reproduction_engine/' + args.variant)}, now(), now() "
            f"WHERE NOT EXISTS (SELECT 1 FROM pricing.runs WHERE scenario_id={scenario_sub} "
            f"AND run_type='REPRODUCTION_VALIDATION_RUN' AND code={sql_str(run_code)});"
        )

        seq = 1
        for u in units:
            uid = u["unit_id"]
            row = result["per_unit"].get(uid, {})
            for var_name, adj_type in (("total_area", "PR-002_TOTAL_AREA"),
                                        ("weighted_area", "PR-004_WEIGHTED_AREA"),
                                        ("floor_factor", "PR-005_FLOOR_FACTOR")):
                val = row.get(var_name)
                if val is None:
                    continue
                lines.append(
                    "INSERT INTO pricing.unit_adjustments (run_id, unit_id, adjustment_type, result_value, "
                    "sequence_order) VALUES ("
                    f"{run_sub}, {sql_str(uid)}, {sql_str(adj_type)}, {sql_num(val)}, {seq});"
                )
            seq += 1

        # ---- FASE DE VALIDACAO (só agora a referencia é lida) ----
        references = load_source_reference_prices(psql_bin, development_id)

        blocked, calculated = 0, 0
        for u in units:
            uid = u["unit_id"]
            row = result["per_unit"].get(uid, {})
            reproduced_price = row.get("unit_price")
            ref = references.get(uid)
            ref_price = to_dec(ref["system_calculated_price"]) if ref else None

            cause: str | None
            if reproduced_price is None:
                blocked += 1
                classification = "BLOCKED"
                delta_pct = None
                cause = "MISSING_PARAMETER"
            else:
                calculated += 1
                delta_abs = (reproduced_price - ref_price) if ref_price is not None else None
                delta_pct = (delta_abs / ref_price) if (delta_abs is not None and ref_price not in (None, 0)) else None
                classification = classify_match(delta_abs, delta_pct)
                cause = None if classification in ("EXACT", "WITHIN_1_CENT") else "UNKNOWN"

            delta_pct_sql = sql_num(str(delta_pct)) if delta_pct is not None else "NULL"
            cause_sql = sql_str(cause) if cause is not None else "NULL"

            lines.append(
                "INSERT INTO pricing.reproduction_comparisons "
                "(reproduction_run_id, imported_run_id, unit_id, source_reference_price, reproduced_price, "
                "delta_percent, match_classification, divergence_cause) VALUES ("
                f"{run_sub}, "
                f"{sql_str(ref['run_id']) if ref else 'NULL'}, {sql_str(uid)}, "
                f"{sql_num(ref['system_calculated_price']) if ref else 'NULL'}, "
                f"{sql_num(str(reproduced_price)) if reproduced_price is not None else 'NULL'}, "
                f"{delta_pct_sql}, {sql_str(classification)}, {cause_sql});"
            )

        lines.append(f"UPDATE audit.reproduction_runs SET status='COMPLETED', completed_at=now(), "
                      f"pricing_run_id={run_sub} WHERE id={sql_str(reproduction_id)};")
        lines.append("COMMIT;")

        tmp_sql = Path(args.sql_scratch) if args.sql_scratch else Path("_reproduce_tmp.sql")
        tmp_sql.write_text("\n".join(lines), encoding="utf-8")
        run_result = ing.run_sql_file(psql_bin, tmp_sql, single_transaction=False)
        if not args.keep_scratch:
            tmp_sql.unlink(missing_ok=True)

        if run_result.returncode != 0:
            print(f"FALHOU ao reproduzir development={dev['business_key']}", file=sys.stderr)
            print(run_result.stderr[-4000:], file=sys.stderr)
            ing.run_query_csv(
                psql_bin,
                f"UPDATE audit.reproduction_runs SET status='FAILED', completed_at=now() "
                f"WHERE id={sql_str(reproduction_id)};",
            )
            return 1

        print(f"OK development={dev['business_key']} units_total={len(units)} "
              f"calculated={calculated} blocked={blocked}")
        overall_counts["units_total"] += len(units)
        overall_counts["units_calculated"] += calculated
        overall_counts["units_blocked"] += blocked

    print(f"TOTAL: {overall_counts}")
    return 0


def to_dec(value) -> Decimal | None:
    return engine_mod.to_decimal(value)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["dry-run", "summary", "apply"], default="dry-run")
    parser.add_argument("--ruleset", help="caminho do ruleset privado (obrigatorio para dry-run/apply)")
    parser.add_argument("--variant", choices=["as_implemented_in_source", "consistent_rule_variant"],
                         default="as_implemented_in_source")
    parser.add_argument("--mapping-version", default="unspecified")
    parser.add_argument("--sql-scratch", default=None)
    parser.add_argument("--keep-scratch", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "summary":
        return cmd_summary(args)
    if not args.ruleset:
        parser.error("--ruleset e obrigatorio para --mode dry-run/apply")
    if args.mode == "dry-run":
        return cmd_dry_run(args)
    return cmd_apply(args)


if __name__ == "__main__":
    sys.exit(main())
