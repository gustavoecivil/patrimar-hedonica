#!/usr/bin/env python3
"""Teste de integração (público, 100% sintético) de
scripts/promote_staging_to_core.py contra um PostgreSQL real.

Cobre, usando exclusivamente dados fabricados diretamente em raw.*/
staging.* (NUNCA um workbook ou valor real — Fase 3B Passo 24):

  1. promoção de candidatos HIGH/CANDIDATE para core.developments/
     towers/unit_typologies/units e pricing.parameters/
     calibration_entries/unit_price_results (result_origin=
     IMPORTED_REFERENCE, run_type=IMPORTED_REFERENCE_RUN);
  2. candidatos com valor vazio (achado real da Fase 3B) NÃO são
     promovidos — permanecem staged, sem inventar valor;
  3. candidato MEDIUM/LOW nunca é promovido, mesmo presente na mesma
     execução;
  4. lineage sem órfãos (todo entity_id criado resolve em
     audit.data_lineage);
  5. idempotência: reexecutar a mesma (ingest_batch_id, mapping_version)
     produz ALREADY_PROMOTED, zero linhas novas;
  6. rollback-on-error: uma duplicidade real (mesmo tower_ref+unit_ref
     dentro do mesmo workbook) é detectada ANTES da escrita, a
     promoção inteira é abortada, o promotion_run correspondente
     termina FAILED, e nenhuma linha parcial sobrevive.

Requer um PostgreSQL real com database/v2/001..009 já aplicados,
acessível via as variáveis de ambiente padrão do libpq. Por segurança,
recusa rodar contra um banco cujo PGDATABASE não contenha "_test".
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
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest_xlsx_postgres as ing  # noqa: E402
import promote_staging_to_core as promote  # noqa: E402


def load_env_file(path: str) -> None:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()


def capture(func, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = func(*args, **kwargs)
    return rc, buf.getvalue()


def fake_sha() -> str:
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()


def setup_synthetic_batch(psql_bin: str, sha: str, sheet_name: str = "SinteticoTeste") -> dict:
    """Cria diretamente em raw.*/staging.* um cenário 100% sintético
    (sem parsear nenhum XLSX): 1 batch COMPLETED, 1 workbook, 1 aba, e
    candidatos HIGH/CANDIDATE cobrindo unit/parameter/calibration/
    price_output, mais 1 parâmetro com valor vazio (achado real da
    Fase 3B) e 1 candidato MEDIUM (nunca deve ser promovido)."""
    batch_id = str(uuid.uuid4())
    workbook_id = str(uuid.uuid4())
    sheet_id = str(uuid.uuid4())

    sql = f"""
BEGIN;
INSERT INTO raw.ingest_batches (id, status, source_count, tool_version, started_at, completed_at)
  VALUES ('{batch_id}', 'COMPLETED', 1, 'test/synthetic-promotion', now(), now());
INSERT INTO raw.workbooks (id, ingest_batch_id, source_filename, source_sha256, source_size_bytes, sheet_count)
  VALUES ('{workbook_id}', '{batch_id}', 'synthetic-test.xlsx', '{sha}', 100, 1);
INSERT INTO raw.sheets (id, workbook_id, sheet_name, sheet_index)
  VALUES ('{sheet_id}', '{workbook_id}', '{sheet_name}', 0);

INSERT INTO staging.unit_candidates
  (source_workbook_id, source_sheet_id, source_row, development_ref, tower_ref, unit_ref, typology_ref,
   private_area, uncovered_area, position_ref, mapping_confidence, mapping_status)
VALUES
  ('{workbook_id}', '{sheet_id}', 10, 'SYNTH', 'TORRE-A', '101', 'TIPO-1', 50.5, 5.0, 'FRENTE', 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 11, 'SYNTH', 'TORRE-A', '102', 'TIPO-1', 55.0, 0,   'FUNDOS', 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 12, 'SYNTH', 'TORRE-B', '201', 'TIPO-2', 70.0, 3.0, 'FRENTE', 'HIGH', 'CANDIDATE');

INSERT INTO staging.parameter_candidates
  (source_workbook_id, source_sheet_id, source_cell_ref, parameter_key_guess, value_text, value_type_guess,
   mapping_confidence, mapping_status)
VALUES
  ('{workbook_id}', '{sheet_id}', 'C6', 'SYNTH_PARAM_OK', '0.85', 'NUMERIC', 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 'C7', 'SYNTH_PARAM_EMPTY', NULL, 'NUMERIC', 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 'C8', 'SYNTH_PARAM_MEDIUM', '1.0', 'NUMERIC', 'MEDIUM', 'REVIEW_REQUIRED');

