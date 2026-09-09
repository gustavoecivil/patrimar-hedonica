#!/usr/bin/env python3
"""REFERENCE_ALLOCATION_V1 — motor de referencia (100% sintetico).

ATENCAO: este algoritmo NAO representa a metodologia proprietaria da
Patrimar/Rodolfo. E uma implementacao de referencia, publica, criada
apenas para provar que o schema PostgreSQL v2 (database/v2/) e capaz
de representar um ciclo completo de distribuicao de VGV entre
unidades - dados, parametros, unidades e cenario sao inteiramente
ficticios. Ver docs/12-REFERENCE-ALLOCATION-ENGINE.md.

Algoritmo (didatico, deliberadamente simples):

    weighted_area      = private_area + uncovered_area * uncovered_area_factor
    adjustment_weight  = weighted_area * floor_factor * position_factor
    participation      = adjustment_weight / SUM(adjustment_weight)
    system_price       = target_vgv * participation   (arredondado, com
                          residuo de fechamento aplicado deterministicamente)
    price_per_m2        = system_price / private_area

Biblioteca padrao apenas (json, decimal, hashlib, argparse). Nao
depende de Excel, banco de dados ou do frontend legado. Separa
claramente calculo (funcoes puras sobre dicts) de qualquer
persistencia (que fica em scripts/generate_v2_seed.py).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path

getcontext().prec = 40  # precisao alta para as etapas intermediarias

CENTS = Decimal("0.01")
DISCLAIMER = (
    "REFERENCE_ALLOCATION_V1 e uma implementacao de referencia 100% sintetica. "
    "NAO representa a metodologia proprietaria da Patrimar/Rodolfo."
)


class ScenarioError(ValueError):
    """Erro de validacao de um cenario/entrada — sempre explicito, nunca silencioso."""


def d(value) -> Decimal:
    """Converte para Decimal de forma segura (nunca via float)."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------- construcao --

