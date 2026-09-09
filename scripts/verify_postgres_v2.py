#!/usr/bin/env python3
"""Verifica, contra um PostgreSQL real, que os dados persistidos pelo
seed sintetico (database/v2/seeds/001_demo_allocation.sql) correspondem
exatamente aos resultados esperados
(fixtures/v2/reference_allocation_expected.json) — incluindo o hash
logico determinístico calculado pelo motor de referencia.

Conecta via `psql` (subprocesso, saida --csv) usando as variaveis de
ambiente padrao do libpq (PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD).
NUNCA recebe nem contém credenciais no código — tudo vem do ambiente.
Biblioteca padrão do Python apenas (sem psycopg2, que não estava
disponível no ambiente desta fase).

Uso:
    set PGHOST=... PGPORT=... PGDATABASE=... PGUSER=... PGPASSWORD=...
    python scripts/verify_postgres_v2.py --expected fixtures/v2/reference_allocation_expected.json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_allocation_engine as engine  # noqa: E402


def find_psql() -> str:
    for candidate in ("psql", "psql.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    extra = os.environ.get("PSQL_BIN")
    if extra and Path(extra).exists():
        return extra
    raise RuntimeError(
        "psql nao encontrado no PATH. Defina PSQL_BIN com o caminho completo do executavel, "
        "ou adicione o diretorio bin do PostgreSQL ao PATH desta sessao."
    )


def run_query(psql_bin: str, sql: str) -> list[dict]:
    # --csv por si só já inclui cabeçalho e separador correto; combinar
    # com --tuples-only/--no-align suprime o cabeçalho e troca o
    # delimitador para "|" (comprovado ao executar de fato — psql não
    # avisa sobre o conflito de flags).
    result = subprocess.run(
        [psql_bin, "--csv", "-c", sql],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"consulta falhou: {sql}\n{result.stderr}")
    reader = csv.DictReader(io.StringIO(result.stdout))
    return list(reader)


def d(value):
    return Decimal(value) if value not in (None, "") else None


def fetch_run_units(psql_bin: str, run_code: str) -> list[dict]:
    sql = f"""
    SELECT t.business_key AS tower_business_key, u.unit_code,
           upr.weighted_area_m2, upr.combined_weight_factor, upr.participation_share,
           upr.system_calculated_price, upr.system_calculated_price_per_m2
    FROM pricing.unit_price_results upr
    JOIN core.units u ON u.id = upr.unit_id
    JOIN core.towers t ON t.id = u.tower_id
    JOIN pricing.runs r ON r.id = upr.run_id
    WHERE r.code = '{run_code}'
    ORDER BY t.business_key, u.unit_code;
    """
    rows = run_query(psql_bin, sql)
    return [{
        "tower_business_key": r["tower_business_key"],
        "unit_code": r["unit_code"],
        "weighted_area_m2": d(r["weighted_area_m2"]),
        "combined_weight_factor": d(r["combined_weight_factor"]),
        "participation_share": d(r["participation_share"]),
        "system_calculated_price": d(r["system_calculated_price"]),
        "system_calculated_price_per_m2": d(r["system_calculated_price_per_m2"]),
    } for r in rows]


def fetch_vgv_target(psql_bin: str, run_code: str) -> Decimal:
    sql = f"""
    SELECT vt.target_value
    FROM pricing.vgv_targets vt JOIN pricing.runs r ON r.id = vt.run_id
    WHERE r.code = '{run_code}';
    """
    rows = run_query(psql_bin, sql)
    return d(rows[0]["target_value"])


def fetch_validation(psql_bin: str, run_code: str) -> dict:
    sql = f"""
    SELECT val.check_type, val.severity, val.expected_value, val.actual_value, val.difference
    FROM pricing.validations val JOIN pricing.runs r ON r.id = val.run_id
    WHERE r.code = '{run_code}';
    """
    rows = run_query(psql_bin, sql)
    r = rows[0]
    return {
        "check_type": r["check_type"], "severity": r["severity"],
        "expected_value": d(r["expected_value"]), "actual_value": d(r["actual_value"]),
        "difference": d(r["difference"]),
    }


def fetch_override(psql_bin: str, run_code: str) -> dict:
    sql = f"""
    SELECT t.business_key AS tower_business_key, u.unit_code,
           ov.previous_price, ov.proposed_price, ov.final_price, ov.vgv_impact
    FROM pricing.unit_overrides ov
    JOIN core.units u ON u.id = ov.unit_id
    JOIN core.towers t ON t.id = u.tower_id
    JOIN pricing.runs r ON r.id = ov.run_id
    WHERE r.code = '{run_code}';
    """
    rows = run_query(psql_bin, sql)
    r = rows[0]
    return {
        "tower_business_key": r["tower_business_key"], "unit_code": r["unit_code"],
        "previous_price": d(r["previous_price"]), "proposed_price": d(r["proposed_price"]),
        "final_price": d(r["final_price"]), "vgv_impact": d(r["vgv_impact"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compara os dados persistidos no PostgreSQL real contra "
                     "fixtures/v2/reference_allocation_expected.json."
    )
    parser.add_argument("--expected", default="fixtures/v2/reference_allocation_expected.json")
    parser.add_argument("--system-run-code", default="RUN-SYSTEM-ONLY")
    parser.add_argument("--override-run-code", default="RUN-WITH-OVERRIDE")
    args = parser.parse_args(argv)

    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    psql_bin = find_psql()

    failures = []

    units = fetch_run_units(psql_bin, args.system_run_code)
    if len(units) != expected["units_count"]:
        failures.append(f"units_count: esperado {expected['units_count']}, banco tem {len(units)}")

    target_vgv = fetch_vgv_target(psql_bin, args.system_run_code)
    if target_vgv != d(expected["target_vgv"]):
        failures.append(f"target_vgv: esperado {expected['target_vgv']}, banco tem {target_vgv}")

    total_system_price = sum((u["system_calculated_price"] for u in units), Decimal("0"))
    if total_system_price != d(expected["total_system_price"]):
        failures.append(
            f"total_system_price: esperado {expected['total_system_price']}, banco tem {total_system_price}"
        )

    validation = fetch_validation(psql_bin, args.system_run_code)
    exp_validation = expected["validation"]
    if validation["severity"] != exp_validation["severity"] or validation["difference"] != d(exp_validation["difference"]):
        failures.append(f"validation: esperado {exp_validation}, banco tem {validation}")

    run_result_from_db = {
        "algorithm": expected["algorithm"],
        "target_vgv": target_vgv,
        "total_system_price": total_system_price,
        "units": units,
    }
    hash_from_db = engine.logical_hash(run_result_from_db)
    if hash_from_db != expected["logical_hash"]:
        failures.append(f"logical_hash: esperado {expected['logical_hash']}, banco produz {hash_from_db}")

    override = fetch_override(psql_bin, args.override_run_code)
    exp_override = expected["override"]["override"]
    for field in ("previous_price", "proposed_price", "final_price", "vgv_impact"):
        if override[field] != d(exp_override[field]):
            failures.append(f"override.{field}: esperado {exp_override[field]}, banco tem {override[field]}")

    print(f"unidades verificadas: {len(units)}")
    print(f"target_vgv={target_vgv} total_system_price={total_system_price}")
    print(f"hash_from_db={hash_from_db}")
    print(f"hash_expected={expected['logical_hash']}")

    if failures:
        print(f"FALHOU: {len(failures)} divergencia(s)")
        for f in failures:
            print(f" - {f}")
        return 1

    print("OK: dados persistidos no PostgreSQL correspondem exatamente ao esperado (incluindo hash lógico)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
