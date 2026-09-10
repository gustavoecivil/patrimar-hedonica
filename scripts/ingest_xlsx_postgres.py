#!/usr/bin/env python3
"""Ingestao controlada de workbooks XLSX para o schema `raw`/`staging`
do PostgreSQL v2 (database/v2/008_ingestion.sql).

Dois subcomandos:

  ingest-raw   Le um ou mais arquivos .xlsx e grava fidelidade total
               (workbook -> aba -> celula, valor + formula + tipo
               original) em raw.*. Idempotente por SHA-256: a mesma
               versao exata de um arquivo nunca e ingerida duas vezes.

  stage        Le raw.* (ja ingerido) + um arquivo de mapeamento JSON
               (fornecido pelo chamador, nunca hardcoded aqui) e
               popula staging.* com candidatos normalizados, mantendo
               rastreabilidade obrigatoria at'e a celula/linha de
               origem.

Requisitos (Fase 3A): biblioteca padrao + `psql` (sem psycopg2, que
nao estava disponivel no ambiente); sem nomes privados hardcoded; sem
caminhos absolutos; sem credenciais no codigo (tudo via variaveis de
ambiente padrao do libpq: PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD);
modo fail-fast; ingestao raw em transacao unica; dry-run; idempotencia;
logs nunca imprimem valor de celula por padrao.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_xlsx as ax  # noqa: E402


def find_psql() -> str:
    for candidate in ("psql", "psql.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    extra = os.environ.get("PSQL_BIN")
    if extra and Path(extra).exists():
        return extra
    raise RuntimeError(
        "psql nao encontrado no PATH. Defina PSQL_BIN com o caminho completo do executavel."
    )


def run_sql_file(psql_bin: str, sql_path: Path, single_transaction: bool = True) -> subprocess.CompletedProcess:
    args = [psql_bin, "-v", "ON_ERROR_STOP=1"]
    if single_transaction:
        args.append("--single-transaction")
    args += ["-f", str(sql_path)]
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=120)


def run_query_csv(psql_bin: str, sql: str) -> list[dict]:
    # Escreve a consulta num arquivo .sql UTF-8 e usa -f em vez de -c: no
    # Windows, passar texto acentuado (nomes de aba/coluna reais) direto
    # como argumento de linha de comando corrompe a codificacao antes de
    # chegar ao psql — comprovado ao executar de fato nesta fase.
    import csv
    import io
    import tempfile
    fd, tmp_path = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    try:
        Path(tmp_path).write_text(sql, encoding="utf-8")
        result = subprocess.run([psql_bin, "--csv", "-f", tmp_path],
                                 capture_output=True, text=True, encoding="utf-8", timeout=30)
    finally:
        os.unlink(tmp_path)
    if result.returncode != 0:
        raise RuntimeError(f"consulta falhou: {result.stderr}")
    # csv.DictReader (não usado aqui de propósito) pula silenciosamente
    # qualquer linha fisicamente vazia — o que acontece sempre que a
    # consulta seleciona UMA única coluna e o valor daquela linha é NULL
    # (o psql --csv representa essa linha como uma linha em branco, sem
    # nenhuma vírgula). Isso faz a linha inteira desaparecer do resultado,
    # não só o valor virar None — achado real ao testar promote_staging_to_core.py
    # nesta fase. Por isso, usamos csv.reader (que não pula linha vazia)
    # e pareamos manualmente com o cabeçalho.
    reader = csv.reader(io.StringIO(result.stdout))
    rows = list(reader)
    if not rows:
        return []
    header, data_rows = rows[0], rows[1:]
    out = []
    for r in data_rows:
        if r == [] and len(header) == 1:
            r = [""]
        out.append(dict(zip(header, r)))
    return out


def sql_str(value) -> str:
    # mesma ambiguidade CSV NULL vs. "" descrita em sql_num — aqui so
    # importa para valores vindos de fetch_sheet_rows (raw_value pode
    # ser SQL NULL legitimo); literais de codigo controlados nunca sao
    # "" de proposito neste script.
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def sql_num(value) -> str:
    # "" tambem significa NULL aqui: o CSV do psql representa SQL NULL
    # como campo vazio, indistinguivel de uma string vazia real — para
    # colunas numericas, ambos os casos devem virar NULL (nunca um
    # token vazio inserido cru na instrucao SQL, que e' erro de sintaxe).
    if value is None or value == "":
        return "NULL"
    return str(value)


def sql_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


# ---------------------------------------------------------------- parsing --

def parse_workbook_full(path: Path) -> dict:
    """Reaproveita audit_xlsx.py para extrair fidelidade total (nao so
    estatisticas agregadas): abas, dimensao, e toda celula preenchida
    com tipo/valor/formula originais."""
    z = ax.Zip(path)
    shared_strings = ax.parse_shared_strings(z)
    xf_to_numfmt, custom_fmts = ax.parse_styles(z)
    sheets_meta, _, _, _ = ax.parse_workbook(z)
    wb_rels = ax.parse_rels(z, "xl/_rels/workbook.xml.rels")

    sheets_out = []
    for sm in sheets_meta:
        target = wb_rels.get(sm["rId"])
        if not target:
            continue
        sheet_path = ax.resolve_target("xl", target)
        root = z.xml(sheet_path)
        if root is None:
            continue
        sheet = ax.parse_sheet_xml(root, shared_strings, xf_to_numfmt, custom_fmts)
        sheets_out.append({
            "name": sm["name"],
            "index": sm["index"],
            "state": sm["state"],
            "dimension": sheet["dimension"],
            "cells": sheet["cells"],
        })
    return {"sheets": sheets_out}


def cell_value_for_raw(cell: dict) -> tuple[str | None, str | None]:
    """Retorna (raw_value_text, cached_value_text) a partir de um dict
    de celula do audit_xlsx (type/value/formula)."""
    value = cell["value"]
    if cell["type"] == "date" and value is not None:
        text = value.isoformat()
    elif value is None:
        text = None
    else:
        text = str(value)
    if cell["formula"]:
        return None, text
    return text, None


# -------------------------------------------------------------- ingest-raw --

def cmd_ingest_raw(args) -> int:
    inputs = [ax.resolve_input_path(p) for p in args.input]
    for p in inputs:
        if not p.exists():
            print(f"ERRO: arquivo nao encontrado: {p}", file=sys.stderr)
            return 2

    hashes = []
    for p in inputs:
        import hashlib
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        hashes.append(h.hexdigest())

    if args.dry_run:
        print("=== DRY RUN — nenhuma escrita no banco ===")
        for p, sha in zip(inputs, hashes):
            parsed = parse_workbook_full(p)
            n_sheets = len(parsed["sheets"])
            # Conta apenas celulas nao-vazias — mesmo filtro usado na
            # insercao real (raw.cells so grava conteudo, nao celulas
            # sem valor/formula) — para o dry-run reconciliar de fato
            # com o "filled_cells" da auditoria da Fase 1B.
            n_cells = sum(1 for s in parsed["sheets"] for c in s["cells"].values() if c["type"] != "empty")
            n_formulas = sum(1 for s in parsed["sheets"] for c in s["cells"].values() if c["formula"])
            print(f"workbook sha256={sha[:12]}... sheets={n_sheets} cells={n_cells} formulas={n_formulas}")
        return 0

    psql_bin = find_psql()
    existing = run_query_csv(psql_bin, "SELECT source_sha256 FROM raw.workbooks;")
    existing_hashes = {row["source_sha256"] for row in existing}

    already = [sha for sha in hashes if sha in existing_hashes]
    to_ingest = [(p, sha) for p, sha in zip(inputs, hashes) if sha not in existing_hashes]

    for sha in already:
        print(f"ALREADY_INGESTED sha256={sha[:12]}...")

    if not to_ingest:
        print("Nada novo para ingerir (todos os arquivos ja foram ingeridos anteriormente).")
        return 0

    # O registro do batch e' criado e COMMITADO SEPARADAMENTE, antes do
    # bloco de risco (ingestao em massa). Se a ingestao falhar e a
    # transacao principal for revertida, o batch precisa continuar
    # existindo (em estado RUNNING) para podermos marca-lo como FAILED
    # de verdade — "nao fingir ingestao parcial bem-sucedida" (Passo 6)
    # exige que o proprio registro do batch sobreviva ao rollback.
    batch_rows = run_query_csv(
        psql_bin,
        "INSERT INTO raw.ingest_batches (id, status, source_count, tool_version, started_at) "
        f"VALUES (gen_random_uuid(), 'RUNNING', {len(to_ingest)}, {sql_str(args.tool_version)}, now()) "
        "RETURNING id;",
    )
    batch_id = batch_rows[0]["id"]

    tmp_sql = Path(args.sql_scratch) if args.sql_scratch else Path("_ingest_raw_tmp.sql")
    lines = ["BEGIN;"]

    for p, sha in to_ingest:
        parsed = parse_workbook_full(p)
        size_bytes = p.stat().st_size
        lines.append(
            f"INSERT INTO raw.workbooks (id, ingest_batch_id, source_filename, source_sha256, "
            f"source_size_bytes, sheet_count) VALUES (gen_random_uuid(), "
            f"{sql_str(batch_id)}, {sql_str(p.name)}, {sql_str(sha)}, "
            f"{sql_num(size_bytes)}, {sql_num(len(parsed['sheets']))});"
        )
        for sheet in parsed["sheets"]:
            lines.append(
                f"INSERT INTO raw.sheets (id, workbook_id, sheet_name, sheet_index, visibility, dimension_ref) "
                f"VALUES (gen_random_uuid(), (SELECT id FROM raw.workbooks WHERE source_sha256={sql_str(sha)}), "
                f"{sql_str(sheet['name'])}, {sql_num(sheet['index'])}, {sql_str(sheet['state'])}, "
                f"{sql_str(sheet['dimension'])});"
            )
            for ref, cell in sheet["cells"].items():
                if cell["type"] == "empty":
                    continue
                raw_value, cached_value = cell_value_for_raw(cell)
                lines.append(
                    "INSERT INTO raw.cells (sheet_id, cell_ref, row_number, column_index, column_letters, "
                    "cell_type, raw_value, cached_value, formula_expression, is_shared_formula, style_index) "
                    "VALUES ((SELECT s.id FROM raw.sheets s JOIN raw.workbooks w ON w.id=s.workbook_id "
                    f"WHERE w.source_sha256={sql_str(sha)} AND s.sheet_name={sql_str(sheet['name'])}), "
                    f"{sql_str(ref)}, {sql_num(cell['row'])}, {sql_num(ax.col_letters_to_index(cell['col_letters']))}, "
                    f"{sql_str(cell['col_letters'])}, {sql_str(cell['type'])}, {sql_str(raw_value)}, "
                    f"{sql_str(cached_value)}, {sql_str(cell['formula'])}, {sql_bool(bool(cell['is_shared_formula']))}, "
                    f"{sql_num(cell['style'])});"
                )

    lines.append(
        f"UPDATE raw.ingest_batches SET status='COMPLETED', completed_at=now() "
        f"WHERE id = {sql_str(batch_id)};"
    )
    lines.append("COMMIT;")
    tmp_sql.write_text("\n".join(lines), encoding="utf-8")

    result = run_sql_file(psql_bin, tmp_sql, single_transaction=False)
    if not args.keep_scratch:
        tmp_sql.unlink(missing_ok=True)

    if result.returncode != 0:
        print("FALHOU ao ingerir — transacao de dados revertida pelo proprio PostgreSQL.", file=sys.stderr)
        print(result.stderr[-4000:], file=sys.stderr)
        # o registro do batch (criado/commitado ANTES do bloco de risco,
        # acima) sobrevive ao rollback — agora e' marcado FAILED de fato,
        # numa instrucao separada e autocommitada.
        fail_sql = (f"UPDATE raw.ingest_batches SET status='FAILED', completed_at=now() "
                    f"WHERE id = {sql_str(batch_id)};")
        subprocess.run([psql_bin, "-c", fail_sql], capture_output=True, text=True, timeout=15)
        print(f"Batch {batch_id} marcado como FAILED.", file=sys.stderr)
        return 1

    print(f"OK: {len(to_ingest)} workbook(s) ingerido(s) com sucesso.")
    for p, sha in to_ingest:
        print(f"  sha256={sha[:12]}...")
    return 0


# ------------------------------------------------------------------- stage --

def load_mapping(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_sheet_rows(psql_bin: str, sha: str, sheet_name: str, columns: dict[str, str],
                      start_row: int, anchor_field: str) -> list[dict]:
    """Busca, em raw.cells, os valores das colunas de interesse para
    cada linha de dado (row_number >= start_row) de uma aba, agrupando
    por linha. Só retorna linhas onde o campo-ancora esta preenchido —
    isso e' o que distingue "linha de dado real" de linhas vazias no
    meio do intervalo (nunca assumimos que todas as linhas do range
    tem dado)."""
    # COALESCE(raw_value, cached_value): comprovado necessario ao ingerir
    # de fato — colunas que parecem "valor manual" podem, em algumas
    # linhas, ser preenchidas por FORMULA (ex.: incremento sequencial de
    # codigo de unidade tipo "=C6+1"), caso em que raw_value fica NULL e
    # o valor real esta em cached_value. Para fins de staging queremos o
    # valor efetivo, seja ele literal ou calculado — nunca perdemos a
    # formula em si, que continua intacta e consultavel em raw.cells.
    col_list = ", ".join(f"'{c}'" for c in set(columns.values()))
    sql = (
        f"SELECT row_number, column_letters, COALESCE(raw_value, cached_value) AS value_text "
        f"FROM raw.cells rc "
        f"JOIN raw.sheets s ON s.id = rc.sheet_id JOIN raw.workbooks w ON w.id = s.workbook_id "
        f"WHERE w.source_sha256 = {sql_str(sha)} AND s.sheet_name = {sql_str(sheet_name)} "
        f"AND rc.row_number >= {int(start_row)} AND rc.column_letters IN ({col_list}) "
        f"ORDER BY rc.row_number;"
    )
    rows_raw = run_query_csv(psql_bin, sql)
    by_row: dict[int, dict[str, str]] = {}
    for r in rows_raw:
        by_row.setdefault(int(r["row_number"]), {})[r["column_letters"]] = r["value_text"]

    anchor_col = columns[anchor_field]
    results = []
    for row_number, col_values in sorted(by_row.items()):
        if not col_values.get(anchor_col):
            continue
        record = {field: col_values.get(col) for field, col in columns.items()}
        record["_row_number"] = row_number
        results.append(record)
    return results


def cmd_stage(args) -> int:
    mapping = load_mapping(Path(args.mapping))

    if args.dry_run:
        by_confidence: dict[str, int] = {}
        for entry in mapping:
            by_confidence[entry["confidence"]] = by_confidence.get(entry["confidence"], 0) + 1
        print("=== DRY RUN — nenhuma escrita no banco (contagem de ENTRADAS de mapeamento, "
              "nao de linhas de dado que cada 'row_range' vai gerar) ===")
        print(f"entradas no mapeamento: {len(mapping)}")
        for k, v in sorted(by_confidence.items()):
            print(f"  {k}: {v}")
        return 0

    psql_bin = find_psql()
    lines = ["BEGIN;"]
    counts = {"unit_candidates": 0, "parameter_candidates": 0, "calibration_candidates": 0,
              "price_output_candidates": 0, "mapping_review": 0}

    for entry in mapping:
        sha = entry["workbook_sha256"]
        sheet_name = entry["sheet_name"]
        confidence = entry["confidence"]
        category = entry.get("category")
        extraction = entry.get("extraction", "single_cell")

        workbook_sql = f"(SELECT id FROM raw.workbooks WHERE source_sha256={sql_str(sha)})"
        sheet_sql = (f"(SELECT id FROM raw.sheets WHERE workbook_id={workbook_sql} "
                     f"AND sheet_name={sql_str(sheet_name)})")

        if confidence != "HIGH":
            lines.append(
                "INSERT INTO staging.mapping_review (source_workbook_id, source_sheet_id, source_row, "
                "source_cell_ref, field_label, suspected_concept, confidence, status) VALUES ("
                f"{workbook_sql}, {sheet_sql}, {sql_num(entry.get('source_row'))}, "
                f"{sql_str(entry.get('source_cell_ref'))}, {sql_str(entry.get('field_label'))}, "
                f"{sql_str(entry.get('canonical_concept', ''))}, {sql_str(confidence)}, "
                f"{sql_str('UNMAPPED' if confidence == 'LOW' else 'REVIEW_REQUIRED')});"
            )
            counts["mapping_review"] += 1
            continue

        if extraction == "single_cell":
            cell_ref = entry["cell_ref"]
            if category == "parameter":
                lines.append(
                    "INSERT INTO staging.parameter_candidates (source_workbook_id, source_sheet_id, "
                    "source_cell_ref, parameter_key_guess, value_text, value_type_guess, mapping_confidence, "
                    "mapping_status, notes) VALUES ("
                    f"{workbook_sql}, {sheet_sql}, {sql_str(cell_ref)}, "
                    f"{sql_str(entry.get('parameter_key_guess'))}, "
                    # COALESCE(raw_value, cached_value): mesmo motivo documentado em fetch_sheet_rows —
                    # uma célula de parâmetro isolada também pode ser formula-driven (achado real da
                    # Fase 3B ao promover CALIBRATION_LOOKUP_COLUMN_INDEX, ex. COLUMNS(B1:AV1)), não só
                    # colunas de dado em massa.
                    f"(SELECT COALESCE(raw_value, cached_value) FROM raw.cells rc WHERE rc.sheet_id={sheet_sql} "
                    f"AND rc.cell_ref={sql_str(cell_ref)}), "
                    f"{sql_str(entry.get('value_type_guess'))}, 'HIGH', 'CANDIDATE', {sql_str(entry.get('notes'))});"
                )
                counts["parameter_candidates"] += 1
            elif category == "calibration":
                lines.append(
                    "INSERT INTO staging.calibration_candidates (source_workbook_id, source_sheet_id, "
                    "source_cell_ref, dimension_guess, category_key_guess, factor_value, mapping_confidence, "
                    "mapping_status) VALUES ("
                    f"{workbook_sql}, {sheet_sql}, {sql_str(cell_ref)}, {sql_str(entry.get('dimension_guess'))}, "
                    f"{sql_str(entry.get('category_key_guess'))}, "
                    f"(SELECT raw_value::numeric FROM raw.cells rc WHERE rc.sheet_id={sheet_sql} "
                    f"AND rc.cell_ref={sql_str(cell_ref)}), 'HIGH', 'CANDIDATE');"
                )
                counts["calibration_candidates"] += 1
            else:
                lines.append(
                    "INSERT INTO staging.mapping_review (source_workbook_id, source_sheet_id, source_cell_ref, "
                    "field_label, suspected_concept, confidence, status) VALUES ("
                    f"{workbook_sql}, {sheet_sql}, {sql_str(cell_ref)}, {sql_str(entry.get('field_label'))}, "
                    f"{sql_str(entry.get('canonical_concept', ''))}, 'HIGH', 'REVIEW_REQUIRED');"
                )
                counts["mapping_review"] += 1
            continue

        if extraction == "row_range":
            columns = entry["columns"]
            start_row = entry["start_row"]
            anchor_field = entry["anchor_field"]
            data_rows = fetch_sheet_rows(psql_bin, sha, sheet_name, columns, start_row, anchor_field)

            if category == "unit":
                for rec in data_rows:
                    lines.append(
                        "INSERT INTO staging.unit_candidates (source_workbook_id, source_sheet_id, source_row, "
                        "development_ref, tower_ref, unit_ref, typology_ref, private_area, uncovered_area, "
                        "floor_ref, position_ref, mapping_confidence, mapping_status) VALUES ("
                        f"{workbook_sql}, {sheet_sql}, {sql_num(rec['_row_number'])}, "
                        f"{sql_str(entry.get('development_ref'))}, {sql_str(rec.get('tower_ref'))}, "
                        f"{sql_str(rec.get('unit_ref'))}, {sql_str(rec.get('typology_ref'))}, "
                        f"{sql_num(rec.get('private_area'))}, {sql_num(rec.get('uncovered_area'))}, "
                        f"{sql_str(rec.get('floor_ref'))}, {sql_str(rec.get('position_ref'))}, "
                        f"'HIGH', 'CANDIDATE');"
                    )
                    counts["unit_candidates"] += 1
            elif category == "calibration":
                dimension_guess = entry.get("dimension_guess")
                for rec in data_rows:
                    lines.append(
                        "INSERT INTO staging.calibration_candidates (source_workbook_id, source_sheet_id, "
                        "dimension_guess, category_key_guess, factor_value, mapping_confidence, "
                        "mapping_status) VALUES ("
                        f"{workbook_sql}, {sheet_sql}, {sql_str(dimension_guess)}, "
                        f"{sql_str(rec.get('category_key_guess'))}, {sql_num(rec.get('factor_value'))}, "
                        f"'HIGH', 'CANDIDATE');"
                    )
                    counts["calibration_candidates"] += 1
            elif category == "price_output":
                for rec in data_rows:
                    lines.append(
                        "INSERT INTO staging.price_output_candidates (source_workbook_id, source_sheet_id, "
                        "source_row, unit_ref_guess, price_value, price_per_m2_value, mapping_confidence, "
                        "mapping_status) VALUES ("
                        f"{workbook_sql}, {sheet_sql}, {sql_num(rec['_row_number'])}, "
                        f"{sql_str(rec.get('unit_ref_guess'))}, {sql_num(rec.get('price_value'))}, "
                        f"{sql_num(rec.get('price_per_m2_value'))}, 'HIGH', 'CANDIDATE');"
                    )
                    counts["price_output_candidates"] += 1
            continue

        raise ValueError(f"extraction desconhecida: {extraction!r}")

    lines.append("COMMIT;")
    tmp_sql = Path(args.sql_scratch) if args.sql_scratch else Path("_stage_tmp.sql")
    tmp_sql.write_text("\n".join(lines), encoding="utf-8")

    result = run_sql_file(psql_bin, tmp_sql, single_transaction=False)
    if not args.keep_scratch:
        tmp_sql.unlink(missing_ok=True)

    if result.returncode != 0:
        print("FALHOU ao popular staging — transacao revertida.", file=sys.stderr)
        print(result.stderr[-4000:], file=sys.stderr)
        return 1

    print("OK: staging populado.")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ingestao controlada de XLSX para raw/staging do schema v2.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_raw = sub.add_parser("ingest-raw")
    p_raw.add_argument("--input", action="append", required=True)
    p_raw.add_argument("--tool-version", default="ingest_xlsx_postgres/1.0")
    p_raw.add_argument("--dry-run", action="store_true")
    p_raw.add_argument("--sql-scratch", default=None)
    p_raw.add_argument("--keep-scratch", action="store_true")
    p_raw.set_defaults(func=cmd_ingest_raw)

    p_stage = sub.add_parser("stage")
    p_stage.add_argument("--mapping", required=True)
    p_stage.add_argument("--dry-run", action="store_true")
    p_stage.add_argument("--sql-scratch", default=None)
    p_stage.add_argument("--keep-scratch", action="store_true")
    p_stage.set_defaults(func=cmd_stage)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