def build_default_scenario() -> dict:
    """Constroi deterministicamente o cenario canonico de demonstracao.

    Nenhuma aleatoriedade: 2 torres x 10 pavimentos x 2 unidades/pavimento
    = 40 unidades, com tipologia e posicao atribuidas por formula simples
    (indice mod N), nao por sorteio.
    """
    towers = [
        {"business_key": "TOWER-1", "name": "Reference Tower 1"},
        {"business_key": "TOWER-2", "name": "Reference Tower 2"},
    ]
    typologies = [
        {"business_key": "TYPE_A", "name": "Reference Typology A", "bedrooms": 1,
         "suites": 0, "private_area_m2": "45.00", "uncovered_area_m2": "0.00"},
        {"business_key": "TYPE_B", "name": "Reference Typology B", "bedrooms": 2,
         "suites": 1, "private_area_m2": "65.00", "uncovered_area_m2": "5.00"},
        {"business_key": "TYPE_C", "name": "Reference Typology C", "bedrooms": 3,
         "suites": 1, "private_area_m2": "85.00", "uncovered_area_m2": "10.00"},
        {"business_key": "TYPE_D", "name": "Reference Typology D", "bedrooms": 4,
         "suites": 2, "private_area_m2": "120.00", "uncovered_area_m2": "20.00"},
    ]
    position_cycle = ["A", "B", "C", "D"]
    typology_cycle = [t["business_key"] for t in typologies]

    units = []
    for tower in towers:
        for floor in range(1, 11):
            for slot in (1, 2):
                unit_index = (floor - 1) * 2 + slot  # 1..20 dentro da torre
                position_category = position_cycle[(unit_index - 1) % len(position_cycle)]
                typology_key = typology_cycle[(unit_index - 1) % len(typology_cycle)]
                unit_code = f"{floor:02d}{slot:02d}"
                units.append({
                    "tower_business_key": tower["business_key"],
                    "typology_business_key": typology_key,
                    "unit_code": unit_code,
                    "floor": floor,
                    "position_category": position_category,
                })

    scenario = {
        "meta": {
            "name": "REFERENCE_ALLOCATION_V1 demo scenario",
            "disclaimer": DISCLAIMER,
            "generation_note": "Gerado por formula deterministica (indice mod N) — sem PRNG.",
        },
        "development": {
            "business_key": "DEMO-ALLOCATION-001",
            "name": "Reference Allocation Demo Development",
            "city": "Reference City",
            "state": "RF",
            "bairro": "Reference District",
            "total_floors": 10,
        },
        "towers": towers,
        "typologies": typologies,
        "units": units,
        "floor_bands": {"LOW": [1, 3], "MID": [4, 7], "HIGH": [8, 10]},
        "parameter_set": {
            "code": "REFERENCE_ALLOCATION_V1",
            "version": 1,
            "parameters": [
                {"key": "UNCOVERED_AREA_FACTOR", "value_type": "NUMERIC",
                 "numeric_value": "0.40", "unit_of_measure": "ratio",
                 "description": "Fator sintetico aplicado a area descoberta ao compor a area ponderada."},
            ],
        },
        "calibration_sets": [
            {"code": "FLOOR_BAND", "dimension": "FLOOR", "entries": [
                {"category_key": "LOW", "factor": "1.00"},
                {"category_key": "MID", "factor": "1.05"},
                {"category_key": "HIGH", "factor": "1.10"},
            ]},
            {"code": "POSITION_CATEGORY", "dimension": "POSITION", "entries": [
                {"category_key": "A", "factor": "1.00"},
                {"category_key": "B", "factor": "1.02"},
                {"category_key": "C", "factor": "1.04"},
                {"category_key": "D", "factor": "1.06"},
            ]},
        ],
        "vgv_target": {
            "target_value": "10000000.00",
            "origin": "MANUAL",
            "note": "SYNTHETIC_MANUAL_TARGET — valor didatico, sem relacao com nenhum dado real.",
        },
        "scenario": {"code": "DEMO-SCENARIO-001", "name": "Reference allocation demo scenario",
                      "status": "ACTIVE"},
        "runs": {
            "run1": {"code": "RUN-SYSTEM-ONLY", "label": "SYSTEM_ONLY"},
            "run2": {"code": "RUN-WITH-OVERRIDE", "label": "WITH_OVERRIDE"},
        },
        "override": {
            "run": "run2",
            "target_unit_code": "0101",
            "target_tower_business_key": "TOWER-1",
            "reason": "Motivo ficticio de demonstracao: ajuste estrategico sintetico, sem relacao com nenhum caso real.",
            "override_delta": "50000.00",
            "decided_at": "2026-09-09T12:00:00+00:00",
        },
    }
    return scenario


# ----------------------------------------------------------------- validacao --

def validate_scenario(scenario: dict) -> None:
    tower_keys = {t["business_key"] for t in scenario["towers"]}
    typology_keys = {t["business_key"] for t in scenario["typologies"]}
    seen_codes = set()
    for u in scenario["units"]:
        if u["tower_business_key"] not in tower_keys:
            raise ScenarioError(f"unidade {u['unit_code']} referencia torre inexistente: {u['tower_business_key']}")
        if u["typology_business_key"] not in typology_keys:
            raise ScenarioError(f"unidade {u['unit_code']} referencia tipologia inexistente: {u['typology_business_key']}")
        key = (u["tower_business_key"], u["unit_code"])
        if key in seen_codes:
            raise ScenarioError(f"unit_code duplicado dentro da torre: {key}")
        seen_codes.add(key)
        if d(next(t for t in scenario["typologies"] if t["business_key"] == u["typology_business_key"])["private_area_m2"]) <= 0:
            raise ScenarioError(f"area privativa invalida (<=0) para unidade {u['unit_code']}")

    band_keys = {e["category_key"] for cs in scenario["calibration_sets"] if cs["code"] == "FLOOR_BAND" for e in cs["entries"]}
    for band, (lo, hi) in scenario["floor_bands"].items():
        if band not in band_keys:
            raise ScenarioError(f"faixa de pavimento '{band}' nao tem entrada de calibracao correspondente")
        if lo > hi:
            raise ScenarioError(f"faixa de pavimento '{band}' invalida: {lo}..{hi}")

    position_keys = {e["category_key"] for cs in scenario["calibration_sets"] if cs["code"] == "POSITION_CATEGORY" for e in cs["entries"]}
    for u in scenario["units"]:
        if u["position_category"] not in position_keys:
            raise ScenarioError(f"unidade {u['unit_code']} usa posicao sem calibracao: {u['position_category']}")

    params = {p["key"]: p for p in scenario["parameter_set"]["parameters"]}
    if "UNCOVERED_AREA_FACTOR" not in params:
        raise ScenarioError("parametro obrigatorio ausente: UNCOVERED_AREA_FACTOR")

    if d(scenario["vgv_target"]["target_value"]) <= 0:
        raise ScenarioError("target_value do VGV deve ser positivo")


