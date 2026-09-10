#!/usr/bin/env python3
"""Gera o dataset DEMO (100% sintético, público) usado pelo frontend
Patrimar Pricing Intelligence quando publicado no Netlify.

Fonte exclusiva: `scripts/reference_allocation_engine.py` +
`fixtures/v2/reference_allocation_scenario.json` — ambos já públicos
e explicitamente sintéticos (D8, `docs/12-REFERENCE-ALLOCATION-ENGINE.md`).
NUNCA lê `data/restricted/` nem se conecta a nenhum banco privado.

Uso:
    python scripts/generate_pricing_intelligence_demo_data.py
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_allocation_engine as engine  # noqa: E402


def dec_str(value) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def build_demo_dataset() -> dict:
    scenario = engine.build_default_scenario()
    result = engine.compute_system_run(scenario)
    override_result = engine.apply_override(result, scenario["override"])

    towers = {t["business_key"]: t for t in scenario["towers"]}
    typologies = {t["business_key"]: t for t in scenario["typologies"]}
    unit_meta = {(u["tower_business_key"], u["unit_code"]): u for u in scenario["units"]}

    override_unit = (override_result["override"]["tower_business_key"], override_result["override"]["unit_code"])
    override_delta = override_result["override"]["vgv_impact"]

    units_out = []
    for m in result["units"]:
        key = (m["tower_business_key"], m["unit_code"])
        meta = unit_meta.get(key, {})
        has_override = key == override_unit
        final_price = override_result["override"]["final_price"] if has_override else m["system_calculated_price"]
        adjustment = override_delta if has_override else Decimal("0")
        units_out.append({
            "tower": m["tower_business_key"],
            "unit_code": m["unit_code"],
            "typology": meta.get("typology_business_key", ""),
            "floor": int(m["floor"]),
            "position": m["position_category"],
            "private_area_m2": dec_str(m["private_area_m2"]),
            "uncovered_area_m2": dec_str(m["uncovered_area_m2"]),
            "weighted_area_m2": dec_str(m["weighted_area_m2"]),
            "floor_factor": dec_str(m["floor_factor"]),
            "position_factor": dec_str(m["position_factor"]),
            "participation_share": dec_str(m["participation_share"]),
            "system_price": dec_str(m["system_calculated_price"]),
            "adjustment": dec_str(adjustment),
            "final_price": dec_str(final_price),
            "price_per_m2": dec_str(engine.money(final_price / m["private_area_m2"]) if m["private_area_m2"] else Decimal("0")),
            "status": "AJUSTE" if has_override else "VALIDADO",
        })

    total_final_price = sum((Decimal(u["final_price"]) for u in units_out), Decimal("0"))
    avg_price_per_m2 = engine.money(
        sum((Decimal(u["final_price"]) for u in units_out), Decimal("0"))
        / sum((Decimal(u["private_area_m2"]) for u in units_out), Decimal("0"))
    )

    validation_units = [
        {
            "tower": u["tower"], "unit_code": u["unit_code"],
            "reference_price": u["final_price"], "reproduced_price": u["final_price"],
            "delta_absolute": "0.00", "match_classification": "EXACT",
        }
        for u in units_out
    ]

    dataset = {
        "meta": {
            "mode": "DEMO",
            "algorithm": result["algorithm"],
            "disclaimer": result["disclaimer"] + " Usado aqui apenas para demonstrar a interface publicamente, "
                          "nunca como metodologia real da Patrimar.",
            "source": "fixtures/v2/reference_allocation_scenario.json (100% sintético, público)",
        },
        "development": {
            "name": scenario["development"]["name"],
            "city": scenario["development"]["city"],
            "state": scenario["development"]["state"],
            "bairro": scenario["development"]["bairro"],
        },
        "towers": sorted(towers.keys()),
        "typologies": sorted(typologies.keys()),
        "kpis": {
            "vgv": dec_str(override_result["final_vgv"]),
            "units_count": len(units_out),
            "towers_count": len(towers),
            "typologies_count": len(typologies),
            "avg_price_per_m2": dec_str(avg_price_per_m2),
            "adjustments_count": 1,
            "reproduction_accuracy_pct": "100.0",
            "within_1_cent_count": len(units_out),
        },
        "units": units_out,
        "validation": {
            "units_analyzed": len(units_out),
            "exact_matches": len(units_out),
            "within_1_cent": len(units_out),
            "mae": "0.00",
            "max_absolute_error": "0.00",
            "aggregate_delta": "0.00",
            "classification": "DEMO_ILLUSTRATIVO",
            "note": "Ambiente de demonstração: dados 100% sintéticos, gerados para ilustrar a tela — "
                    "não repetir os números reais da validação (ver docs/16 e docs/17 para os números reais, sanitizados).",
            "units": validation_units,
        },
    }
    return dataset


def main() -> int:
    dataset = build_demo_dataset()
    out_path = Path(__file__).resolve().parent.parent / "web" / "pricing-intelligence" / "demo-data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"OK: {out_path} ({len(dataset['units'])} unidades sintéticas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
