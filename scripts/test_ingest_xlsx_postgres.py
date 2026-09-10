#!/usr/bin/env python3
"""Teste de integracao (publico, 100% sintetico) de
scripts/ingest_xlsx_postgres.py contra um PostgreSQL real.

Cobre, usando exclusivamente um workbook .xlsx fabricado em memoria
(NUNCA um XLSX real — Fase 3A Passo 23):

  1. ingest-raw dry-run nao escreve nada no banco.
  2. ingest-raw real grava fidelidade total em raw.* (workbook/aba/
     celula, incluindo uma celula formula com cached_value separado
     do raw_value).
  3. Reingestao do mesmo arquivo (mesmo SHA-256) produz ALREADY_INGESTED
     e nao duplica nenhuma linha (idempotencia / deteccao de fonte
     duplicada).
  4. stage popula staging.unit_candidates / price_output_candidates /
     calibration_candidates / parameter_candidates a partir de entradas
     HIGH do mapeamento, e staging.mapping_review a partir de entradas
     MEDIUM (REVIEW_REQUIRED) e LOW (UNMAPPED).
  5. Toda linha de staging criada tem lineage resolvivel de volta ao
     raw.workbooks/raw.sheets de origem (nenhum orfao).
  6. Uma transacao de ingestao que viola uma constraint do banco e
     revertida pelo proprio PostgreSQL, e o batch correspondente e
     marcado FAILED (nunca "parcialmente concluido" silenciosamente) —
     mesmo padrao usado por cmd_ingest_raw em scripts/ingest_xlsx_postgres.py.

Requer um PostgreSQL real acessivel via as variaveis de ambiente padrao
do libpq (PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD), com
database/v2/001_schemas.sql..008_ingestion.sql ja aplicados (ou aplica
008 sozinho se ainda nao existir). Por seguranca, se recusa a rodar
contra um banco cujo PGDATABASE nao contenha "_test" — este teste cria
e apaga linhas, ainda que sinteticas.

Uso:
    set PGHOST=... PGPORT=... PGDATABASE=..._test PGUSER=... PGPASSWORD=...
    python scripts/test_ingest_xlsx_postgres.py
ou:
    python scripts/test_ingest_xlsx_postgres.py --env-file .env.pricing_v2_test
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest_xlsx_postgres as ing  # noqa: E402

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

SHEET_NAME = "Sintetico"


def load_env_file(path: str) -> None:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()


def build_synthetic_xlsx() -> bytes:
    """Monta, com zipfile/xml puro (sem openpyxl), um .xlsx minimo e
    100% fabricado: 1 aba, celulas literais e DUAS celulas-formula com
    cached value (mesma classe de estrutura que causou o bug real de
    extracao encontrado na Fase 3A — codigo de unidade como sequencia
    incremental de formula, nao valor manual)."""

    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{NS_CT}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    root_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_PKG_REL}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_R}">
  <sheets>
    <sheet name="{SHEET_NAME}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""

    workbook_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_PKG_REL}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    def num(ref, value):
        return f'<c r="{ref}"><v>{value}</v></c>'

    def formula(ref, expr, cached):
        return f'<c r="{ref}"><f>{expr}</f><v>{cached}</v></c>'

    def text(ref, value):
        return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'

    rows = [
        (1, [num("H1", "0.75")]),
        (2, [num("A2", "1"), num("B2", "50.5"), text("C2", "TIPO1"),
             num("D2", "500000"), text("E2", "TERREO"), num("F2", "0.95")]),
        (3, [formula("A3", "A2+1", "2"), num("B3", "60.25"), text("C3", "TIPO1"),
             num("D3", "600000"), text("E3", "PRIMEIRO"), num("F3", "1.0")]),
        (4, [formula("A4", "A3+1", "3"), num("B4", "70.0"), text("C4", "TIPO2"),
             num("D4", "700000"), text("E4", "SEGUNDO"), num("F4", "1.05")]),
    ]
    rows_xml = "".join(
        f'<row r="{r}">' + "".join(cells) + "</row>" for r, cells in rows
    )
    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_R}">
  <dimension ref="A1:H4"/>
  <sheetData>{rows_xml}</sheetData>
</worksheet>"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def capture(func, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = func(*args, **kwargs)
    return rc, buf.getvalue()


def ensure_schema(psql_bin: str) -> None:
    check = ing.run_query_csv(
        psql_bin,
        "SELECT to_regclass('raw.ingest_batches') IS NOT NULL AS present;",
    )
    if check[0]["present"] != "t":
        result = ing.run_sql_file(psql_bin, Path("database/v2/008_ingestion.sql"), single_transaction=True)
        if result.returncode != 0:
            raise RuntimeError(f"falha ao aplicar database/v2/008_ingestion.sql: {result.stderr}")


def cleanup(psql_bin: str, sha: str, extra_batch_ids: list[str]) -> None:
    stmts = [
        f"DELETE FROM staging.mapping_review WHERE source_workbook_id IN "
        f"(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
        f"DELETE FROM staging.unit_candidates WHERE source_workbook_id IN "
        f"(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
        f"DELETE FROM staging.calibration_candidates WHERE source_workbook_id IN "
        f"(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
        f"DELETE FROM staging.price_output_candidates WHERE source_workbook_id IN "
        f"(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
        f"DELETE FROM staging.parameter_candidates WHERE source_workbook_id IN "
        f"(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
        f"DELETE FROM raw.cells WHERE sheet_id IN (SELECT s.id FROM raw.sheets s "
        f"JOIN raw.workbooks w ON w.id=s.workbook_id WHERE w.source_sha256='{sha}');",
        f"DELETE FROM raw.sheets WHERE workbook_id IN (SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
        f"DELETE FROM raw.workbooks WHERE source_sha256='{sha}';",
    ]
    all_batches = ing.run_query_csv(
        psql_bin,
        f"SELECT id FROM raw.ingest_batches WHERE id::text IN "
        f"({', '.join(chr(39) + b + chr(39) for b in extra_batch_ids)});"
    ) if extra_batch_ids else []
    for b in all_batches:
        stmts.append(f"DELETE FROM raw.ingest_batches WHERE id='{b['id']}';")
    sql = "BEGIN;\n" + "\n".join(stmts) + "\nCOMMIT;\n"
    fd, tmp = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    try:
        Path(tmp).write_text(sql, encoding="utf-8")
        result = ing.run_sql_file(psql_bin, Path(tmp), single_transaction=False)
        if result.returncode != 0:
            print(f"AVISO: limpeza dos dados sinteticos falhou: {result.stderr}", file=sys.stderr)
    finally:
        os.unlink(tmp)


def run() -> int:
    checks = 0
    batch_ids_to_cleanup: list[str] = []

    psql_bin = ing.find_psql()
    ensure_schema(psql_bin)

    xlsx_bytes = build_synthetic_xlsx()
    sha = hashlib.sha256(xlsx_bytes).hexdigest()

    # garante ambiente limpo caso uma execucao anterior tenha sido interrompida
    cleanup(psql_bin, sha, [])

    fd, xlsx_path_str = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    xlsx_path = Path(xlsx_path_str)
    xlsx_path.write_bytes(xlsx_bytes)

    fd, scratch_path_str = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    scratch_path = Path(scratch_path_str)

    try:
        # 1. dry-run nao escreve nada
        before = ing.run_query_csv(psql_bin, f"SELECT count(*) AS n FROM raw.workbooks WHERE source_sha256='{sha}';")
        args_dry = argparse.Namespace(input=[str(xlsx_path)], dry_run=True, tool_version="test/synthetic",
                                       sql_scratch=str(scratch_path), keep_scratch=False)
        rc, out = capture(ing.cmd_ingest_raw, args_dry)
        assert rc == 0, f"dry-run deveria retornar 0, retornou {rc}"
        assert "DRY RUN" in out
        assert f"cells=19" in out, f"dry-run deveria contar 19 celulas preenchidas, saida: {out}"
        assert "formulas=2" in out, f"dry-run deveria contar 2 formulas, saida: {out}"
        after = ing.run_query_csv(psql_bin, f"SELECT count(*) AS n FROM raw.workbooks WHERE source_sha256='{sha}';")
        assert before == after, "dry-run nao deveria alterar raw.workbooks"
        checks += 1

        # 2. ingestao real grava fidelidade total
        args_real = argparse.Namespace(input=[str(xlsx_path)], dry_run=False, tool_version="test/synthetic",
                                        sql_scratch=str(scratch_path), keep_scratch=False)
        rc, out = capture(ing.cmd_ingest_raw, args_real)
        assert rc == 0, f"ingest-raw deveria retornar 0, retornou {rc}. saida: {out}"
        assert "OK:" in out
        checks += 1

        wb_rows = ing.run_query_csv(psql_bin, f"SELECT id, sheet_count, ingest_batch_id FROM raw.workbooks WHERE source_sha256='{sha}';")
        assert len(wb_rows) == 1, f"esperado 1 workbook, achou {len(wb_rows)}"
        assert wb_rows[0]["sheet_count"] == "1"
        batch_ids_to_cleanup.append(wb_rows[0]["ingest_batch_id"])
        checks += 1

        batch_rows = ing.run_query_csv(psql_bin, f"SELECT status FROM raw.ingest_batches WHERE id='{wb_rows[0]['ingest_batch_id']}';")
        assert batch_rows[0]["status"] == "COMPLETED", f"batch deveria estar COMPLETED, esta {batch_rows[0]['status']}"
        checks += 1

        sheet_rows = ing.run_query_csv(
            psql_bin,
            f"SELECT id, sheet_name FROM raw.sheets WHERE workbook_id='{wb_rows[0]['id']}';",
        )
        assert len(sheet_rows) == 1 and sheet_rows[0]["sheet_name"] == SHEET_NAME
        checks += 1

        cell_count = ing.run_query_csv(psql_bin, f"SELECT count(*) AS n FROM raw.cells WHERE sheet_id='{sheet_rows[0]['id']}';")
        assert cell_count[0]["n"] == "19", f"esperado 19 celulas preenchidas, banco tem {cell_count[0]['n']}"
        checks += 1

        # celula-formula preserva raw_value=NULL, cached_value e formula_expression separados
        a3 = ing.run_query_csv(
            psql_bin,
            f"SELECT raw_value, cached_value, formula_expression FROM raw.cells "
            f"WHERE sheet_id='{sheet_rows[0]['id']}' AND cell_ref='A3';",
        )[0]
        assert a3["raw_value"] == "", "A3 e formula: raw_value deveria ser NULL/vazio"
        assert a3["cached_value"] == "2.0"
        assert a3["formula_expression"] == "A2+1"
        checks += 1

        # 3. reingestao do mesmo arquivo => ALREADY_INGESTED, sem duplicar
        rc, out = capture(ing.cmd_ingest_raw, args_real)
        assert rc == 0
        assert f"ALREADY_INGESTED sha256={sha[:12]}" in out, out
        checks += 1

        cell_count_after = ing.run_query_csv(psql_bin, f"SELECT count(*) AS n FROM raw.cells WHERE sheet_id='{sheet_rows[0]['id']}';")
        assert cell_count_after[0]["n"] == "19", "reingestao nao deveria duplicar celulas"
        wb_count_after = ing.run_query_csv(psql_bin, f"SELECT count(*) AS n FROM raw.workbooks WHERE source_sha256='{sha}';")
        assert wb_count_after[0]["n"] == "1", "reingestao nao deveria duplicar o workbook"
        checks += 1

        # 4. stage: mapeamento sintetico com HIGH (todas as categorias) + MEDIUM + LOW
        mapping = [
            dict(workbook_sha256=sha, sheet_name=SHEET_NAME, extraction="single_cell", category="parameter",
                 confidence="HIGH", cell_ref="H1", parameter_key_guess="SYNTHETIC_PARAM",
                 value_type_guess="NUMERIC", notes="parametro sintetico de teste"),
            dict(workbook_sha256=sha, sheet_name=SHEET_NAME, extraction="row_range", category="unit",
                 confidence="HIGH", start_row=2, anchor_field="unit_ref",
                 columns={"unit_ref": "A", "private_area": "B", "typology_ref": "C"},
                 development_ref="SYNTH_DEV"),
            dict(workbook_sha256=sha, sheet_name=SHEET_NAME, extraction="row_range", category="price_output",
                 confidence="HIGH", start_row=2, anchor_field="unit_ref_guess",
                 columns={"unit_ref_guess": "A", "price_value": "D"}),
            dict(workbook_sha256=sha, sheet_name=SHEET_NAME, extraction="row_range", category="calibration",
                 confidence="HIGH", start_row=2, anchor_field="category_key_guess", dimension_guess="FLOOR",
                 columns={"category_key_guess": "E", "factor_value": "F"}),
            dict(workbook_sha256=sha, sheet_name=SHEET_NAME, confidence="MEDIUM",
                 source_cell_ref="Z1", field_label="campo ambiguo sintetico",
                 canonical_concept="unknown.synthetic_medium"),
            dict(workbook_sha256=sha, sheet_name=SHEET_NAME, confidence="LOW",
                 source_cell_ref="Z2", field_label="campo nao mapeado sintetico",
                 canonical_concept="unknown.synthetic_low"),
        ]
        fd, mapping_path_str = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        mapping_path = Path(mapping_path_str)
        mapping_path.write_text(json.dumps(mapping), encoding="utf-8")

        try:
            args_stage = argparse.Namespace(mapping=str(mapping_path), dry_run=False,
                                             sql_scratch=str(scratch_path), keep_scratch=False)
            rc, out = capture(ing.cmd_stage, args_stage)
            assert rc == 0, f"stage deveria retornar 0, retornou {rc}. saida: {out}"
            checks += 1

            units = ing.run_query_csv(
                psql_bin,
                f"SELECT unit_ref, private_area, typology_ref, development_ref, mapping_status "
                f"FROM staging.unit_candidates WHERE source_workbook_id="
                f"(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}') ORDER BY unit_ref;",
            )
            assert len(units) == 3, f"esperado 3 unit_candidates, achou {len(units)}"
            assert {u["unit_ref"] for u in units} == {"1.0", "2.0", "3.0"}
            assert all(u["mapping_status"] == "CANDIDATE" for u in units)
            assert all(u["development_ref"] == "SYNTH_DEV" for u in units)
            checks += 1

            prices = ing.run_query_csv(
                psql_bin,
                f"SELECT unit_ref_guess, price_value FROM staging.price_output_candidates "
                f"WHERE source_workbook_id=(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
            )
            assert len(prices) == 3
            checks += 1

            calib = ing.run_query_csv(
                psql_bin,
                f"SELECT category_key_guess, factor_value FROM staging.calibration_candidates "
                f"WHERE source_workbook_id=(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
            )
            assert len(calib) == 3
            checks += 1

            params = ing.run_query_csv(
                psql_bin,
                f"SELECT parameter_key_guess, value_text FROM staging.parameter_candidates "
                f"WHERE source_workbook_id=(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}');",
            )
            assert len(params) == 1 and params[0]["parameter_key_guess"] == "SYNTHETIC_PARAM"
            assert params[0]["value_text"] == "0.75"
            checks += 1

            reviews = ing.run_query_csv(
                psql_bin,
                f"SELECT confidence, status FROM staging.mapping_review "
                f"WHERE source_workbook_id=(SELECT id FROM raw.workbooks WHERE source_sha256='{sha}') "
                f"ORDER BY confidence;",
            )
            assert len(reviews) == 2
            by_conf = {r["confidence"]: r["status"] for r in reviews}
            assert by_conf["MEDIUM"] == "REVIEW_REQUIRED"
            assert by_conf["LOW"] == "UNMAPPED"
            checks += 1

            # 5. lineage: toda linha de staging resolve de volta ao workbook/aba de origem
            orphans = ing.run_query_csv(
                psql_bin,
                "SELECT count(*) AS n FROM staging.unit_candidates uc "
                "LEFT JOIN raw.workbooks w ON w.id = uc.source_workbook_id "
                "LEFT JOIN raw.sheets s ON s.id = uc.source_sheet_id "
                f"WHERE uc.source_workbook_id = (SELECT id FROM raw.workbooks WHERE source_sha256='{sha}') "
                "AND (w.id IS NULL OR s.id IS NULL);",
            )
            assert orphans[0]["n"] == "0", "nenhuma linha de staging deveria ficar orfa de raw.*"
            checks += 1
        finally:
            mapping_path.unlink(missing_ok=True)

        # 6. rollback-on-error: uma transacao que viola uma constraint e revertida
        #    pelo proprio PostgreSQL, e o batch e marcado FAILED — mesmo padrao
        #    usado por cmd_ingest_raw (batch commitado ANTES do bloco de risco).
        fail_batch = ing.run_query_csv(
            psql_bin,
            "INSERT INTO raw.ingest_batches (id, status, source_count, tool_version, started_at) "
            "VALUES (gen_random_uuid(), 'RUNNING', 1, 'test/synthetic-failure', now()) RETURNING id;",
        )
        fail_batch_id = fail_batch[0]["id"]
        batch_ids_to_cleanup.append(fail_batch_id)

        sentinel_filename = f"synthetic-failure-sentinel-{fail_batch_id}.xlsx"
        bad_sql = (
            "BEGIN;\n"
            f"INSERT INTO raw.workbooks (id, ingest_batch_id, source_filename, source_sha256, "
            f"source_size_bytes, sheet_count) VALUES (gen_random_uuid(), '{fail_batch_id}', "
            f"'{sentinel_filename}', 'deadbeef-synthetic-invalid-hash', -1, 1);\n"
            f"UPDATE raw.ingest_batches SET status='COMPLETED', completed_at=now() WHERE id='{fail_batch_id}';\n"
            "COMMIT;\n"
        )
        scratch_path.write_text(bad_sql, encoding="utf-8")
        result = ing.run_sql_file(psql_bin, scratch_path, single_transaction=False)
        assert result.returncode != 0, "SQL com CHECK violado (source_size_bytes > 0) deveria falhar"
        checks += 1

        fail_update_sql = (
            f"UPDATE raw.ingest_batches SET status='FAILED', completed_at=now() WHERE id='{fail_batch_id}';"
        )
        fd2, fail_tmp_str = tempfile.mkstemp(suffix=".sql")
        os.close(fd2)
        try:
            Path(fail_tmp_str).write_text(fail_update_sql, encoding="utf-8")
            result2 = ing.run_sql_file(psql_bin, Path(fail_tmp_str), single_transaction=False)
            assert result2.returncode == 0
        finally:
            os.unlink(fail_tmp_str)

        status_rows = ing.run_query_csv(psql_bin, f"SELECT status FROM raw.ingest_batches WHERE id='{fail_batch_id}';")
        assert status_rows[0]["status"] == "FAILED", "batch deveria estar FAILED apos a transacao revertida"
        checks += 1

        no_partial = ing.run_query_csv(
            psql_bin, f"SELECT count(*) AS n FROM raw.workbooks WHERE source_filename='{sentinel_filename}';"
        )
        assert no_partial[0]["n"] == "0", "nenhuma linha parcial deveria ter sobrevivido ao rollback"
        checks += 1

    finally:
        cleanup(psql_bin, sha, batch_ids_to_cleanup)
        xlsx_path.unlink(missing_ok=True)
        scratch_path.unlink(missing_ok=True)

    print(f"OK: {checks} verificacoes passaram (pipeline ingest-raw/stage sintetico + rollback FAILED)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=None,
                         help="Arquivo local KEY=VALUE com PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD "
                              "(nunca versionado). Se omitido, usa as variaveis de ambiente ja definidas.")
    args = parser.parse_args(argv)

    if args.env_file:
        load_env_file(args.env_file)

    if "_test" not in os.environ.get("PGDATABASE", ""):
        print(
            f"ERRO: recusado a rodar contra PGDATABASE={os.environ.get('PGDATABASE')!r} "
            f"(nao contem '_test'). Este teste cria/apaga dados sinteticos e so deve "
            f"rodar contra um banco de teste.",
            file=sys.stderr,
        )
        return 2

    try:
        return run()
    except AssertionError as e:
        print(f"FALHOU: {e}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired as e:
        print(f"FALHOU (timeout): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