INSERT INTO staging.calibration_candidates
  (source_workbook_id, source_sheet_id, dimension_guess, category_key_guess, factor_value,
   mapping_confidence, mapping_status)
VALUES
  ('{workbook_id}', '{sheet_id}', 'FLOOR', '1', 0.95, 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 'FLOOR', '2', 1.05, 'HIGH', 'CANDIDATE');

INSERT INTO staging.price_output_candidates
  (source_workbook_id, source_sheet_id, source_row, unit_ref_guess, price_value, price_per_m2_value,
   mapping_confidence, mapping_status)
VALUES
  ('{workbook_id}', '{sheet_id}', 10, '101', 500000.00, 9900.99, 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 11, '102', 550000.00, 10000.00, 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 12, '201', 700000.00, 10000.00, 'HIGH', 'CANDIDATE');
COMMIT;
"""
    fd, tmp = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    try:
        Path(tmp).write_text(sql, encoding="utf-8")
        result = ing.run_sql_file(psql_bin, Path(tmp), single_transaction=False)
        if result.returncode != 0:
            raise RuntimeError(f"falha ao preparar cenário sintético: {result.stderr}")
    finally:
        os.unlink(tmp)

    return {"batch_id": batch_id, "workbook_id": workbook_id, "sheet_id": sheet_id}


def setup_duplicate_batch(psql_bin: str, sha: str) -> dict:
    """Cenário sintético que DEVE falhar: duas unidades com o mesmo
    (tower_ref, unit_ref) no mesmo workbook — duplicidade real que a
    promoção precisa detectar e abortar antes de escrever qualquer coisa."""
    batch_id = str(uuid.uuid4())
    workbook_id = str(uuid.uuid4())
    sheet_id = str(uuid.uuid4())
    sql = f"""
BEGIN;
INSERT INTO raw.ingest_batches (id, status, source_count, tool_version, started_at, completed_at)
  VALUES ('{batch_id}', 'COMPLETED', 1, 'test/synthetic-promotion-dup', now(), now());
INSERT INTO raw.workbooks (id, ingest_batch_id, source_filename, source_sha256, source_size_bytes, sheet_count)
  VALUES ('{workbook_id}', '{batch_id}', 'synthetic-test-dup.xlsx', '{sha}', 100, 1);
INSERT INTO raw.sheets (id, workbook_id, sheet_name, sheet_index)
  VALUES ('{sheet_id}', '{workbook_id}', 'SinteticoDup', 0);
INSERT INTO staging.unit_candidates
  (source_workbook_id, source_sheet_id, source_row, tower_ref, unit_ref, private_area, mapping_confidence, mapping_status)
VALUES
  ('{workbook_id}', '{sheet_id}', 10, 'TORRE-X', '999', 40.0, 'HIGH', 'CANDIDATE'),
  ('{workbook_id}', '{sheet_id}', 11, 'TORRE-X', '999', 41.0, 'HIGH', 'CANDIDATE');
