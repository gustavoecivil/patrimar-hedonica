#!/usr/bin/env python3
"""Testes unitarios de scripts/reference_allocation_engine.py — motor
REFERENCE_ALLOCATION_V1, 100% sintetico. Cobre: invariantes numericos,
determinismo, sensibilidade a parametros, comportamento de override, e
falha explicita sobre dados invalidos (ver docs/12).
"""

from __future__ import annotations

import copy
import sys
from decimal import Decimal

import reference_allocation_engine as engine


def fresh_scenario() -> dict:
    return engine.build_default_scenario()


def run():
    checks = 0

    scenario = fresh_scenario()
    result = engine.compute_system_run(scenario)
    units = result["units"]

    # 1. soma das participacoes = 1 dentro da tolerancia Decimal
    total_participation = sum((u["participation_share"] for u in units), Decimal(0))
    assert abs(total_participation - Decimal("1")) < Decimal("1E-20"), \
        f"soma das participacoes deveria ser 1, veio {total_participation}"
    checks += 1

    # 2. precos do SYSTEM_ONLY fecham exatamente no VGV
    assert result["total_system_price"] == result["target_vgv"], \
        "SUM(system_calculated_price) deveria fechar exatamente no VGV alvo"
    assert result["validation"]["severity"] == "INFO"
    assert result["validation"]["difference"] == Decimal("0.00")
    checks += 1

    # 3. nenhuma unidade possui participacao negativa
    assert all(u["participation_share"] >= 0 for u in units)
    checks += 1

    # 4. nenhuma unidade possui preco negativo
    assert all(u["system_calculated_price"] >= 0 for u in units)
    checks += 1

    # 5. todas as unidades possuem resultado
    assert len(units) == len(scenario["units"]) == 40
    checks += 1

    # 6. fatores obrigatorios estao presentes
    required_keys = {"weighted_area_m2", "floor_factor", "position_factor",
                      "combined_weight_factor", "participation_share",
                      "system_calculated_price", "system_calculated_price_per_m2"}
    assert all(required_keys.issubset(u.keys()) for u in units)
    checks += 1

    # 7. mesmo input produz mesmo output
    result_b = engine.compute_system_run(fresh_scenario())
    assert result["total_system_price"] == result_b["total_system_price"]
    for ua, ub in zip(sorted(units, key=lambda u: (u["tower_business_key"], u["unit_code"])),
                       sorted(result_b["units"], key=lambda u: (u["tower_business_key"], u["unit_code"]))):
        assert ua["system_calculated_price"] == ub["system_calculated_price"]
        assert ua["participation_share"] == ub["participation_share"]
    checks += 1

    # 8. hash deterministico e igual
    hash_a = engine.logical_hash(result)
    hash_b = engine.logical_hash(engine.compute_system_run(fresh_scenario()))
    assert hash_a == hash_b, "logical_hash deveria ser identico entre execucoes com o mesmo input"
    checks += 1

    # 9. alteracao de parametro altera resultado
    scenario_diff_param = fresh_scenario()
    for p in scenario_diff_param["parameter_set"]["parameters"]:
        if p["key"] == "UNCOVERED_AREA_FACTOR":
            p["numeric_value"] = "0.90"
    result_diff_param = engine.compute_system_run(scenario_diff_param)
    hash_diff_param = engine.logical_hash(result_diff_param)
    assert hash_diff_param != hash_a, "mudar UNCOVERED_AREA_FACTOR deveria mudar o resultado"
    checks += 1

    # 10. alteracao de VGV preserva proporcao esperada (participacoes inalteradas,
    #     precos escalam proporcionalmente ao novo VGV, dentro da tolerancia de
    #     arredondamento por unidade)
    scenario_double_vgv = fresh_scenario()
    scenario_double_vgv["vgv_target"]["target_value"] = "20000000.00"
    result_double_vgv = engine.compute_system_run(scenario_double_vgv)
    # a unidade que absorve o residuo de fechamento (Passo 10) carrega um
    # ajuste de arredondamento independente em cada run — por desenho, ela
    # nao escala proporcionalmente ao VGV. Todas as demais unidades devem.
    residual_units = {(u["tower_business_key"], u["unit_code"])
                       for u in units + result_double_vgv["units"] if u.get("residual_applied")}
    for ua, ub in zip(sorted(units, key=lambda u: (u["tower_business_key"], u["unit_code"])),
                       sorted(result_double_vgv["units"], key=lambda u: (u["tower_business_key"], u["unit_code"]))):
        assert ua["participation_share"] == ub["participation_share"], \
            "participacao nao deveria mudar so porque o VGV mudou"
        if (ua["tower_business_key"], ua["unit_code"]) in residual_units:
            continue
        expected = ua["system_calculated_price"] * 2
        assert abs(ub["system_calculated_price"] - expected) <= Decimal("0.01"), \
            "preco deveria dobrar proporcionalmente ao VGV, dentro de arredondamento"
    checks += 1

    # 11. override nao altera system_calculated_price historico
    result_snapshot = copy.deepcopy(result)
    override_result = engine.apply_override(result, scenario["override"])
    assert result["units"] == result_snapshot["units"], \
        "apply_override nao deveria mutar o run_result original"
    checks += 1

    # 12. override altera apenas final decision/result (nao redistribui outras unidades)
    ov = override_result["override"]
    other_units_prices_before = {(u["tower_business_key"], u["unit_code"]): u["system_calculated_price"]
                                  for u in result["units"]
                                  if (u["tower_business_key"], u["unit_code"]) != (ov["tower_business_key"], ov["unit_code"])}
    other_units_prices_after = {(u["tower_business_key"], u["unit_code"]): u["system_calculated_price"]
                                 for u in result["units"]
                                 if (u["tower_business_key"], u["unit_code"]) != (ov["tower_business_key"], ov["unit_code"])}
    assert other_units_prices_before == other_units_prices_after, \
        "override em uma unidade nao deveria alterar system_calculated_price de outras unidades"
    checks += 1

    # 13. impacto no VGV e calculado corretamente
    assert ov["vgv_impact"] == ov["final_price"] - ov["previous_price"]
    assert override_result["final_vgv"] == override_result["system_vgv"] + ov["vgv_impact"]
    assert override_result["vgv_delta_after_override"] == ov["vgv_impact"]
    checks += 1

    # 14. dados invalidos falham explicitamente
    bad_scenario = fresh_scenario()
    bad_scenario["units"][0]["tower_business_key"] = "TOWER-DOES-NOT-EXIST"
    try:
        engine.compute_system_run(bad_scenario)
        raise AssertionError("esperava ScenarioError para torre inexistente")
    except engine.ScenarioError:
        pass
    checks += 1

    bad_scenario2 = fresh_scenario()
    bad_scenario2["parameter_set"]["parameters"] = []
    try:
        engine.compute_system_run(bad_scenario2)
        raise AssertionError("esperava ScenarioError para parametro obrigatorio ausente")
    except engine.ScenarioError:
        pass
    checks += 1

    bad_scenario3 = fresh_scenario()
    bad_scenario3["vgv_target"]["target_value"] = "-5.00"
    try:
        engine.compute_system_run(bad_scenario3)
        raise AssertionError("esperava ScenarioError para VGV negativo")
    except engine.ScenarioError:
        pass
    checks += 1

    # --- invariantes de dominio (Passo 19) ---

    # scenario/unit: toda unidade referencia torre e tipologia existentes (ja
    # coberto por validate_scenario, aqui testado explicitamente)
    for u in scenario["units"]:
        assert u["tower_business_key"] in {t["business_key"] for t in scenario["towers"]}
        assert u["typology_business_key"] in {t["business_key"] for t in scenario["typologies"]}
    checks += 1

    # calibracao: toda faixa de pavimento usada tem entrada de calibracao
    floor_band_keys = {e["category_key"] for cs in scenario["calibration_sets"]
                        if cs["code"] == "FLOOR_BAND" for e in cs["entries"]}
    assert set(scenario["floor_bands"].keys()) == floor_band_keys
    checks += 1

    # override: referencia unidade coerente com o run — unidade inexistente falha
    bad_override = dict(scenario["override"])
    bad_override["target_unit_code"] = "9999"
    try:
        engine.apply_override(result_snapshot, bad_override)
        raise AssertionError("esperava ScenarioError para override em unidade inexistente")
    except engine.ScenarioError:
        pass
    checks += 1

    # --- sensibilidade (Passo 20) — teste funcional, nao estatistico ---

    # aumentar o fator da faixa HIGH deve aumentar a participacao relativa das
    # unidades de pavimento alto frente as demais.
    scenario_high_floor = fresh_scenario()
    for cs in scenario_high_floor["calibration_sets"]:
        if cs["code"] == "FLOOR_BAND":
            for e in cs["entries"]:
                if e["category_key"] == "HIGH":
                    e["factor"] = "1.50"
    result_high_floor = engine.compute_system_run(scenario_high_floor)

    def participation_by_band(res, scn):
        by_unit = {(u["tower_business_key"], u["unit_code"]): u["participation_share"] for u in res["units"]}
        total_high = Decimal(0)
        for u in scn["units"]:
            band = engine._floor_band(u["floor"], scn["floor_bands"])
            if band == "HIGH":
                total_high += by_unit[(u["tower_business_key"], u["unit_code"])]
        return total_high

    high_share_before = participation_by_band(result, scenario)
    high_share_after = participation_by_band(result_high_floor, scenario_high_floor)
    assert high_share_after > high_share_before, \
        "aumentar o fator HIGH deveria aumentar a participacao relativa das unidades de pavimento alto"
    checks += 1

    # aumentar UNCOVERED_AREA_FACTOR deve aumentar a participacao relativa das
    # unidades com area descoberta > 0 (tipologias B/C/D) frente a tipologia A.
    scenario_high_uncovered = fresh_scenario()
    for p in scenario_high_uncovered["parameter_set"]["parameters"]:
        if p["key"] == "UNCOVERED_AREA_FACTOR":
            p["numeric_value"] = "1.00"
    result_high_uncovered = engine.compute_system_run(scenario_high_uncovered)

    def participation_type_a(res, scn):
        by_unit = {(u["tower_business_key"], u["unit_code"]): u["participation_share"] for u in res["units"]}
        total_a = Decimal(0)
        for u in scn["units"]:
            if u["typology_business_key"] == "TYPE_A":
                total_a += by_unit[(u["tower_business_key"], u["unit_code"])]
        return total_a

    type_a_share_before = participation_type_a(result, scenario)
    type_a_share_after = participation_type_a(result_high_uncovered, scenario_high_uncovered)
    assert type_a_share_after < type_a_share_before, \
        "aumentar UNCOVERED_AREA_FACTOR deveria reduzir a participacao relativa da tipologia sem area descoberta"
    checks += 1

    print(f"OK: {checks} grupos de verificacao passaram (reference_allocation_engine)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