# ------------------------------------------------------------------- calculo --

def _floor_band(floor: int, floor_bands: dict) -> str:
    for band, (lo, hi) in floor_bands.items():
        if lo <= floor <= hi:
            return band
    raise ScenarioError(f"pavimento {floor} nao pertence a nenhuma faixa configurada")


def _calibration_factor(scenario: dict, calibration_code: str, category_key: str) -> Decimal:
    for cs in scenario["calibration_sets"]:
        if cs["code"] == calibration_code:
            for entry in cs["entries"]:
                if entry["category_key"] == category_key:
                    return d(entry["factor"])
    raise ScenarioError(f"entrada de calibracao nao encontrada: {calibration_code}/{category_key}")


def compute_unit_metrics(scenario: dict, unit: dict) -> dict:
    typology = next(t for t in scenario["typologies"] if t["business_key"] == unit["typology_business_key"])
    private_area = d(typology["private_area_m2"])
    uncovered_area = d(typology["uncovered_area_m2"])
    uncovered_factor = d(next(p for p in scenario["parameter_set"]["parameters"]
                               if p["key"] == "UNCOVERED_AREA_FACTOR")["numeric_value"])

    weighted_area = private_area + uncovered_area * uncovered_factor

    band = _floor_band(unit["floor"], scenario["floor_bands"])
    floor_factor = _calibration_factor(scenario, "FLOOR_BAND", band)
    position_factor = _calibration_factor(scenario, "POSITION_CATEGORY", unit["position_category"])

    adjustment_weight = weighted_area * floor_factor * position_factor

    return {
        "tower_business_key": unit["tower_business_key"],
        "unit_code": unit["unit_code"],
        "private_area_m2": private_area,
        "uncovered_area_m2": uncovered_area,
        "floor": unit["floor"],
        "floor_band": band,
        "position_category": unit["position_category"],
        "weighted_area_m2": weighted_area,
        "floor_factor": floor_factor,
        "position_factor": position_factor,
        "combined_weight_factor": floor_factor * position_factor,
        "adjustment_weight": adjustment_weight,
    }