COMMIT;
"""
    fd, tmp = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    try:
        Path(tmp).write_text(sql, encoding="utf-8")
        result = ing.run_sql_file(psql_bin, Path(tmp), single_transaction=False)
        if result.returncode != 0:
            raise RuntimeError(f"falha ao preparar cenário de duplicidade: {result.stderr}")
    finally:
        os.unlink(tmp)
    return {"batch_id": batch_id, "workbook_id": workbook_id, "sheet_id": sheet_id}


def cleanup(psql_bin: str, workbook_ids: list[str], batch_ids: list[str]) -> None:
    stmts = []
    for wid in workbook_ids:
        stmts += [
            f"DELETE FROM audit.data_lineage WHERE data_source_id IN "
            f"(SELECT id FROM audit.data_sources WHERE code LIKE 'DEV-%' AND code IN "
            f"(SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.unit_price_results WHERE run_id IN (SELECT r.id FROM pricing.runs r "
            f"JOIN pricing.scenarios sc ON sc.id=r.scenario_id JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.run_calibration_sets WHERE run_id IN (SELECT r.id FROM pricing.runs r "
            f"JOIN pricing.scenarios sc ON sc.id=r.scenario_id JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.runs WHERE scenario_id IN (SELECT sc.id FROM pricing.scenarios sc "
            f"JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.calibration_entries WHERE calibration_set_id IN "
            f"(SELECT cs.id FROM pricing.calibration_sets cs JOIN pricing.scenarios sc ON sc.id=cs.scenario_id "
            f"JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.calibration_sets WHERE scenario_id IN (SELECT sc.id FROM pricing.scenarios sc "
            f"JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.parameters WHERE parameter_set_id IN (SELECT ps.id FROM pricing.parameter_sets ps "
            f"JOIN pricing.scenarios sc ON sc.id=ps.scenario_id JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.parameter_sets WHERE scenario_id IN (SELECT sc.id FROM pricing.scenarios sc "
            f"JOIN core.developments d ON d.id=sc.development_id "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM core.units WHERE development_id IN (SELECT d.id FROM core.developments d "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM core.unit_typologies WHERE development_id IN (SELECT d.id FROM core.developments d "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM core.towers WHERE development_id IN (SELECT d.id FROM core.developments d "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM pricing.scenarios WHERE development_id IN (SELECT d.id FROM core.developments d "
            f"WHERE d.business_key IN (SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}'));",
            f"DELETE FROM core.developments WHERE business_key IN "
            f"(SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}');",
            f"DELETE FROM audit.data_sources WHERE code IN "
            f"(SELECT 'DEV-' || upper(substring(source_sha256,1,10)) FROM raw.workbooks WHERE id='{wid}');",
            f"DELETE FROM staging.price_output_candidates WHERE source_workbook_id='{wid}';",
            f"DELETE FROM staging.calibration_candidates WHERE source_workbook_id='{wid}';",
            f"DELETE FROM staging.parameter_candidates WHERE source_workbook_id='{wid}';",
            f"DELETE FROM staging.unit_candidates WHERE source_workbook_id='{wid}';",
            f"DELETE FROM raw.sheets WHERE workbook_id='{wid}';",
            f"DELETE FROM raw.workbooks WHERE id='{wid}';",
        ]
    for bid in batch_ids:
        stmts.append(f"DELETE FROM audit.promotion_runs WHERE ingest_batch_id='{bid}';")
        stmts.append(f"DELETE FROM raw.ingest_batches WHERE id='{bid}';")

    sql = "BEGIN;\n" + "\n".join(stmts) + "\nCOMMIT;\n"
    fd, tmp = tempfile.mkstemp(suffix=".sql")
    os.close(fd)
    try:
        Path(tmp).write_text(sql, encoding="utf-8")
        result = ing.run_sql_file(psql_bin, Path(tmp), single_transaction=False)
        if result.returncode != 0:
            print(f"AVISO: limpeza dos dados sintéticos falhou: {result.stderr}", file=sys.stderr)
    finally:
        os.unlink(tmp)


def run() -> int:
    checks = 0
    psql_bin = ing.find_psql()

    sha = fake_sha()
    ctx = setup_synthetic_batch(psql_bin, sha)
    dup_sha = fake_sha()
    dup_ctx = setup_duplicate_batch(psql_bin, dup_sha)

    fd, mapping_path_str = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    mapping_path = Path(mapping_path_str)
    mapping_path.write_text(json.dumps({"note": "sintetico, sem uso de conteudo — so para hash de versao"}),
                             encoding="utf-8")

    dev_bk = promote.business_key_for_workbook(sha)

    try:
        args = argparse.Namespace(mode="apply", ingest_batch_id=ctx["batch_id"],
                                   mapping=str(mapping_path), sql_scratch=None, keep_scratch=False)
        rc, out = capture(promote.cmd_apply, args)
        assert rc == 0, f"apply deveria retornar 0, retornou {rc}. saida: {out}"
        assert "OK:" in out
        checks += 1

        units = ing.run_query_csv(
            psql_bin,
            f"SELECT unit_code, closed_area_m2, open_terrace_area_m2, position_code, "
            f"t.business_key AS tower_bk, ty.business_key AS typ_bk "
            f"FROM core.units u LEFT JOIN core.towers t ON t.id=u.tower_id "
            f"LEFT JOIN core.unit_typologies ty ON ty.id=u.unit_typology_id "
            f"WHERE u.development_id=(SELECT id FROM core.developments WHERE business_key='{dev_bk}') "
            f"ORDER BY unit_code;",
        )
        assert len(units) == 3, f"esperado 3 unidades, achou {len(units)}"
        assert {u["unit_code"] for u in units} == {"101", "102", "201"}
        assert {u["tower_bk"] for u in units} == {"TORRE-A", "TORRE-B"}
        checks += 1

        params = ing.run_query_csv(
            psql_bin,
            f"SELECT key, numeric_value FROM pricing.parameters p "
            f"JOIN pricing.parameter_sets ps ON ps.id=p.parameter_set_id "
            f"JOIN pricing.scenarios sc ON sc.id=ps.scenario_id "
            f"WHERE sc.development_id=(SELECT id FROM core.developments WHERE business_key='{dev_bk}');",
        )
        assert len(params) == 1, f"esperado 1 parametro promovido (o com valor vazio deve ficar de fora), achou {len(params)}"
        assert params[0]["key"] == "SYNTH_PARAM_OK"
        checks += 1

        review_untouched = ing.run_query_csv(
            psql_bin,
            f"SELECT promoted_entity_id FROM staging.parameter_candidates "
            f"WHERE parameter_key_guess='SYNTH_PARAM_MEDIUM';",
        )
        assert review_untouched[0]["promoted_entity_id"] == "", "candidato MEDIUM nunca deve ser promovido"
        checks += 1

        calib = ing.run_query_csv(
            psql_bin,
            f"SELECT category_key, factor FROM pricing.calibration_entries ce "
            f"JOIN pricing.calibration_sets cs ON cs.id=ce.calibration_set_id "
            f"JOIN pricing.scenarios sc ON sc.id=cs.scenario_id "
            f"WHERE sc.development_id=(SELECT id FROM core.developments WHERE business_key='{dev_bk}');",
        )
        assert len(calib) == 2
        checks += 1

        prices = ing.run_query_csv(
            psql_bin,
            f"SELECT upr.system_calculated_price, upr.result_origin, r.run_type "
            f"FROM pricing.unit_price_results upr "
            f"JOIN pricing.runs r ON r.id=upr.run_id "
            f"JOIN pricing.scenarios sc ON sc.id=r.scenario_id "
            f"WHERE sc.development_id=(SELECT id FROM core.developments WHERE business_key='{dev_bk}');",
        )
        assert len(prices) == 3
        assert all(p["result_origin"] == "IMPORTED_REFERENCE" for p in prices)
        assert all(p["run_type"] == "IMPORTED_REFERENCE_RUN" for p in prices)
        checks += 1

        orphans = ing.run_query_csv(
            psql_bin,
            "SELECT count(*) AS n FROM audit.data_lineage dl WHERE dl.entity_table='units' "
            "AND NOT EXISTS (SELECT 1 FROM core.units u WHERE u.id=dl.entity_id) "
            f"AND dl.entity_id IN (SELECT id FROM core.units WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key='{dev_bk}'));",
        )
        assert orphans[0]["n"] == "0"
        lineage_count = ing.run_query_csv(
            psql_bin,
            "SELECT count(*) AS n FROM audit.data_lineage WHERE data_source_id="
            f"(SELECT id FROM audit.data_sources WHERE code='{dev_bk}');",
        )
        assert int(lineage_count[0]["n"]) >= 3 + 1 + 2 + 3 + 1, "lineage deveria cobrir todas as entidades promovidas"
        checks += 1

        rc2, out2 = capture(promote.cmd_apply, args)
        assert rc2 == 0
        assert "ALREADY_PROMOTED" in out2, out2
        checks += 1

        units_after = ing.run_query_csv(
            psql_bin,
            f"SELECT count(*) AS n FROM core.units WHERE development_id="
            f"(SELECT id FROM core.developments WHERE business_key='{dev_bk}');",
        )
        assert units_after[0]["n"] == "3", "reexecucao nao deveria duplicar unidades"
        checks += 1

        args_dup = argparse.Namespace(mode="apply", ingest_batch_id=dup_ctx["batch_id"],
                                       mapping=str(mapping_path), sql_scratch=None, keep_scratch=False)
        rc3, out3 = capture(promote.cmd_apply, args_dup)
        assert rc3 == 1, f"promocao com duplicidade deveria falhar (rc=1), retornou {rc3}. saida: {out3}"
        checks += 1

        dup_bk = promote.business_key_for_workbook(dup_sha)
        dup_status = ing.run_query_csv(
            psql_bin,
            f"SELECT status FROM audit.promotion_runs WHERE ingest_batch_id='{dup_ctx['batch_id']}';",
        )
        assert dup_status[0]["status"] == "FAILED", "promotion_run da duplicidade deveria estar FAILED"
        checks += 1

        no_partial = ing.run_query_csv(
            psql_bin,
            f"SELECT count(*) AS n FROM core.developments WHERE business_key='{dup_bk}';",
        )
        assert no_partial[0]["n"] == "0", "nenhuma linha parcial deveria sobreviver ao rollback da duplicidade"
        checks += 1

    finally:
        cleanup(psql_bin, [ctx["workbook_id"], dup_ctx["workbook_id"]], [ctx["batch_id"], dup_ctx["batch_id"]])
        mapping_path.unlink(missing_ok=True)

    print(f"OK: {checks} verificações passaram (promoção sintética + idempotência + rollback FAILED)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)

    if args.env_file:
        load_env_file(args.env_file)

    if "_test" not in os.environ.get("PGDATABASE", ""):
        print(
            f"ERRO: recusado a rodar contra PGDATABASE={os.environ.get('PGDATABASE')!r} "
            f"(nao contem '_test').",
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
