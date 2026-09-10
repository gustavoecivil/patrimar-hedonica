#!/usr/bin/env python3
"""Promoção controlada de staging.* (candidatos normalizados, Fase 3A)
para core.*/pricing.* (Fase 3B), no schema v2 do PostgreSQL
(database/v2/009_promotion.sql).

NUNCA calcula preço. Distingue explicitamente, no próprio dado
persistido, um resultado que já existia na fonte original
(`result_origin='IMPORTED_REFERENCE'`) de um resultado calculado por
uma execução real do motor de alocação (`SYSTEM_CALCULATED`) — ver
docs/15-STAGING-TO-CANONICAL-PROMOTION.md.

Promove SOMENTE candidatos com `mapping_confidence='HIGH'` e
`mapping_status='CANDIDATE'` — nunca `MEDIUM`/`LOW`, que permanecem
em `staging.mapping_review`.

Identidade da execução: (ingest_batch_id, mapping_version). Nenhum
outro batch é misturado silenciosamente. `mapping_version` é derivado
deterministicamente do conteúdo do arquivo de mapeamento (hash),
nunca de um número escolhido a mão — reproduzível a partir de
(source SHA implícito no batch) + ingest_batch + mapping_version.

Requisitos (mesmo padrão de scripts/ingest_xlsx_postgres.py): biblioteca
padrão + `psql` (sem psycopg2); sem nome/valor privado hardcoded; sem
caminho absoluto; conexão só por variável de ambiente padrão do libpq;
fail-fast; transação única para o bloco de escrita; dry-run;
idempotente; logs nunca imprimem valor de célula/candidato privado por
padrão.

Modos:
  --mode dry-run    conta o que SERIA promovido, não escreve nada.
  --mode summary    relatório read-only de progresso (promovido vs. pendente).
  --mode apply      promove de fato, numa única transação, com o
                     mesmo padrão de estado PENDING/RUNNING/COMPLETED/
                     FAILED usado na Fase 3A.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest_xlsx_postgres as ing  # noqa: E402

sql_str = ing.sql_str
sql_num = ing.sql_num


def mapping_version_of(mapping_path: Path) -> str:
    digest = hashlib.sha256(mapping_path.read_bytes()).hexdigest()
    return f"sha256:{digest[:16]}"


def business_key_for_workbook(source_sha256: str) -> str:
    return f"DEV-{source_sha256[:10].upper()}"


def fetch_batch_workbooks(psql_bin: str, batch_id: str) -> list[dict]:
    rows = ing.run_query_csv(
        psql_bin,
        f"SELECT id, source_sha256 FROM raw.workbooks WHERE ingest_batch_id='{batch_id}' ORDER BY ingested_at;",
    )
    return rows


def fetch_unpromoted(psql_bin: str, table: str, workbook_id: str) -> list[dict]:
    rows = ing.run_query_csv(
        psql_bin,
        f"SELECT * FROM staging.{table} WHERE source_workbook_id='{workbook_id}' "
        f"AND mapping_confidence='HIGH' AND mapping_status='CANDIDATE' AND promoted_entity_id IS NULL "
        f"ORDER BY id;",
    )
    return rows


def cmd_dry_run(args) -> int:
    psql_bin = ing.find_psql()
    workbooks = fetch_batch_workbooks(psql_bin, args.ingest_batch_id)
    if not workbooks:
        print(f"ERRO: nenhum workbook encontrado para ingest_batch_id={args.ingest_batch_id}", file=sys.stderr)
        return 2

    mapping_version = mapping_version_of(Path(args.mapping))
    print("=== DRY RUN — nenhuma escrita no banco ===")
    print(f"ingest_batch_id={args.ingest_batch_id} mapping_version={mapping_version}")

    already = ing.run_query_csv(
        psql_bin,
        f"SELECT status FROM audit.promotion_runs WHERE ingest_batch_id='{args.ingest_batch_id}' "
        f"AND mapping_version='{mapping_version}';",
    )
    if already and already[0]["status"] == "COMPLETED":
        print("ALREADY_PROMOTED (esta combinação de ingest_batch + mapping_version já foi promovida)")

    total = {"units": 0, "parameters": 0, "calibrations": 0, "price_outputs": 0}
    for wb in workbooks:
        bk = business_key_for_workbook(wb["source_sha256"])
        units = fetch_unpromoted(psql_bin, "unit_candidates", wb["id"])
        params = fetch_unpromoted(psql_bin, "parameter_candidates", wb["id"])
        calibs = fetch_unpromoted(psql_bin, "calibration_candidates", wb["id"])
        prices = fetch_unpromoted(psql_bin, "price_output_candidates", wb["id"])
        print(f"workbook business_key={bk} units_candidatos_pendentes={len(units)} "
              f"parameters_pendentes={len(params)} calibrations_pendentes={len(calibs)} "
              f"price_outputs_pendentes={len(prices)}")
        total["units"] += len(units)
        total["parameters"] += len(params)
        total["calibrations"] += len(calibs)
        total["price_outputs"] += len(prices)
    print(f"TOTAL a promover nesta execução: units={total['units']} parameters={total['parameters']} "
          f"calibrations={total['calibrations']} price_outputs={total['price_outputs']}")
    return 0


def cmd_summary(args) -> int:
    psql_bin = ing.find_psql()
    for table, entity in [
        ("unit_candidates", "core.units"),
        ("parameter_candidates", "pricing.parameters"),
        ("calibration_candidates", "pricing.calibration_entries"),
        ("price_output_candidates", "pricing.unit_price_results (IMPORTED_REFERENCE)"),
    ]:
        rows = ing.run_query_csv(
            psql_bin,
            f"SELECT "
            f"count(*) AS total, "
            f"count(*) FILTER (WHERE mapping_confidence='HIGH' AND mapping_status='CANDIDATE') AS high_candidate, "
            f"count(*) FILTER (WHERE promoted_entity_id IS NOT NULL) AS promoted "
            f"FROM staging.{table};",
        )
        r = rows[0]
        print(f"{table} -> {entity}: total={r['total']} high_candidate={r['high_candidate']} promoted={r['promoted']}")
    review = ing.run_query_csv(
        psql_bin,
        "SELECT confidence, status, count(*) AS n FROM staging.mapping_review GROUP BY confidence, status ORDER BY 1,2;",
    )
    for r in review:
        print(f"mapping_review confidence={r['confidence']} status={r['status']} n={r['n']}")
    return 0


def emit_units(lines: list[str], psql_bin: str, wb: dict, dev_bk: str) -> tuple[int, list[str]]:
    candidates = fetch_unpromoted(psql_bin, "unit_candidates", wb["id"])
    if not candidates:
        return 0, []

    seen_keys = set()
    for c in candidates:
        key = (c.get("tower_ref") or "", c["unit_ref"])
        if key in seen_keys:
            raise RuntimeError(
                f"colisão de identidade detectada (tower_ref+unit_ref duplicado) para workbook {dev_bk} — "
                f"abortando promoção desta execução, nenhuma unidade duplicada será criada."
            )
        seen_keys.add(key)

    towers = sorted({c["tower_ref"] for c in candidates if c.get("tower_ref")})
    typologies = sorted({c["typology_ref"] for c in candidates if c.get("typology_ref")})

    for t in towers:
        lines.append(
            "INSERT INTO core.towers (development_id, business_key) "
            f"SELECT (SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}), {sql_str(t)} "
            "WHERE NOT EXISTS (SELECT 1 FROM core.towers tw "
            f"WHERE tw.development_id=(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) "
            f"AND tw.business_key={sql_str(t)});"
        )
    for ty in typologies:
        lines.append(
            "INSERT INTO core.unit_typologies (development_id, business_key, classification) "
            f"SELECT (SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}), {sql_str(ty)}, "
            "'OFFICIAL_TYPOLOGY' "
            "WHERE NOT EXISTS (SELECT 1 FROM core.unit_typologies ut "
            f"WHERE ut.development_id=(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) "
            f"AND ut.business_key={sql_str(ty)});"
        )

    promoted_ids_sql: list[str] = []
    for c in candidates:
        tower_sub = (
            f"(SELECT id FROM core.towers WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) "
            f"AND business_key={sql_str(c['tower_ref'])})"
            if c.get("tower_ref") else "NULL"
        )
        typology_sub = (
            f"(SELECT id FROM core.unit_typologies WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) "
            f"AND business_key={sql_str(c['typology_ref'])})"
            if c.get("typology_ref") else "NULL"
        )
        new_id_expr = "gen_random_uuid()"
        lines.append(f"WITH ins AS (INSERT INTO core.units "
                      "(id, development_id, tower_id, unit_typology_id, unit_code, position_code, "
                      "closed_area_m2, open_terrace_area_m2) VALUES ("
                      f"{new_id_expr}, (SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}), "
                      f"{tower_sub}, {typology_sub}, {sql_str(c['unit_ref'])}, {sql_str(c.get('position_ref'))}, "
                      f"{sql_num(c.get('private_area')) if c.get('private_area') not in (None, '') else '0'}, "
                      f"{sql_num(c.get('uncovered_area')) if c.get('uncovered_area') not in (None, '') else '0'}) "
                      "RETURNING id) "
                      f"UPDATE staging.unit_candidates SET promoted_entity_id=(SELECT id FROM ins), promoted_at=now() "
                      f"WHERE id={sql_str(c['id'])};")
        lines.append(
            "INSERT INTO audit.data_lineage (entity_schema, entity_table, entity_id, data_source_id, derived_from) "
            "SELECT 'core','units', promoted_entity_id, "
            f"(SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)}), "
            f"'staging.unit_candidates' FROM staging.unit_candidates WHERE id={sql_str(c['id'])};"
        )
    return len(candidates), [c["id"] for c in candidates]


def emit_parameters(lines: list[str], psql_bin: str, wb: dict, dev_bk: str) -> tuple[int, int]:
    all_candidates = fetch_unpromoted(psql_bin, "parameter_candidates", wb["id"])
    if not all_candidates:
        return 0, 0
    # Não promove CONFIRMED_PARAMETER sem valor lido de fato — um mapeamento
    # HIGH não garante que a célula, na prática, tenha valor não vazio
    # (achado real desta fase). "parâmetro sem definição clara" é um sinal
    # de qualidade esperado (Fase 3A), não um erro que deva abortar todo o
    # lote — o candidato permanece staged, não promovido, para revisão.
    candidates = [c for c in all_candidates if (c.get("value_text") or "").strip() != ""]
    skipped = len(all_candidates) - len(candidates)
    for c in candidates:
        value_type = c.get("value_type_guess") or "TEXT"
        if value_type == "NUMERIC":
            value_cols = f"{sql_num(c.get('value_text'))}, NULL, NULL, NULL"
        elif value_type == "BOOLEAN":
            val = "TRUE" if str(c.get("value_text")).strip().lower() in ("1", "true", "t", "sim") else "FALSE"
            value_cols = f"NULL, NULL, {val}, NULL"
        elif value_type == "DATE":
            value_cols = f"NULL, NULL, NULL, {sql_str(c.get('value_text'))}"
        else:
            value_type = "TEXT"
            value_cols = f"NULL, {sql_str(c.get('value_text'))}, NULL, NULL"
        lines.append(
            "WITH ins AS (INSERT INTO pricing.parameters "
            "(parameter_set_id, key, value_type, numeric_value, text_value, boolean_value, date_value, "
            "data_source_id) VALUES ("
            f"(SELECT id FROM pricing.parameter_sets WHERE scenario_id="
            f"(SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
            f"AND code='IMPORTED_PARAMETERS'), "
            f"{sql_str(c.get('parameter_key_guess'))}, {sql_str(value_type)}, {value_cols}, "
            f"(SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)})) "
            "RETURNING id) "
            f"UPDATE staging.parameter_candidates SET promoted_entity_id=(SELECT id FROM ins), promoted_at=now() "
            f"WHERE id={sql_str(c['id'])};"
        )
        lines.append(
            "INSERT INTO audit.data_lineage (entity_schema, entity_table, entity_id, data_source_id, derived_from) "
            "SELECT 'pricing','parameters', promoted_entity_id, "
            f"(SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)}), "
            f"'staging.parameter_candidates' FROM staging.parameter_candidates WHERE id={sql_str(c['id'])};"
        )
    return len(candidates), skipped


def emit_calibrations(lines: list[str], psql_bin: str, wb: dict, dev_bk: str) -> tuple[int, int]:
    all_candidates = fetch_unpromoted(psql_bin, "calibration_candidates", wb["id"])
    if not all_candidates:
        return 0, 0
    # mesmo critério defensivo de emit_parameters: category_key/factor vazios
    # não são promovidos, ficam staged para revisão.
    candidates = [c for c in all_candidates
                  if (c.get("category_key_guess") or "").strip() != "" and (c.get("factor_value") or "").strip() != ""]
    skipped = len(all_candidates) - len(candidates)
    if not candidates:
        return 0, skipped
    dims = sorted({c.get("dimension_guess") or "CALIBRATION" for c in candidates})
    for dim in dims:
        lines.append(
            "INSERT INTO pricing.calibration_sets (scenario_id, code, dimension, status) "
            f"SELECT (SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE'), "
            f"{sql_str(dim)}, {sql_str(dim)}, 'ACTIVE' "
            "WHERE NOT EXISTS (SELECT 1 FROM pricing.calibration_sets cs "
            f"WHERE cs.scenario_id=(SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
            f"AND cs.code={sql_str(dim)} AND cs.version=1);"
        )
    for c in candidates:
        dim = c.get("dimension_guess") or "CALIBRATION"
        lines.append(
            "WITH ins AS (INSERT INTO pricing.calibration_entries (calibration_set_id, category_key, factor) "
            f"SELECT (SELECT id FROM pricing.calibration_sets WHERE scenario_id="
            f"(SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
            f"AND code={sql_str(dim)} AND version=1), "
            f"{sql_str(c.get('category_key_guess'))}, {sql_num(c.get('factor_value'))} "
            "WHERE NOT EXISTS (SELECT 1 FROM pricing.calibration_entries ce "
            f"WHERE ce.calibration_set_id=(SELECT id FROM pricing.calibration_sets WHERE scenario_id="
            f"(SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
            f"AND code={sql_str(dim)} AND version=1) AND ce.category_key={sql_str(c.get('category_key_guess'))}) "
            "RETURNING id) "
            f"UPDATE staging.calibration_candidates SET promoted_entity_id=(SELECT id FROM ins), promoted_at=now() "
            f"WHERE id={sql_str(c['id'])} AND EXISTS (SELECT 1 FROM ins);"
        )
        lines.append(
            "INSERT INTO audit.data_lineage (entity_schema, entity_table, entity_id, data_source_id, derived_from) "
            "SELECT 'pricing','calibration_entries', promoted_entity_id, "
            f"(SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)}), "
            f"'staging.calibration_candidates' FROM staging.calibration_candidates "
            f"WHERE id={sql_str(c['id'])} AND promoted_entity_id IS NOT NULL;"
        )
    return len(candidates), skipped


def emit_price_outputs(lines: list[str], psql_bin: str, wb: dict, dev_bk: str) -> tuple[int, int]:
    all_candidates = fetch_unpromoted(psql_bin, "price_output_candidates", wb["id"])
    if not all_candidates:
        return 0, 0
    # mesmo critério defensivo: preço vazio não é promovido (system_calculated_price é NOT NULL).
    candidates = [c for c in all_candidates if (c.get("price_value") or "").strip() != ""]
    skipped = len(all_candidates) - len(candidates)
    if not candidates:
        return 0, skipped

    lines.append(
        "INSERT INTO pricing.runs (scenario_id, parameter_set_id, code, status, run_type, engine_version, "
        "started_at, completed_at) "
        f"SELECT (SELECT id FROM pricing.scenarios WHERE development_id="
        f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE'), "
        f"(SELECT id FROM pricing.parameter_sets WHERE scenario_id="
        f"(SELECT id FROM pricing.scenarios WHERE development_id="
        f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
        f"AND code='IMPORTED_PARAMETERS'), "
        f"'IMPORTED_REFERENCE_RUN', 'COMPLETED', 'IMPORTED_REFERENCE_RUN', 'IMPORTED_FROM_SOURCE_SPREADSHEET', "
        "now(), now() "
        "WHERE NOT EXISTS (SELECT 1 FROM pricing.runs r "
        f"WHERE r.scenario_id=(SELECT id FROM pricing.scenarios WHERE development_id="
        f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
        "AND r.run_type='IMPORTED_REFERENCE_RUN');"
    )
    lines.append(
        "INSERT INTO pricing.run_calibration_sets (run_id, calibration_set_id) "
        f"SELECT (SELECT id FROM pricing.runs WHERE scenario_id="
        f"(SELECT id FROM pricing.scenarios WHERE development_id="
        f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
        "AND run_type='IMPORTED_REFERENCE_RUN'), cs.id "
        "FROM pricing.calibration_sets cs "
        f"WHERE cs.scenario_id=(SELECT id FROM pricing.scenarios WHERE development_id="
        f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
        "AND NOT EXISTS (SELECT 1 FROM pricing.run_calibration_sets rcs "
        f"WHERE rcs.run_id=(SELECT id FROM pricing.runs WHERE scenario_id="
        f"(SELECT id FROM pricing.scenarios WHERE development_id="
        f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
        "AND run_type='IMPORTED_REFERENCE_RUN') AND rcs.calibration_set_id=cs.id);"
    )

    for c in candidates:
        lines.append(
            "WITH matched_unit AS ("
            "SELECT uc.promoted_entity_id AS unit_id FROM staging.unit_candidates uc "
            f"WHERE uc.source_workbook_id={sql_str(wb['id'])} AND uc.source_row={sql_num(c['source_row'])} "
            "AND uc.promoted_entity_id IS NOT NULL LIMIT 1"
            "), ins AS ("
            "INSERT INTO pricing.unit_price_results (run_id, unit_id, system_calculated_price, "
            "system_calculated_price_per_m2, result_origin) "
            f"SELECT (SELECT id FROM pricing.runs WHERE scenario_id="
            f"(SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
            "AND run_type='IMPORTED_REFERENCE_RUN'), matched_unit.unit_id, "
            f"{sql_num(c.get('price_value'))}, {sql_num(c.get('price_per_m2_value'))}, 'IMPORTED_REFERENCE' "
            "FROM matched_unit WHERE matched_unit.unit_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM pricing.unit_price_results upr WHERE upr.run_id="
            f"(SELECT id FROM pricing.runs WHERE scenario_id="
            f"(SELECT id FROM pricing.scenarios WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
            "AND run_type='IMPORTED_REFERENCE_RUN') AND upr.unit_id=matched_unit.unit_id) "
            "RETURNING id) "
            f"UPDATE staging.price_output_candidates SET promoted_entity_id=(SELECT id FROM ins), promoted_at=now() "
            f"WHERE id={sql_str(c['id'])} AND EXISTS (SELECT 1 FROM ins);"
        )
        lines.append(
            "INSERT INTO audit.data_lineage (entity_schema, entity_table, entity_id, data_source_id, derived_from) "
            "SELECT 'pricing','unit_price_results', promoted_entity_id, "
            f"(SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)}), "
            f"'staging.price_output_candidates' FROM staging.price_output_candidates "
            f"WHERE id={sql_str(c['id'])} AND promoted_entity_id IS NOT NULL;"
        )
    return len(candidates), skipped


def cmd_apply(args) -> int:
    psql_bin = ing.find_psql()
    workbooks = fetch_batch_workbooks(psql_bin, args.ingest_batch_id)
    if not workbooks:
        print(f"ERRO: nenhum workbook encontrado para ingest_batch_id={args.ingest_batch_id}", file=sys.stderr)
        return 2

    mapping_version = mapping_version_of(Path(args.mapping))

    existing = ing.run_query_csv(
        psql_bin,
        f"SELECT id, status FROM audit.promotion_runs WHERE ingest_batch_id='{args.ingest_batch_id}' "
        f"AND mapping_version='{mapping_version}';",
    )
    if existing and existing[0]["status"] == "COMPLETED":
        print(f"ALREADY_PROMOTED ingest_batch_id={args.ingest_batch_id} mapping_version={mapping_version}")
        return 0

    if existing:
        # retry de uma tentativa anterior FAILED/RUNNING para a MESMA identidade
        # (ingest_batch_id, mapping_version) — reaproveita o registro existente
        # em vez de violar a UNIQUE constraint com um novo INSERT.
        promotion_id = existing[0]["id"]
        ing.run_query_csv(
            psql_bin,
            f"UPDATE audit.promotion_runs SET status='RUNNING', started_at=now(), completed_at=NULL "
            f"WHERE id='{promotion_id}';",
        )
    else:
        promotion_rows = ing.run_query_csv(
            psql_bin,
            "INSERT INTO audit.promotion_runs (id, ingest_batch_id, mapping_version, status, started_at) "
            f"VALUES (gen_random_uuid(), '{args.ingest_batch_id}', '{mapping_version}', 'RUNNING', now()) "
            "RETURNING id;",
        )
        promotion_id = promotion_rows[0]["id"]

    lines = ["BEGIN;"]
    counts = {"developments": 0, "units": 0, "parameters": 0, "calibrations": 0, "price_outputs": 0,
              "parameters_skipped_empty": 0, "calibrations_skipped_empty": 0, "price_outputs_skipped_empty": 0}

    try:
        for wb in workbooks:
            dev_bk = business_key_for_workbook(wb["source_sha256"])
            lines.append(
                "INSERT INTO audit.data_sources (code, name, origin_type, methodology_note) "
                f"SELECT {sql_str(dev_bk)}, 'Planilha real ingerida (Fase 3A/3B)', 'real', "
                "'Ver raw.workbooks para SHA-256 de origem; nenhum valor privado neste registro.' "
                f"WHERE NOT EXISTS (SELECT 1 FROM audit.data_sources WHERE code={sql_str(dev_bk)});"
            )
            lines.append(
                "INSERT INTO core.developments (business_key, data_source_id) "
                f"SELECT {sql_str(dev_bk)}, (SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)}) "
                f"WHERE NOT EXISTS (SELECT 1 FROM core.developments WHERE business_key={sql_str(dev_bk)});"
            )
            lines.append(
                "INSERT INTO audit.data_lineage (entity_schema, entity_table, entity_id, data_source_id, derived_from) "
                "SELECT 'core','developments', (SELECT id FROM core.developments WHERE business_key="
                f"{sql_str(dev_bk)}), (SELECT id FROM audit.data_sources WHERE code={sql_str(dev_bk)}), "
                "'raw.workbooks' WHERE NOT EXISTS (SELECT 1 FROM audit.data_lineage dl WHERE dl.entity_schema='core' "
                "AND dl.entity_table='developments' AND dl.entity_id=(SELECT id FROM core.developments "
                f"WHERE business_key={sql_str(dev_bk)}));"
            )
            lines.append(
                "INSERT INTO pricing.scenarios (development_id, code, name, description, status) "
                f"SELECT (SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}), "
                "'IMPORTED_REFERENCE', 'Referência importada', "
                "'Cenário que representa os dados importados originais da fonte — não é recomendação do "
                "Patrimar Pricing Intelligence.', 'ACTIVE' "
                "WHERE NOT EXISTS (SELECT 1 FROM pricing.scenarios sc "
                f"WHERE sc.development_id=(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) "
                "AND sc.code='IMPORTED_REFERENCE');"
            )
            lines.append(
                "INSERT INTO pricing.parameter_sets (scenario_id, code, version, status) "
                f"SELECT (SELECT id FROM pricing.scenarios WHERE development_id="
                f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE'), "
                "'IMPORTED_PARAMETERS', 1, 'ACTIVE' "
                "WHERE NOT EXISTS (SELECT 1 FROM pricing.parameter_sets ps "
                f"WHERE ps.scenario_id=(SELECT id FROM pricing.scenarios WHERE development_id="
                f"(SELECT id FROM core.developments WHERE business_key={sql_str(dev_bk)}) AND code='IMPORTED_REFERENCE') "
                "AND ps.code='IMPORTED_PARAMETERS' AND ps.version=1);"
            )
            counts["developments"] += 1

            n_units, _ = emit_units(lines, psql_bin, wb, dev_bk)
            n_params, skip_params = emit_parameters(lines, psql_bin, wb, dev_bk)
            n_calib, skip_calib = emit_calibrations(lines, psql_bin, wb, dev_bk)
            n_prices, skip_prices = emit_price_outputs(lines, psql_bin, wb, dev_bk)

            counts["units"] += n_units
            counts["parameters"] += n_params
            counts["calibrations"] += n_calib
            counts["price_outputs"] += n_prices
            counts["parameters_skipped_empty"] += skip_params
            counts["calibrations_skipped_empty"] += skip_calib
            counts["price_outputs_skipped_empty"] += skip_prices
    except RuntimeError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        fail_sql = (f"UPDATE audit.promotion_runs SET status='FAILED', completed_at=now() "
                    f"WHERE id='{promotion_id}';")
        ing.run_query_csv(psql_bin, fail_sql)
        print(f"promotion_run {promotion_id} marcado como FAILED.", file=sys.stderr)
        return 1

    lines.append(f"UPDATE audit.promotion_runs SET status='COMPLETED', completed_at=now() WHERE id='{promotion_id}';")
    lines.append("COMMIT;")

    tmp_sql = Path(args.sql_scratch) if args.sql_scratch else Path("_promote_tmp.sql")
    tmp_sql.write_text("\n".join(lines), encoding="utf-8")
    result = ing.run_sql_file(psql_bin, tmp_sql, single_transaction=False)
    if not args.keep_scratch:
        tmp_sql.unlink(missing_ok=True)

    if result.returncode != 0:
        print("FALHOU ao promover — transação revertida pelo próprio PostgreSQL.", file=sys.stderr)
        print(result.stderr[-4000:], file=sys.stderr)
        fail_sql = (f"UPDATE audit.promotion_runs SET status='FAILED', completed_at=now() "
                    f"WHERE id='{promotion_id}';")
        ing.run_query_csv(psql_bin, fail_sql)
        print(f"promotion_run {promotion_id} marcado como FAILED.", file=sys.stderr)
        return 1

    print(f"OK: promotion_run={promotion_id} mapping_version={mapping_version}")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["dry-run", "summary", "apply"], default="dry-run")
    parser.add_argument("--ingest-batch-id", help="obrigatório para --mode dry-run/apply")
    parser.add_argument("--mapping", help="caminho do mapeamento privado (obrigatório para dry-run/apply)")
    parser.add_argument("--sql-scratch", default=None)
    parser.add_argument("--keep-scratch", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "summary":
        return cmd_summary(args)
    if not args.ingest_batch_id or not args.mapping:
        parser.error("--ingest-batch-id e --mapping são obrigatórios para --mode dry-run/apply")
    if args.mode == "dry-run":
        return cmd_dry_run(args)
    return cmd_apply(args)


if __name__ == "__main__":
    sys.exit(main())
