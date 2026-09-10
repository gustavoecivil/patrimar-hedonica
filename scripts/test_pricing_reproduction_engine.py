#!/usr/bin/env python3
"""Testes sintéticos (públicos) de scripts/pricing_reproduction_engine.py.

Usa exclusivamente regras e nomes FICTÍCIOS ("widget"/"gadget"),
estruturalmente equivalentes ao que a Fase 3C usa de verdade
(soma, soma ponderada, fatores multiplicativos, busca em tabela por
chave derivada, participação proporcional, combinação linear,
divisão), mas SEM nenhuma fórmula, constante ou nome real da Patrimar
— ver docs/16-INDEPENDENT-PRICING-REPRODUCTION.md.

Cobre: grafo/DAG e ordem topológica; dependência ausente; ciclo;
Decimal (float rejeitado); regra dormente (nunca executada); regra
bloqueada com propagação transitiva; parâmetro; calibração/lookup por
chave derivada; override (combinação linear + soma); cálculo sem
qualquer acesso a "referência"; determinismo (hash lógico estável);
comportamento de arredondamento com Decimal puro.
"""

from __future__ import annotations

import sys
from decimal import Decimal

from pricing_reproduction_engine import (
    Ruleset, RulesetError, ReproductionEngine,
    derive_magnitude_prefix_key, logical_hash, to_decimal,
)