def compute_system_run(scenario: dict) -> dict:
    """Calcula o resultado SYSTEM_ONLY de uma unica run. Determinístico:
    mesmo `scenario` produz sempre o mesmo resultado (sem estado global,
    sem horario do sistema, sem aleatoriedade)."""
    validate_scenario(scenario)

    target_vgv = d(scenario["vgv_target"]["target_value"])
    metrics = [compute_unit_metrics(scenario, u) for u in scenario["units"]]
    total_weight = sum((m["adjustment_weight"] for m in metrics), Decimal("0"))
    if total_weight <= 0:
        raise ScenarioError("soma dos pesos de ajuste e zero ou negativa — cenario invalido")

    for m in metrics:
        m["participation_share"] = m["adjustment_weight"] / total_weight
        m["raw_price"] = target_vgv * m["participation_share"]
        m["system_calculated_price"] = money(m["raw_price"])

    # fechamento do VGV: residuo de arredondamento vai, deterministicamente,
    # para a unidade de maior participacao (empate: unit_code crescente).
    total_rounded = sum((m["system_calculated_price"] for m in metrics), Decimal("0"))
    residual = money(target_vgv - total_rounded)
    if residual != 0:
        chosen = sorted(metrics, key=lambda m: (-m["participation_share"], m["tower_business_key"], m["unit_code"]))[0]
        chosen["system_calculated_price"] = money(chosen["system_calculated_price"] + residual)
        chosen["residual_applied"] = str(residual)

    for m in metrics:
        m["system_calculated_price_per_m2"] = money(m["system_calculated_price"] / m["private_area_m2"])

    total_system_price = sum((m["system_calculated_price"] for m in metrics), Decimal("0"))

    validation = {
        "check_type": "VGV_RECONCILIATION",
        "severity": "INFO" if total_system_price == target_vgv else "ERROR",
        "expected_value": target_vgv,
        "actual_value": total_system_price,
        "difference": total_system_price - target_vgv,
    }

    unit_adjustments = []
    for m in metrics:
        unit_adjustments.extend([
            {"tower_business_key": m["tower_business_key"], "unit_code": m["unit_code"],
             "adjustment_type": "AREA_WEIGHTING", "sequence_order": 1,
             "input_value": m["private_area_m2"], "factor_value": None,
             "result_value": m["weighted_area_m2"]},
            {"tower_business_key": m["tower_business_key"], "unit_code": m["unit_code"],
             "adjustment_type": "FLOOR_PREMIUM", "sequence_order": 2,
             "input_value": m["weighted_area_m2"], "factor_value": m["floor_factor"],
             "result_value": m["weighted_area_m2"] * m["floor_factor"]},
            {"tower_business_key": m["tower_business_key"], "unit_code": m["unit_code"],
             "adjustment_type": "POSITION_PREMIUM", "sequence_order": 3,
             "input_value": m["weighted_area_m2"] * m["floor_factor"], "factor_value": m["position_factor"],
             "result_value": m["adjustment_weight"]},
        ])

    return {
        "algorithm": "REFERENCE_ALLOCATION_V1",
        "disclaimer": DISCLAIMER,
        "target_vgv": target_vgv,
        "total_weight": total_weight,
        "units": metrics,
        "unit_adjustments": unit_adjustments,
        "validation": validation,
        "total_system_price": total_system_price,
    }


def apply_override(run_result: dict, override_cfg: dict) -> dict:
    """Aplica um evento de override sobre um resultado SYSTEM_ONLY já
    calculado, sem jamais alterar system_calculated_price (Passo 11/14).
    Retorna uma estrutura NOVA — o `run_result` de entrada não é mutado."""
    tower_key = override_cfg["target_tower_business_key"]
    unit_code = override_cfg["target_unit_code"]
    unit = next((m for m in run_result["units"]
                 if m["tower_business_key"] == tower_key and m["unit_code"] == unit_code), None)
    if unit is None:
        raise ScenarioError(f"override aponta para unidade inexistente no run: {tower_key}/{unit_code}")

    previous_price = unit["system_calculated_price"]
    delta = d(override_cfg["override_delta"])
    proposed_price = money(previous_price + delta)
    final_price = proposed_price  # nesta referência, proposto == final (sem aprovação parcial)
    vgv_impact = final_price - previous_price

    override_record = {
        "tower_business_key": tower_key,
        "unit_code": unit_code,
        "previous_price": previous_price,
        "proposed_price": proposed_price,
        "final_price": final_price,
        "vgv_impact": vgv_impact,
        "reason": override_cfg["reason"],
        "decided_at": override_cfg["decided_at"],
    }

    system_vgv = run_result["total_system_price"]
    final_vgv = system_vgv + vgv_impact

    return {
        "algorithm": run_result["algorithm"],
        "disclaimer": run_result["disclaimer"],
        "target_vgv": run_result["target_vgv"],
        "system_vgv": system_vgv,
        "final_vgv": final_vgv,
        "vgv_delta_after_override": vgv_impact,
        "override": override_record,
    }


