#!/usr/bin/env python3
"""Gera, a partir da fixture canonica fixtures/v2/reference_allocation_scenario.json
e do motor scripts/reference_allocation_engine.py, tres artefatos derivados
(nunca editados manualmente):

  - database/v2/seeds/001_demo_allocation.sql   (dados 100% sinteticos)
  - fixtures/v2/reference_allocation_expected.json
  - fixtures/v2/reference_allocation_report.md

A fixture JSON e a UNICA fonte de verdade do cenario de demonstracao.
Os tres artefatos acima sao sempre regenerados a partir dela — nunca
editados a mao — para nao divergirem entre si (ver docs/12).

Biblioteca padrao apenas. Sem dependencia de PostgreSQL/psycopg2 (o
SQL gerado e apenas texto).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_allocation_engine as engine  # noqa: E402

SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL,
                             "patrimar-hedonica/database/v2/seeds/001_demo_allocation")
RUN_TIMESTAMP_BASE = "2026-09-09T18:00:00+00:00"  # literal, determinístico — ver nota em pricing.runs abaixo


def uid(*parts: str) -> str:
    return str(uuid.uuid5(SEED_NAMESPACE, ":".join(parts)))


def sql_str(value) -> str:
    if value is None:
        return "NULL"
    text = str(value).replace("'", "''")
    return f"'{text}'"


def sql_num(value) -> str:
    if value is None:
        return "NULL"
    return str(value)


def sql_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


class SeedBuilder:
    def __init__(self, scenario: dict):
        self.scenario = scenario
        self.lines: list[str] = []

    def emit(self, text: str):
        self.lines.append(text)

    def insert(self, table: str, columns: list[str], values: list):
        cols = ", ".join(columns)
        vals = ", ".join(values)
        self.emit(f"INSERT INTO {table} ({cols}) VALUES ({vals});")

    def build(self) -> str:
        s = self.scenario
        self.emit("-- Seed 100% sintetico — gerado por scripts/generate_v2_seed.py")
        self.emit(f"-- Fonte: fixtures/v2/reference_allocation_scenario.json — NAO editar a mao.")
        self.emit(f"-- {engine.DISCLAIMER}")
        self.emit("")

        data_source_id = uid("audit.data_sources", "SYNTHETIC-REFERENCE-V1")
        self.insert("audit.data_sources",
                     ["id", "code", "name", "origin_type", "methodology_note"],
                     [sql_str(data_source_id), sql_str("SYNTHETIC-REFERENCE-V1"),
                      sql_str("Reference allocation synthetic demo data"),
                      sql_str("synthetic"),
                      sql_str("Dados 100% sinteticos gerados por scripts/generate_v2_seed.py para provar o schema v2.")])
        self.emit("")

        dev = s["development"]
        development_id = uid("core.developments", dev["business_key"])
        self.insert("core.developments",
                     ["id", "business_key", "name", "city", "state", "bairro", "total_floors", "data_source_id"],
                     [sql_str(development_id), sql_str(dev["business_key"]), sql_str(dev["name"]),
                      sql_str(dev["city"]), sql_str(dev["state"]), sql_str(dev["bairro"]),
                      sql_num(dev["total_floors"]), sql_str(data_source_id)])
        self.emit("")

        tower_ids = {}
        for t in s["towers"]:
            tid = uid("core.towers", dev["business_key"], t["business_key"])
            tower_ids[t["business_key"]] = tid
            self.insert("core.towers", ["id", "development_id", "business_key", "name"],
                         [sql_str(tid), sql_str(development_id), sql_str(t["business_key"]), sql_str(t["name"])])
        self.emit("")

        typology_ids = {}
        for ty in s["typologies"]:
            tyid = uid("core.unit_typologies", dev["business_key"], ty["business_key"])
            typology_ids[ty["business_key"]] = tyid
            self.insert("core.unit_typologies",
                         ["id", "development_id", "business_key", "name", "bedrooms", "suites"],
                         [sql_str(tyid), sql_str(development_id), sql_str(ty["business_key"]),
                          sql_str(ty["name"]), sql_num(ty["bedrooms"]), sql_num(ty["suites"])])
        self.emit("")

        unit_ids = {}
        for u in s["units"]:
            ty = next(t for t in s["typologies"] if t["business_key"] == u["typology_business_key"])
            key = (u["tower_business_key"], u["unit_code"])
            unid = uid("core.units", dev["business_key"], *key)
            unit_ids[key] = unid
            self.insert(
                "core.units",
                ["id", "development_id", "tower_id", "unit_typology_id", "unit_code", "floor",
                 "position_code", "closed_area_m2", "balcony_area_m2", "ancillary_area_m2",
                 "open_terrace_area_m2", "data_source_id"],
                [sql_str(unid), sql_str(development_id), sql_str(tower_ids[u["tower_business_key"]]),
                 sql_str(typology_ids[u["typology_business_key"]]), sql_str(u["unit_code"]),
                 sql_num(u["floor"]), sql_str(u["position_category"]),
                 sql_num(ty["private_area_m2"]), sql_num("0.00"), sql_num("0.00"),
                 sql_num(ty["uncovered_area_m2"]), sql_str(data_source_id)],
            )
        self.emit("")

        scenario_id = uid("pricing.scenarios", dev["business_key"], s["scenario"]["code"])
        self.insert("pricing.scenarios",
                     ["id", "development_id", "code", "name", "status", "description"],
                     [sql_str(scenario_id), sql_str(development_id), sql_str(s["scenario"]["code"]),
                      sql_str(s["scenario"]["name"]), sql_str(s["scenario"]["status"]),
                      sql_str("Cenario de demonstracao 100% sintetico (REFERENCE_ALLOCATION_V1). " + s["vgv_target"]["note"])])
        self.emit("")

        pset = s["parameter_set"]
        parameter_set_id = uid("pricing.parameter_sets", scenario_id, pset["code"], str(pset["version"]))
        self.insert("pricing.parameter_sets",
                     ["id", "scenario_id", "code", "version", "status"],
                     [sql_str(parameter_set_id), sql_str(scenario_id), sql_str(pset["code"]),
                      sql_num(pset["version"]), sql_str("ACTIVE")])
        parameter_ids = {}
        for p in pset["parameters"]:
            pid = uid("pricing.parameters", parameter_set_id, p["key"])
            parameter_ids[p["key"]] = pid
            self.insert("pricing.parameters",
                         ["id", "parameter_set_id", "key", "value_type", "numeric_value",
                          "unit_of_measure", "description", "data_source_id"],
                         [sql_str(pid), sql_str(parameter_set_id), sql_str(p["key"]),
                          sql_str(p["value_type"]), sql_num(p["numeric_value"]),
                          sql_str(p["unit_of_measure"]), sql_str(p["description"]), sql_str(data_source_id)])
        self.emit("")

        calibration_set_ids = {}
        calibration_entry_ids = {}  # (calibration_code, category_key) -> id
        for cs in s["calibration_sets"]:
            csid = uid("pricing.calibration_sets", scenario_id, cs["code"], "1")
            calibration_set_ids[cs["code"]] = csid
            self.insert("pricing.calibration_sets",
                         ["id", "scenario_id", "code", "dimension", "version", "status"],
                         [sql_str(csid), sql_str(scenario_id), sql_str(cs["code"]),
                          sql_str(cs["dimension"]), sql_num(1), sql_str("ACTIVE")])
            for e in cs["entries"]:
                eid = uid("pricing.calibration_entries", csid, e["category_key"])
                calibration_entry_ids[(cs["code"], e["category_key"])] = eid
                self.insert("pricing.calibration_entries",
                             ["id", "calibration_set_id", "category_key", "factor"],
                             [sql_str(eid), sql_str(csid), sql_str(e["category_key"]), sql_num(e["factor"])])
        self.emit("")

        run_ids = {}
        # Timestamps literais e deterministicos (nunca now()): duas runs
        # aplicadas na mesma transacao com now() teriam o MESMO
        # completed_at, o que a Fase 2C provou (executando de fato contra
        # PostgreSQL) tornar a escolha de "run mais recente" da view
        # nao deterministica. Cada run subsequente completa 1 minuto
        # depois da anterior, na ordem em que aparecem na fixture.
        base_ts = datetime.fromisoformat(RUN_TIMESTAMP_BASE)
        for i, (run_key, run_cfg) in enumerate(s["runs"].items()):
            rid = uid("pricing.runs", scenario_id, run_cfg["code"])
            run_ids[run_key] = rid
            started_at = (base_ts + timedelta(minutes=i)).isoformat()
            completed_at = (base_ts + timedelta(minutes=i, seconds=30)).isoformat()
            self.insert("pricing.runs",
                         ["id", "scenario_id", "parameter_set_id", "code", "status", "engine_version",
                          "started_at", "completed_at"],
                         [sql_str(rid), sql_str(scenario_id), sql_str(parameter_set_id),
                          sql_str(run_cfg["code"]), sql_str("COMPLETED"), sql_str("REFERENCE_ALLOCATION_V1"),
                          sql_str(started_at), sql_str(completed_at)])
            for csid in calibration_set_ids.values():
                self.insert("pricing.run_calibration_sets", ["run_id", "calibration_set_id"],
                             [sql_str(rid), sql_str(csid)])
        self.emit("")

        target_vgv = engine.d(s["vgv_target"]["target_value"])
        vgv_target_ids = {}
        for run_key, rid in run_ids.items():
            vid = uid("pricing.vgv_targets", scenario_id, run_key)
            vgv_target_ids[run_key] = vid
            self.insert("pricing.vgv_targets",
                         ["id", "scenario_id", "run_id", "origin", "target_value", "status"],
                         [sql_str(vid), sql_str(scenario_id), sql_str(rid), sql_str(s["vgv_target"]["origin"]),
                          sql_num(target_vgv), sql_str("ACTIVE")])
        self.emit("")

        system_result = engine.compute_system_run(s)

        for run_key, rid in run_ids.items():
            for m in system_result["units"]:
                key = (m["tower_business_key"], m["unit_code"])
                unit_id = unit_ids[key]
                for adj in [a for a in system_result["unit_adjustments"]
                            if a["tower_business_key"] == key[0] and a["unit_code"] == key[1]]:
                    aid = uid("pricing.unit_adjustments", rid, unit_id, adj["adjustment_type"])
                    # rastreabilidade: liga o ajuste ao parametro ou a entrada de
                    # calibracao que efetivamente originou o fator aplicado.
                    calibration_entry_id = None
                    parameter_id = None
                    if adj["adjustment_type"] == "AREA_WEIGHTING":
                        parameter_id = parameter_ids["UNCOVERED_AREA_FACTOR"]
                    elif adj["adjustment_type"] == "FLOOR_PREMIUM":
                        calibration_entry_id = calibration_entry_ids[("FLOOR_BAND", m["floor_band"])]
                    elif adj["adjustment_type"] == "POSITION_PREMIUM":
                        calibration_entry_id = calibration_entry_ids[("POSITION_CATEGORY", m["position_category"])]
                    self.insert(
                        "pricing.unit_adjustments",
                        ["id", "run_id", "unit_id", "adjustment_type", "input_value", "factor_value",
                         "calibration_entry_id", "parameter_id", "result_value", "sequence_order"],
                        [sql_str(aid), sql_str(rid), sql_str(unit_id), sql_str(adj["adjustment_type"]),
                         sql_num(adj["input_value"]), sql_num(adj["factor_value"]),
                         sql_str(calibration_entry_id), sql_str(parameter_id),
                         sql_num(adj["result_value"]), sql_num(adj["sequence_order"])],
                    )
                self.insert(
                    "pricing.unit_price_results",
                    ["id", "run_id", "unit_id", "weighted_area_m2", "participation_share",
                     "combined_weight_factor", "system_calculated_price", "system_calculated_price_per_m2"],
                    [sql_str(uid("pricing.unit_price_results", rid, unit_id)), sql_str(rid), sql_str(unit_id),
                     sql_num(m["weighted_area_m2"].quantize(Decimal("0.0001"))),
                     sql_num(m["participation_share"].quantize(Decimal("0.000001"))),  # 6 casas: NUMERIC(9,6)
                     sql_num(m["combined_weight_factor"].quantize(Decimal("0.000001"))),
                     sql_num(m["system_calculated_price"]), sql_num(m["system_calculated_price_per_m2"])],
                )
            self.emit("")

            v = system_result["validation"]
            self.insert(
                "pricing.validations",
                ["id", "run_id", "check_type", "severity", "expected_value", "actual_value", "message"],
                [sql_str(uid("pricing.validations", rid)), sql_str(rid), sql_str(v["check_type"]),
                 sql_str(v["severity"]), sql_num(v["expected_value"]), sql_num(v["actual_value"]),
                 sql_str("REFERENCE_ALLOCATION_V1 — reconciliacao de VGV do run.")],
            )
            self.emit("")

        override_cfg = s["override"]
        override_run_id = run_ids[override_cfg["run"]]
        override_result = engine.apply_override(system_result, override_cfg)
        ov = override_result["override"]
        unit_key = (ov["tower_business_key"], ov["unit_code"])
        self.insert(
            "pricing.unit_overrides",
            ["id", "run_id", "unit_id", "previous_price", "proposed_price", "final_price",
             "reason", "decided_at"],
            [sql_str(uid("pricing.unit_overrides", override_run_id, unit_ids[unit_key])),
             sql_str(override_run_id), sql_str(unit_ids[unit_key]),
             sql_num(ov["previous_price"]), sql_num(ov["proposed_price"]), sql_num(ov["final_price"]),
             sql_str(ov["reason"]), sql_str(ov["decided_at"])],
        )
        self.emit("")

        return "\n".join(self.lines) + "\n"


def build_expected_results(scenario: dict) -> dict:
    system_result = engine.compute_system_run(scenario)
    override_result = engine.apply_override(system_result, scenario["override"])
    logical_hash = engine.logical_hash(system_result)
    return engine.result_to_jsonable({
        "algorithm": system_result["algorithm"],
        "disclaimer": system_result["disclaimer"],
        "units_count": len(system_result["units"]),
        "target_vgv": system_result["target_vgv"],
        "total_system_price": system_result["total_system_price"],
        "validation": system_result["validation"],
        "logical_hash": logical_hash,
        "participation_sum_check": sum((m["participation_share"] for m in system_result["units"]), Decimal(0)),
        "override": override_result,
    })


def build_report(scenario: dict, expected: dict) -> str:
    lines = [
        "# Reference Allocation Engine — Relatório de Execução (sintético)",
        "",
        f"> {engine.DISCLAIMER}",
        "",
        f"- Algoritmo: `{expected['algorithm']}`",
        f"- Unidades: {expected['units_count']}",
        f"- VGV alvo (sintético): {expected['target_vgv']}",
        f"- VGV sistemático (soma dos preços calculados): {expected['total_system_price']}",
        f"- Validação VGV_RECONCILIATION: {expected['validation']['severity']} "
        f"(diferença: {expected['validation']['difference']})",
        f"- Soma das participações (deve ser 1, dentro da precisão Decimal): "
        f"{expected['participation_sum_check']}",
        f"- Hash lógico determinístico (RUN 1 — SYSTEM_ONLY): `{expected['logical_hash']}`",
        "",
        "## Override de demonstração (RUN 2 — WITH_OVERRIDE)",
        "",
        f"- Unidade: torre `{expected['override']['override']['tower_business_key']}`, "
        f"código `{expected['override']['override']['unit_code']}`",
        f"- Preço anterior (sistemático): {expected['override']['override']['previous_price']}",
        f"- Preço final após override: {expected['override']['override']['final_price']}",
        f"- Impacto no VGV: {expected['override']['override']['vgv_impact']}",
        f"- VGV sistemático: {expected['override']['system_vgv']}",
        f"- VGV final (após override): {expected['override']['final_vgv']}",
        f"- Delta VGV após override: {expected['override']['vgv_delta_after_override']}",
        "",
        "## Fonte",
        "",
        "Gerado a partir de `fixtures/v2/reference_allocation_scenario.json` por "
        "`scripts/generate_v2_seed.py`. Não editar este relatório manualmente — regenerar.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera seed SQL e artefatos derivados a partir da fixture canônica.")
    parser.add_argument("--scenario", default="fixtures/v2/reference_allocation_scenario.json")
    parser.add_argument("--seed-output", default="database/v2/seeds/001_demo_allocation.sql")
    parser.add_argument("--expected-output", default="fixtures/v2/reference_allocation_expected.json")
    parser.add_argument("--report-output", default="fixtures/v2/reference_allocation_report.md")
    args = parser.parse_args(argv)

    scenario = engine.load_scenario(Path(args.scenario))
    engine.validate_scenario(scenario)

    seed_sql = SeedBuilder(scenario).build()
    Path(args.seed_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.seed_output).write_text(seed_sql, encoding="utf-8")

    expected = build_expected_results(scenario)
    Path(args.expected_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.expected_output).write_text(
        json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    report = build_report(scenario, expected)
    Path(args.report_output).write_text(report, encoding="utf-8")

    print(f"seed SQL: {args.seed_output}")
    print(f"expected results: {args.expected_output}")
    print(f"report: {args.report_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