def run() -> int:
    checks = 0

    # 1. grafo/DAG: ordem topologica respeita dependencias
    rs = Ruleset({
        "inputs": {"a": {}, "b": {}},
        "rules": [
            {"rule_id": "R2", "output": "y", "operation": "sum", "operands": {"fields": ["x", "b"]}},
            {"rule_id": "R1", "output": "x", "operation": "sum", "operands": {"fields": ["a", "b"]}},
        ],
    })
    order = rs.topo_order()
    assert order.index("x") < order.index("y"), "x deve vir antes de y na ordem topologica"
    checks += 1

    # 2. dependencia ausente -> RulesetError
    try:
        Ruleset({
            "inputs": {"a": {}},
            "rules": [{"rule_id": "R1", "output": "x", "operation": "sum", "operands": {"fields": ["a", "nao_existe"]}}],
        })
        assert False, "deveria ter levantado RulesetError para dependencia ausente"
    except RulesetError:
        pass
    checks += 1

    # 3. ciclo -> RulesetError
    try:
        Ruleset({
            "inputs": {},
            "rules": [
                {"rule_id": "R1", "output": "x", "operation": "sum", "operands": {"fields": ["y"]}},
                {"rule_id": "R2", "output": "y", "operation": "sum", "operands": {"fields": ["x"]}},
            ],
        })
        assert False, "deveria ter levantado RulesetError para ciclo"
    except RulesetError:
        pass
    checks += 1

    # 4. operacao desconhecida -> RulesetError
    try:
        Ruleset({
            "inputs": {"a": {}},
            "rules": [{"rule_id": "R1", "output": "x", "operation": "nao_existe", "operands": {}}],
        })
        assert False, "deveria ter levantado RulesetError para operacao desconhecida"
    except RulesetError:
        pass
    checks += 1

    # 5. Decimal obrigatorio -- float rejeitado
    try:
        to_decimal(1.5)
        assert False, "to_decimal deveria rejeitar float"
    except TypeError:
        pass
    assert to_decimal("1.50") == Decimal("1.50")
    assert to_decimal(None) is None
    checks += 1

    # 6. derive_magnitude_prefix_key -- operacao generica parametrizada
    assert derive_magnitude_prefix_key("101", Decimal(1000), 1, 2) == "1"
    assert derive_magnitude_prefix_key("1205", Decimal(1000), 1, 2) == "12"
    assert derive_magnitude_prefix_key(None, Decimal(1000), 1, 2) is None
    checks += 1

    # 7. pipeline completo: sum -> weighted_sum -> multiply_factors -> lookup_table ->
    #    group_sum -> multiply_by_parameter -> ratio_to_group_total -> linear_price -> divide
    ruleset_data = {
        "inputs": {"base_a": {}, "base_b": {}, "extra": {}, "widget_code": {}, "WIDGET_WEIGHT": {}, "override_amt": {}},
        "rules": [
            {"rule_id": "G1", "output": "total_size", "operation": "sum", "operands": {"fields": ["base_a", "base_b", "extra"]}},
            {"rule_id": "G2", "output": "weighted_size", "operation": "weighted_sum",
             "operands": {"base_fields": ["base_a", "base_b"], "weighted_field": "extra", "weight_parameter": "WIDGET_WEIGHT"}},
            {"rule_id": "G3", "output": "tier_factor", "operation": "lookup_table",
             "operands": {"key_source_field": "widget_code", "derivation": "magnitude_prefix",
                          "derivation_params": {"threshold": 1000, "digits_below": 1, "digits_at_or_above": 2},
                          "table": {"1": "0.10", "2": "0.20"}}},
            {"rule_id": "G4", "output": "adjusted_size", "operation": "multiply_factors",
             "operands": {"base": "weighted_size", "factors": ["tier_factor"]}},
            {"rule_id": "G5", "output": "group_total", "operation": "group_sum", "operands": {"fields": ["adjusted_size"]}},
            {"rule_id": "G6", "output": "group_budget", "operation": "multiply_by_parameter",
             "operands": {"field": "group_total", "parameter": "WIDGET_WEIGHT"}},
            {"rule_id": "G7", "output": "share", "operation": "ratio_to_group_total",
             "operands": {"numerator_field": "adjusted_size", "group_total_field": "group_total"}},
            {"rule_id": "G8", "output": "price", "operation": "linear_price",
             "operands": {"participation_field": "share", "group_value_field": "group_budget", "addend_field": "override_amt"}},
            {"rule_id": "G9", "output": "price_per_unit_size", "operation": "divide",
             "operands": {"numerator_field": "price", "denominator_field": "total_size"}},
        ],
    }
    rs2 = Ruleset(ruleset_data)
    engine = ReproductionEngine(rs2)
    units = [
        {"unit_id": "w1", "group_id": "g1", "base_a": "10", "base_b": "5", "extra": "2", "widget_code": "101", "WIDGET_WEIGHT": "100", "override_amt": "0"},
        {"unit_id": "w2", "group_id": "g1", "base_a": "20", "base_b": "5", "extra": "4", "widget_code": "205", "WIDGET_WEIGHT": "100", "override_amt": "50"},
    ]
    result = engine.compute(units)
    assert result["per_unit"]["w1"]["total_size"] == Decimal("17")
    assert result["per_unit"]["w1"]["tier_factor"] == Decimal("0.10")
    assert result["per_unit"]["w2"]["tier_factor"] == Decimal("0.20")
    total_price = result["per_unit"]["w1"]["price"] + result["per_unit"]["w2"]["price"]
    expected_budget = result["group_values"]["g1"]["group_budget"]
    # a soma dos precos == orcamento do grupo + soma dos overrides (identidade de participacao)
    assert total_price == expected_budget + Decimal("50"), "soma dos precos deveria fechar no orcamento + overrides"
    checks += 1

    # 8. regra dormente -- nunca executada, nao aparece como dependencia obrigatoria de nada
    ruleset_dormant = {
        "inputs": {"a": {}},
        "rules": [
            {"rule_id": "D1", "output": "dormant_factor", "operation": "sum", "operands": {"fields": ["a"]}, "status": "DORMANT"},
            {"rule_id": "D2", "output": "active_value", "operation": "sum", "operands": {"fields": ["a"]}, "status": "ACTIVE"},
        ],
    }
    rs3 = Ruleset(ruleset_dormant)
    res3 = ReproductionEngine(rs3).compute([{"unit_id": "u1", "group_id": "g1", "a": "10"}])
    assert res3["per_unit"]["u1"]["dormant_factor"] is None, "regra DORMANT nunca deve produzir valor"
    assert res3["per_unit"]["u1"]["active_value"] == Decimal("10")
    assert "dormant_factor" in res3["blocked_rules"]
    checks += 1

    # 9. bloqueio transitivo -- regra que depende de uma bloqueada tambem fica bloqueada,
    #    nunca calculada com valor inventado
    ruleset_blocked = {
        "inputs": {"a": {}},
        "rules": [
            {"rule_id": "B1", "output": "unavailable", "operation": "sum", "operands": {"fields": ["a"]}, "status": "BLOCKED_BY_AMBIGUITY"},
            {"rule_id": "B2", "output": "depends_on_unavailable", "operation": "multiply_factors",
             "operands": {"base": "a", "factors": ["unavailable"]}},
        ],
    }
    rs4 = Ruleset(ruleset_blocked)
    res4 = ReproductionEngine(rs4).compute([{"unit_id": "u1", "group_id": "g1", "a": "10"}])
    assert res4["per_unit"]["u1"]["unavailable"] is None
    assert res4["per_unit"]["u1"]["depends_on_unavailable"] is None
    assert "depends_on_unavailable" in res4["blocked_rules"]
    assert res4["blocked_rules"]["depends_on_unavailable"].startswith("BLOCKED_TRANSITIVELY_VIA")
    checks += 1

    # 10. calculo sem qualquer acesso a "referencia" -- ReproductionEngine.compute() e' puro
    #     sobre a lista de unidades recebida, sem nenhum parametro/atributo de conexao a banco
    #     ou a preco de referencia. Prova estrutural: nenhum atributo do engine/ruleset carrega
    #     algo com "reference"/"source_price" no nome, e compute() aceita e devolve so o que foi
    #     passado.
    forbidden_terms = ("reference", "source_price", "gabarito")
    engine_attrs = " ".join(dir(ReproductionEngine)) + " ".join(dir(engine.compute))
    assert not any(t in engine_attrs.lower() for t in forbidden_terms), \
        "o motor de calculo nao pode ter nenhum atributo relacionado a preco de referencia"
    units_no_ref = [{"unit_id": "u1", "group_id": "g1", "base_a": "1", "base_b": "1", "extra": "1",
                      "widget_code": "101", "WIDGET_WEIGHT": "10", "override_amt": "0"}]
    ReproductionEngine(rs2).compute(units_no_ref)  # nao levanta erro nem pede nada alem disso
    checks += 1

    # 11. determinismo -- mesmo input produz mesmo hash logico, independente de reexecucao
    res_a = engine.compute(units)
    res_b = engine.compute(units)
    hash_a = logical_hash(res_a, ["w1", "w2"], ["price", "price_per_unit_size"])
    hash_b = logical_hash(res_b, ["w1", "w2"], ["price", "price_per_unit_size"])
    assert hash_a == hash_b, "mesma entrada deveria produzir hash logico identico"
    units_diff = [dict(u) for u in units]
    units_diff[1]["override_amt"] = "51"
    res_c = engine.compute(units_diff)
    hash_c = logical_hash(res_c, ["w1", "w2"], ["price", "price_per_unit_size"])
    assert hash_c != hash_a, "mudar um input deveria mudar o hash logico"
    checks += 1

    # 12. arredondamento -- Decimal preserva precisao total (nao arredonda implicitamente)
    precise = ReproductionEngine(rs2).compute([
        {"unit_id": "p1", "group_id": "gp", "base_a": "1", "base_b": "1", "extra": "1",
         "widget_code": "101", "WIDGET_WEIGHT": "3", "override_amt": "0"},
        {"unit_id": "p2", "group_id": "gp", "base_a": "2", "base_b": "1", "extra": "1",
         "widget_code": "205", "WIDGET_WEIGHT": "3", "override_amt": "0"},
    ])
    share_p1 = precise["per_unit"]["p1"]["share"]
    assert isinstance(share_p1, Decimal)
    assert share_p1 != share_p1.quantize(Decimal("0.01")), \
        "Decimal deveria preservar precisao total sem arredondamento automatico para 2 casas"
    checks += 1

    # 13. lookup_table_composite -- busca 2D por chave composta (ex.: "setor-posicao"),
    #     equivalente generico a um HLOOKUP/VLOOKUP cuja chave e' uma concatenacao de
    #     dois campos (achado real da Fase 3D, aqui com nomes 100% ficticios)
    ruleset_2d = {
        "inputs": {"sector_code": {}, "slot_code": {}},
        "rules": [
            {"rule_id": "G2D", "output": "slot_factor", "operation": "lookup_table_composite",
             "operands": {"key_source_fields": ["sector_code", "slot_code"], "key_separator": "-",
                          "table": {"1-1": "0.05", "1-2": "0.10", "2-1": "0.02"}}},
        ],
    }
    rs5 = Ruleset(ruleset_2d)
    res5 = ReproductionEngine(rs5).compute([
        {"unit_id": "s1", "group_id": "g1", "sector_code": "1", "slot_code": "1"},
        {"unit_id": "s2", "group_id": "g1", "sector_code": "1", "slot_code": "2"},
        {"unit_id": "s3", "group_id": "g1", "sector_code": "2", "slot_code": "1"},
        {"unit_id": "s4", "group_id": "g1", "sector_code": "9", "slot_code": "9"},  # combinacao ausente
    ])
    assert res5["per_unit"]["s1"]["slot_factor"] == Decimal("0.05")
    assert res5["per_unit"]["s2"]["slot_factor"] == Decimal("0.10")
    assert res5["per_unit"]["s3"]["slot_factor"] == Decimal("0.02")
    assert res5["per_unit"]["s4"]["slot_factor"] is None, "combinacao ausente da tabela nunca deve virar valor inventado"
    # normalizacao: "1.0"/"1" devem produzir a mesma chave (equivalente ao RIGHT()/concat do Excel)
    res5b = ReproductionEngine(rs5).compute([
        {"unit_id": "s5", "group_id": "g1", "sector_code": "1.0", "slot_code": "1.0"},
    ])
    assert res5b["per_unit"]["s5"]["slot_factor"] == Decimal("0.05")
    checks += 1

    # 14. missing_key_defaults -- chave ausente da tabela, mas com default EXPLICITAMENTE
    #     evidenciado (nunca um default generico "qualquer chave ausente vira X") continua
    #     produzindo o valor default; qualquer OUTRA chave ausente sem default continua bloqueada
    ruleset_default = {
        "inputs": {"category_code": {}},
        "rules": [
            {"rule_id": "GD", "output": "category_factor", "operation": "lookup_table",
             "operands": {"key_source_field": "category_code", "table": {"5": "0.20"},
                          "missing_key_defaults": {"3": "0.0"}}},
        ],
    }
    rs6 = Ruleset(ruleset_default)
    res6 = ReproductionEngine(rs6).compute([
        {"unit_id": "d1", "group_id": "g1", "category_code": "5"},
        {"unit_id": "d2", "group_id": "g1", "category_code": "3"},
        {"unit_id": "d3", "group_id": "g1", "category_code": "7"},
    ])
    assert res6["per_unit"]["d1"]["category_factor"] == Decimal("0.20")
    assert res6["per_unit"]["d2"]["category_factor"] == Decimal("0.0"), "chave 3 tem default evidenciado explicito"
    assert res6["per_unit"]["d3"]["category_factor"] is None, "chave 7 nao tem default -- deve continuar bloqueada, nunca 0 por acaso"
    checks += 1

    print(f"OK: {checks} grupos de verificacao passaram (pricing_reproduction_engine, 100% sintetico)")
    return 0


def main(argv=None) -> int:
    try:
        return run()
    except AssertionError as e:
        print(f"FALHOU: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