# ------------------------------------------------------------------- hashing --

def _jsonable(obj):
    if isinstance(obj, Decimal):
        return format(obj, "f")  # sempre ponto-fixo, nunca notacao cientifica; determinístico
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    return obj


def canonical_json(obj) -> str:
    return json.dumps(_jsonable(obj), sort_keys=True, separators=(",", ":"))


def logical_hash(run_result: dict) -> str:
    """SHA-256 de um payload canonico e determinístico: participação,
    preços e fatores por unidade + total. Nunca inclui timestamps.

    A quantização de cada campo aqui usa DELIBERADAMENTE a mesma escala
    da coluna correspondente em pricing.unit_price_results
    (database/v2/003_pricing.sql) — weighted_area_m2 NUMERIC(12,4),
    combined_weight_factor NUMERIC(12,6), participation_share
    NUMERIC(9,6). Isso foi comprovado necessário na Fase 2C: calculado
    com a precisão interna quase ilimitada do Decimal em memória, o
    hash não reproduzia depois de ir e voltar de um PostgreSQL real,
    porque a coluna participation_share (6 casas) arredonda um valor
    que em memória tem dezenas de casas decimais. O dinheiro em si
    (system_calculated_price) nunca foi afetado — só este hash, que
    deve refletir o que de fato é persistido, não a precisão interna
    do cálculo."""
    payload = {
        "algorithm": run_result["algorithm"],
        "target_vgv": run_result["target_vgv"],
        "total_system_price": run_result["total_system_price"],
        "units": [
            {
                "tower_business_key": m["tower_business_key"],
                "unit_code": m["unit_code"],
                "weighted_area_m2": m["weighted_area_m2"].quantize(Decimal("0.0001")),
                "combined_weight_factor": m["combined_weight_factor"].quantize(Decimal("0.000001")),
                "participation_share": m["participation_share"].quantize(Decimal("0.000001")),
                "system_calculated_price": m["system_calculated_price"],
                "system_calculated_price_per_m2": m["system_calculated_price_per_m2"],
            }
            for m in sorted(run_result["units"], key=lambda m: (m["tower_business_key"], m["unit_code"]))
        ],
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------- IO --

def load_scenario(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_scenario(scenario: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(scenario, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def result_to_jsonable(run_result: dict) -> dict:
    return _jsonable(copy.deepcopy(run_result))


# ------------------------------------------------------------------- CLI --

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Motor de referencia REFERENCE_ALLOCATION_V1 (100% sintetico, sem dependencias externas)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build-scenario", help="Gera o cenario canonico de demonstracao (JSON).")
    p_build.add_argument("--output", required=True)

    p_run = sub.add_parser("run", help="Calcula um run SYSTEM_ONLY a partir de um cenario.")
    p_run.add_argument("--scenario", required=True)
    p_run.add_argument("--output")

    p_override = sub.add_parser("apply-override", help="Aplica o override configurado no cenario sobre um run.")
    p_override.add_argument("--scenario", required=True)
    p_override.add_argument("--output")

    args = parser.parse_args(argv)

    if args.command == "build-scenario":
        save_scenario(build_default_scenario(), Path(args.output))
        print(f"cenario escrito em {args.output}")
        return 0

    if args.command == "run":
        scenario = load_scenario(Path(args.scenario))
        result = compute_system_run(scenario)
        result["logical_hash"] = logical_hash(result)
        out = result_to_jsonable(result)
        if args.output:
            Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
        print(f"logical_hash={result['logical_hash']}", file=sys.stderr)
        return 0

    if args.command == "apply-override":
        scenario = load_scenario(Path(args.scenario))
        result = compute_system_run(scenario)
        override_result = apply_override(result, scenario["override"])
        out = result_to_jsonable(override_result)
        if args.output:
            Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
