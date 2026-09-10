#!/usr/bin/env python3
"""Servidor local, somente leitura, do modo PRIVATE do frontend Patrimar
Pricing Intelligence (`web/pricing-intelligence/`).

Serve GET /api/dataset no MESMO formato JSON usado por
`web/pricing-intelligence/demo-data.json` (meta/development/towers/
typologies/kpis/units/validation), mas lendo dados REAIS do banco
PostgreSQL privado local (`patrimar_pricing_v2_private_dev`).

Regras obrigatórias (Fase 3E, Passo 22):
  - Bind exclusivo em 127.0.0.1 — NUNCA 0.0.0.0.
  - Nenhuma credencial no código. A conexão usa somente as variáveis de
    ambiente padrão do libpq (PGHOST/PGPORT/PGDATABASE/PGUSER/
    PGPASSWORD), lidas do ambiente ou de um arquivo --env-file
    (formato KEY=VALUE, ex.: .env.pricing_v2_private_dev).
  - Este script nunca é executado no deploy público (Netlify) — é uso
    local apenas, para comparar com o modo DEMO.

Uso:
    python scripts/pricing_preview_server.py --env-file .env.pricing_v2_private_dev
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

# Uma única consulta SQL, agregada em JSON pelo próprio PostgreSQL
# (json_build_object/json_agg) — sem valores privados embutidos no
# texto da query, apenas nomes de tabela/coluna já públicos no schema
# (database/v2/*.sql).
DATASET_SQL = """
WITH active AS (
  SELECT s.id AS scenario_id, s.development_id
  FROM pricing.scenarios s
  WHERE s.status = 'ACTIVE'
),
latest_run AS (
  -- run_type = IMPORTED_REFERENCE_RUN: e o unico tipo de run com
  -- pricing.unit_price_results de fato populado (a referencia
  -- importada da Fase 3B). REPRODUCTION_VALIDATION_RUN (Fase 3C/3D)
  -- grava apenas em pricing.reproduction_comparisons, nao aqui.
  SELECT DISTINCT ON (r.scenario_id) r.id AS run_id, r.scenario_id, a.development_id
  FROM pricing.runs r
  JOIN active a ON a.scenario_id = r.scenario_id
  WHERE r.status = 'COMPLETED' AND r.run_type = 'IMPORTED_REFERENCE_RUN'
  ORDER BY r.scenario_id, r.completed_at DESC, r.id DESC
),
latest_override AS (
  SELECT DISTINCT ON (run_id, unit_id) run_id, unit_id, final_price, decided_at
  FROM pricing.unit_overrides
  ORDER BY run_id, unit_id, decided_at DESC
),
unit_rows AS (
  SELECT
    d.id AS development_id,
    COALESCE(d.name, d.business_key) AS development_name,
    d.city AS development_city,
    d.state AS development_state,
    d.bairro AS development_bairro,
    COALESCE(t.business_key, 'SEM-TORRE') AS tower,
    u.unit_code,
    COALESCE(ty.business_key, '') AS typology,
    u.floor,
    COALESCE(u.position_code, u.position_type, '') AS position,
    (u.closed_area_m2 + u.balcony_area_m2 + u.ancillary_area_m2) AS private_area_m2,
    u.open_terrace_area_m2 AS uncovered_area_m2,
    COALESCE(upr.weighted_area_m2, 0) AS weighted_area_m2,
    upr.system_calculated_price,
    lo.final_price AS override_final_price,
    COALESCE(lo.final_price, upr.system_calculated_price) AS final_price,
    upr.system_calculated_price_per_m2,
    COALESCE(upr.participation_share, 0) AS participation_share
  FROM latest_run lr
  JOIN pricing.unit_price_results upr ON upr.run_id = lr.run_id
  JOIN core.units u ON u.id = upr.unit_id
  JOIN core.developments d ON d.id = lr.development_id
  LEFT JOIN core.towers t ON t.id = u.tower_id
  LEFT JOIN core.unit_typologies ty ON ty.id = u.unit_typology_id
  LEFT JOIN latest_override lo ON lo.run_id = lr.run_id AND lo.unit_id = u.id
),
units_enriched AS (
  SELECT *,
    CASE WHEN override_final_price IS NOT NULL THEN override_final_price - system_calculated_price ELSE 0 END AS adjustment,
    COALESCE(system_calculated_price_per_m2,
      CASE WHEN private_area_m2 > 0 THEN round(final_price / private_area_m2, 2) ELSE 0 END) AS price_per_m2,
    CASE WHEN override_final_price IS NOT NULL THEN 'AJUSTE' ELSE 'VALIDADO' END AS status
  FROM unit_rows
),
dev_summary AS (
  SELECT
    CASE WHEN count(DISTINCT development_id) = 1 THEN max(development_name)
         ELSE count(DISTINCT development_id) || ' empreendimentos (' || string_agg(DISTINCT development_name, ', ') || ')' END AS name,
    max(development_city) AS city, max(development_state) AS state, max(development_bairro) AS bairro
  FROM units_enriched
),
final_reproduction_run AS (
  -- Pode existir mais de uma tentativa de reproducao por
  -- desenvolvimento (audit.reproduction_runs.ruleset_version); usamos
  -- apenas a mais recente COMPLETED, para nao diluir a taxa de acerto
  -- somando tentativas antigas junto da final (Fase 3D concluiu com
  -- uma unica versao final por desenvolvimento).
  SELECT DISTINCT ON (development_id) development_id, pricing_run_id
  FROM audit.reproduction_runs
  WHERE status = 'COMPLETED' AND pricing_run_id IS NOT NULL
  ORDER BY development_id, completed_at DESC
),
validation_rows AS (
  SELECT u.unit_code, COALESCE(t.business_key, 'SEM-TORRE') AS tower,
         rc.source_reference_price, rc.reproduced_price, rc.delta_absolute, rc.match_classification
  FROM pricing.reproduction_comparisons rc
  JOIN final_reproduction_run frr ON frr.pricing_run_id = rc.reproduction_run_id
  JOIN core.units u ON u.id = rc.unit_id
  LEFT JOIN core.towers t ON t.id = u.tower_id
),
validation_agg AS (
  SELECT
    count(*) AS units_analyzed,
    count(*) FILTER (WHERE match_classification IN ('EXACT','WITHIN_1_CENT')) AS within_1_cent,
    count(*) FILTER (WHERE match_classification = 'EXACT') AS exact_matches,
    COALESCE(sum(delta_absolute), 0) AS aggregate_delta,
    COALESCE(avg(abs(delta_absolute)), 0) AS mae,
    COALESCE(max(abs(delta_absolute)), 0) AS max_absolute_error
  FROM validation_rows
)
SELECT json_build_object(
  'meta', json_build_object(
    'mode', 'PRIVATE',
    'algorithm', 'REPRODUCTION_VALIDATION (ver docs/16-INDEPENDENT-PRICING-REPRODUCTION.md)',
    'disclaimer', 'Dados reais do banco privado local. Nunca publicado no Netlify/GitHub.',
    'source', 'patrimar_pricing_v2_private_dev'
  ),
  'development', (SELECT row_to_json(dev_summary) FROM dev_summary),
  'towers', (SELECT COALESCE(json_agg(DISTINCT tower ORDER BY tower), '[]'::json) FROM units_enriched),
  'typologies', (SELECT COALESCE(json_agg(DISTINCT typology ORDER BY typology), '[]'::json) FROM units_enriched),
  'kpis', (
    SELECT json_build_object(
      'vgv', COALESCE(sum(final_price), 0),
      'units_count', count(*),
      'towers_count', count(DISTINCT tower),
      'typologies_count', count(DISTINCT typology),
      'avg_price_per_m2', CASE WHEN sum(private_area_m2) > 0 THEN round(sum(final_price) / sum(private_area_m2), 2) ELSE 0 END,
      'adjustments_count', count(*) FILTER (WHERE adjustment <> 0),
      'reproduction_accuracy_pct', (SELECT CASE WHEN units_analyzed > 0 THEN round(within_1_cent::numeric / units_analyzed * 100, 1) ELSE 0 END FROM validation_agg),
      'within_1_cent_count', (SELECT within_1_cent FROM validation_agg)
    ) FROM units_enriched
  ),
  'units', (
    SELECT COALESCE(json_agg(json_build_object(
      'tower', tower, 'unit_code', unit_code, 'typology', typology, 'floor', floor, 'position', position,
      'private_area_m2', private_area_m2, 'uncovered_area_m2', uncovered_area_m2, 'weighted_area_m2', weighted_area_m2,
      'floor_factor', null, 'position_factor', null, 'participation_share', participation_share,
      'system_price', system_calculated_price, 'adjustment', adjustment, 'final_price', final_price,
      'price_per_m2', price_per_m2, 'status', status
    ) ORDER BY tower, unit_code), '[]'::json)
    FROM units_enriched
  ),
  'validation', (
    SELECT json_build_object(
      'units_analyzed', units_analyzed, 'exact_matches', exact_matches, 'within_1_cent', within_1_cent,
      'mae', round(mae, 2), 'max_absolute_error', round(max_absolute_error, 2), 'aggregate_delta', round(aggregate_delta, 2),
      'classification', 'PRIVATE_REAL', 'note', 'Comparacao real contra a referencia importada (ver docs/16 e docs/17).',
      'units', (SELECT COALESCE(json_agg(json_build_object(
        'tower', tower, 'unit_code', unit_code, 'reference_price', source_reference_price,
        'reproduced_price', reproduced_price, 'delta_absolute', delta_absolute, 'match_classification', match_classification
      )), '[]'::json) FROM validation_rows)
    ) FROM validation_agg
  )
);
"""


def find_psql() -> str:
    extra = os.environ.get("PSQL_BIN")
    if extra and Path(extra).exists():
        return extra
    for candidate in ("psql", "psql.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    print("ERRO: psql não encontrado no PATH. Defina PSQL_BIN com o caminho completo do executável.", file=sys.stderr)
    sys.exit(1)


def load_env_file(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def fetch_dataset(psql_path: str, env: dict) -> bytes:
    result = subprocess.run(
        [psql_path, "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", DATASET_SQL],
        capture_output=True, text=True, env=env, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql falhou: {result.stderr.strip()}")
    text = result.stdout.strip()
    if not text:
        raise RuntimeError("psql não retornou dados (banco vazio ou sem cenário ACTIVE?).")
    json.loads(text)  # valida antes de servir
    return text.encode("utf-8")


def make_handler(psql_path: str, env: dict):
    class Handler(BaseHTTPRequestHandler):
        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self):
            if self.path.rstrip("/") != "/api/dataset":
                self.send_response(404)
                self._cors()
                self.end_headers()
                self.wfile.write(b'{"error":"not found"}')
                return
            try:
                body = fetch_dataset(psql_path, env)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:  # noqa: BLE001
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

        def log_message(self, fmt, *args):
            sys.stderr.write("[pricing_preview_server] " + (fmt % args) + "\n")

    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", help="Arquivo KEY=VALUE com PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD "
                                            "(ex.: .env.pricing_v2_private_dev). Se omitido, usa o ambiente atual.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    env = os.environ.copy()
    if args.env_file:
        env.update(load_env_file(Path(args.env_file)))
    for required in ("PGHOST", "PGDATABASE", "PGUSER"):
        if not env.get(required):
            print(f"ERRO: variável {required} não definida (via ambiente ou --env-file).", file=sys.stderr)
            return 1

    psql_path = find_psql()
    print(f"[pricing_preview_server] validando conexão com {env.get('PGDATABASE')}@{env.get('PGHOST')}...")
    fetch_dataset(psql_path, env)
    print("[pricing_preview_server] OK — conexão validada.")

    server = HTTPServer((BIND_HOST, args.port), make_handler(psql_path, env))
    print(f"[pricing_preview_server] servindo em http://{BIND_HOST}:{args.port}/api/dataset (somente leitura, bind local)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[pricing_preview_server] encerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
