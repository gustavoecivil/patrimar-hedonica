#!/usr/bin/env python3
"""Motor genérico de reprodução independente de metodologia de
precificação (Fase 3C).

Este módulo NÃO contém nenhuma fórmula, constante, parâmetro ou nome
proprietário da Patrimar. Ele só sabe executar um pequeno catálogo de
operações genéricas (soma, soma ponderada, fatores multiplicativos,
busca em tabela de calibração por chave derivada, participação
proporcional, combinação linear, divisão) sobre variáveis declaradas
num "ruleset" — um grafo de regras fornecido em tempo de execução
(tipicamente um arquivo JSON privado, nunca versionado). A forma real
da metodologia (quais operações se aplicam a quais campos, com quais
parâmetros) vem inteiramente do ruleset, não deste arquivo.

Princípios obrigatórios (Fase 3C):
  - Toda aritmética usa `decimal.Decimal` — nunca `float`.
  - O motor nunca lê nem depende de um "preço de referência" durante o
    cálculo (`SOURCE_REFERENCE_PRICE`) — isso pertence exclusivamente à
    fase de VALIDAÇÃO, executada depois e separadamente da fase de
    CÁLCULO (ver `compute()` vs. comparação externa).
  - Uma regra pode ser marcada `status` diferente de `ACTIVE`
    (`BLOCKED_BY_AMBIGUITY`, `DORMANT`, `NOT_REQUIRED_FOR_REPRODUCTION`)
    — nesse caso ela nunca é executada, e qualquer regra que dependa
    dela (direta ou transitivamente) também fica automaticamente
    bloqueada, nunca calculada com um valor inventado.
  - Ciclos e dependências ausentes são detectados antes de qualquer
    execução.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any


class RulesetError(ValueError):
    """Erro de definição do ruleset (ciclo, dependência ausente, operação desconhecida)."""


class BlockedRuleError(RuntimeError):
    """Levantado ao tentar ler o valor de uma variável cuja regra produtora está bloqueada."""


BLOCKING_STATUSES = {"BLOCKED_BY_AMBIGUITY", "DORMANT", "NOT_REQUIRED_FOR_REPRODUCTION", "ANALYSIS_ONLY"}


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError("valor float nao permitido neste motor — use str/int/Decimal (Fase 3C, Passo 11)")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def normalize_key_component(value: Any) -> str | None:
    """Normaliza um componente de chave numérico para texto sem casas
    decimais redundantes (ex.: Decimal('3.0') -> '3') — equivalente
    genérico ao comportamento do Excel ao concatenar um número em
    texto (`RIGHT`/`&` tratam 3.0 como "3", nunca "3.0"). Se o valor
    não for numérico, é devolvido como texto tal como está (permite
    chaves categóricas, não só numéricas)."""
    if value is None:
        return None
    dec = to_decimal(value) if not isinstance(value, Decimal) else value
    if dec is None:
        return str(value)
    if dec == dec.to_integral_value():
        return str(int(dec))
    return format(dec, "f")


def derive_magnitude_prefix_key(raw_value: str, threshold: Decimal, digits_below: int, digits_at_or_above: int) -> str | None:
    """Deriva uma chave de texto a partir dos N primeiros dígitos de um
    valor numérico, onde N depende de um limiar de magnitude — operação
    genérica (equivalente a um IF+LEFT de planilha), parametrizada
    inteiramente pelo ruleset. Não assume nenhuma regra de negócio
    específica além do que os parâmetros descrevem."""
    dec = to_decimal(raw_value)
    if dec is None:
        return None
    digits = str(int(dec)).lstrip("-")
    n = digits_below if dec < threshold else digits_at_or_above
    if not digits or n <= 0:
        return None
    return digits[:n]


class Ruleset:
    """Representação carregada de um ruleset (ver estrutura esperada em
    data/restricted/pricing_rules/ — nunca hardcoded aqui)."""

    def __init__(self, data: dict):
        self.data = data
        self.rules: dict[str, dict] = {r["output"]: r for r in data.get("rules", [])}
        self._validate_graph()

    @classmethod
    def from_file(cls, path: str) -> "Ruleset":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    def version_hash(self, path: str) -> str:
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        return f"sha256:{digest[:16]}"

    def _operand_variable_names(self, rule: dict) -> list[str]:
        names = []
        op = rule["operation"]
        operands = rule.get("operands", {})
        if op in ("sum", "group_sum"):
            names += list(operands.get("fields", []))
        elif op == "weighted_sum":
            names += list(operands.get("base_fields", []))
            if operands.get("weighted_field"):
                names.append(operands["weighted_field"])
        elif op == "multiply_factors":
            names.append(operands["base"])
            names += list(operands.get("factors", []))
        elif op == "lookup_table":
            names.append(operands["key_source_field"])
        elif op == "lookup_table_composite":
            names += list(operands["key_source_fields"])
        elif op == "multiply_by_parameter":
            names.append(operands["field"])
        elif op == "ratio_to_group_total":
            names.append(operands["numerator_field"])
            names.append(operands["group_total_field"])
        elif op == "linear_price":
            names.append(operands["participation_field"])
            names.append(operands["group_value_field"])
            if operands.get("addend_field"):
                names.append(operands["addend_field"])
        elif op == "divide":
            names.append(operands["numerator_field"])
            names.append(operands["denominator_field"])
        elif op == "add":
            names += list(operands.get("fields", []))
        elif op == "passthrough_raw":
            pass
        else:
            raise RulesetError(f"operacao desconhecida: {op!r} (regra {rule.get('rule_id')})")
        return names

    def _validate_graph(self) -> None:
        known_inputs = set(self.data.get("inputs", {}).keys())
        for output, rule in self.rules.items():
            declared_deps = set(rule.get("depends_on_outputs", []))
            operand_vars = set(self._operand_variable_names(rule))
            for v in operand_vars:
                if v in known_inputs:
                    continue
                if v in self.rules:
                    continue
                raise RulesetError(
                    f"regra {rule.get('rule_id', output)}: variavel de entrada {v!r} nao declarada "
                    f"em 'inputs' nem produzida por nenhuma regra"
                )
            missing = operand_vars - known_inputs - set(self.rules.keys())
            if missing:
                raise RulesetError(f"regra {rule.get('rule_id', output)}: dependencia ausente {missing}")

        visiting, visited = set(), set()

        def visit(node: str, path: list[str]):
            if node in visited:
                return
            if node in visiting:
                raise RulesetError(f"ciclo detectado no grafo de regras: {' -> '.join(path + [node])}")
            if node not in self.rules:
                return
            visiting.add(node)
            for dep in self._operand_variable_names(self.rules[node]):
                visit(dep, path + [node])
            visiting.discard(node)
            visited.add(node)

        for output in self.rules:
            visit(output, [])

    def topo_order(self) -> list[str]:
        order: list[str] = []
        visited: set[str] = set()

        def visit(node: str):
            if node in visited or node not in self.rules:
                return
            visited.add(node)
            for dep in self._operand_variable_names(self.rules[node]):
                visit(dep)
            order.append(node)

        for output in self.rules:
            visit(output)
        return order


class ReproductionEngine:
    """Executa um Ruleset sobre um conjunto de unidades, por grupo
    (desenvolvimento). NUNCA recebe nem consulta preço de referência
    durante `compute()` — essa separação é estrutural, não apenas uma
    convenção (a classe não tem nenhum parâmetro para isso)."""

    def __init__(self, ruleset: Ruleset):
        self.ruleset = ruleset

    def compute(self, units: list[dict], group_key: str = "group_id") -> dict:
        """units: lista de dicts com pelo menos os `inputs` declarados no
        ruleset, mais `unit_id` e `group_key`. Retorna
        {unit_id: {variable: Decimal|None}}, mais um bloco 'blocked'
        {variable: motivo} e 'group_values' {group_id: {variable: Decimal}}."""
        order = self.ruleset.topo_order()
        blocked_rules: dict[str, str] = {}
        for output, rule in self.ruleset.rules.items():
            if rule.get("status", "ACTIVE") in BLOCKING_STATUSES:
                blocked_rules[output] = rule.get("status")

        # propaga bloqueio transitivamente
        changed = True
        while changed:
            changed = False
            for output, rule in self.ruleset.rules.items():
                if output in blocked_rules:
                    continue
                deps = self.ruleset._operand_variable_names(rule)
                for d in deps:
                    if d in blocked_rules:
                        blocked_rules[output] = f"BLOCKED_TRANSITIVELY_VIA:{d}"
                        changed = True
                        break

        per_unit: dict[str, dict[str, Decimal | None]] = {}
        group_values: dict[str, dict[str, Decimal]] = {}

        for u in units:
            values: dict[str, Any] = {}
            for k, v in u.items():
                if k in ("unit_id", group_key):
                    continue
                if v is None:
                    values[k] = None
                    continue
                dec = to_decimal(v)
                # mantem o valor original (texto) quando nao for numerico —
                # ex.: chave de unidade usada como fonte de derivacao de
                # chave de calibracao, ou um codigo de posicao categorico.
                values[k] = dec if dec is not None else v
            per_unit[u["unit_id"]] = values

        for output in order:
            rule = self.ruleset.rules[output]
            if output in blocked_rules:
                for uid in per_unit:
                    per_unit[uid][output] = None
                continue
            self._execute_rule(output, rule, units, per_unit, group_values, group_key)

        return {"per_unit": per_unit, "group_values": group_values, "blocked_rules": blocked_rules}

    def _execute_rule(self, output, rule, units, per_unit, group_values, group_key):
        op = rule["operation"]
        operands = rule.get("operands", {})

        if op == "sum":
            for u in units:
                uid = u["unit_id"]
                parts = [per_unit[uid].get(f) for f in operands["fields"]]
                per_unit[uid][output] = None if any(p is None for p in parts) else sum(parts, Decimal(0))

        elif op == "weighted_sum":
            weight_param = operands.get("weight_parameter")
            for u in units:
                uid = u["unit_id"]
                base_parts = [per_unit[uid].get(f) for f in operands.get("base_fields", [])]
                weighted_field = operands.get("weighted_field")
                w_val = per_unit[uid].get(weighted_field) if weighted_field else None
                weight = to_decimal(u.get(weight_param)) if weight_param else Decimal(1)
                if any(p is None for p in base_parts) or (weighted_field and w_val is None) or weight is None:
                    per_unit[uid][output] = None
                    continue
                total = sum(base_parts, Decimal(0))
                if weighted_field:
                    total += w_val * weight
                per_unit[uid][output] = total

        elif op == "multiply_factors":
            for u in units:
                uid = u["unit_id"]
                base = per_unit[uid].get(operands["base"])
                factors = [per_unit[uid].get(f) for f in operands.get("factors", [])]
                if base is None or any(f is None for f in factors):
                    per_unit[uid][output] = None
                    continue
                result = base
                for f in factors:
                    result = result * (Decimal(1) + f)
                per_unit[uid][output] = result

        elif op == "lookup_table":
            table = operands["table"]  # {category_key(str): Decimal}
            key_source_field = operands["key_source_field"]
            derivation = operands.get("derivation")
            row_overrides = operands.get("row_key_overrides", {})  # {unit_id: forced_key}
            # Valores explicitamente evidenciados para chaves cuja célula de
            # fator é vazia na fonte (VLOOKUP/HLOOKUP do Excel trata célula
            # vazia como 0 quando usada como valor de retorno — fato mecânico
            # do Excel, não suposição de negócio). Só se aplica às chaves
            # listadas aqui, nunca a qualquer chave ausente genericamente —
            # cada uma precisa de evidência própria (ex.: valor cacheado de
            # uma célula downstream real confirmando o 0).
            missing_key_defaults = operands.get("missing_key_defaults", {})
            for u in units:
                uid = u["unit_id"]
                raw_key_source = u.get(key_source_field)
                if uid in row_overrides:
                    key = row_overrides[uid]
                elif derivation == "magnitude_prefix":
                    dparams = operands["derivation_params"]
                    key = derive_magnitude_prefix_key(
                        raw_key_source, Decimal(str(dparams["threshold"])),
                        dparams["digits_below"], dparams["digits_at_or_above"],
                    )
                else:
                    key = str(raw_key_source) if raw_key_source is not None else None
                if key is not None and key in table:
                    per_unit[uid][output] = to_decimal(table[key])
                elif key is not None and key in missing_key_defaults:
                    per_unit[uid][output] = to_decimal(missing_key_defaults[key])
                else:
                    per_unit[uid][output] = None

        elif op == "lookup_table_composite":
            # Busca genérica por chave composta (2+ componentes concatenados
            # por um separador) — equivalente a um HLOOKUP/VLOOKUP de
            # planilha cuja chave é montada por concatenação de texto
            # (ex.: `campo_a & "-" & campo_b`). Nenhum componente da chave
            # nem a tabela em si são conhecidos por este motor — vêm
            # inteiramente do ruleset/tabela injetada em runtime.
            table = operands["table"]
            key_fields = operands["key_source_fields"]
            separator = operands.get("key_separator", "-")
            row_overrides = operands.get("row_key_overrides", {})
            for u in units:
                uid = u["unit_id"]
                if uid in row_overrides:
                    key = row_overrides[uid]
                else:
                    components = [normalize_key_component(u.get(f)) for f in key_fields]
                    key = None if any(c is None for c in components) else separator.join(components)
                if key is None or key not in table:
                    per_unit[uid][output] = None
                    continue
                per_unit[uid][output] = to_decimal(table[key])

        elif op == "group_sum":
            totals: dict[str, Decimal] = {}
            any_blocked_group: set[str] = set()
            for u in units:
                gid = u[group_key]
                uid = u["unit_id"]
                val = per_unit[uid].get(operands["fields"][0])
                if val is None:
                    any_blocked_group.add(gid)
                    continue
                totals[gid] = totals.get(gid, Decimal(0)) + val
            for gid, total in totals.items():
                if gid in any_blocked_group:
                    continue
                group_values.setdefault(gid, {})[output] = total
            for uid in per_unit:
                pass  # group_sum nao popula per_unit diretamente

        elif op == "multiply_by_parameter":
            source_field = operands["field"]
            param_key = operands["parameter"]
            for gid, gv in list(group_values.items()):
                base = gv.get(source_field)
                sample_unit = next((u for u in units if u[group_key] == gid), None)
                param_val = to_decimal(sample_unit.get(param_key)) if sample_unit else None
                if base is None or param_val is None:
                    continue
                group_values[gid][output] = base * param_val

        elif op == "ratio_to_group_total":
            numerator_field = operands["numerator_field"]
            group_total_field = operands["group_total_field"]
            for u in units:
                uid = u["unit_id"]
                gid = u[group_key]
                num = per_unit[uid].get(numerator_field)
                denom = group_values.get(gid, {}).get(group_total_field)
                if num is None or denom is None or denom == 0:
                    per_unit[uid][output] = None
                    continue
                per_unit[uid][output] = num / denom

        elif op == "linear_price":
            group_value_field = operands["group_value_field"]
            participation_field = operands["participation_field"]
            addend_field = operands.get("addend_field")
            for u in units:
                uid = u["unit_id"]
                gid = u[group_key]
                share = per_unit[uid].get(participation_field)
                group_val = group_values.get(gid, {}).get(group_value_field)
                addend = per_unit[uid].get(addend_field) if addend_field else Decimal(0)
                if share is None or group_val is None or addend is None:
                    per_unit[uid][output] = None
                    continue
                per_unit[uid][output] = share * group_val + addend

        elif op == "divide":
            for u in units:
                uid = u["unit_id"]
                num = per_unit[uid].get(operands["numerator_field"])
                denom = per_unit[uid].get(operands["denominator_field"])
                if num is None or denom is None or denom == 0:
                    per_unit[uid][output] = None
                    continue
                per_unit[uid][output] = num / denom

        elif op == "add":
            for u in units:
                uid = u["unit_id"]
                parts = [per_unit[uid].get(f) for f in operands["fields"]]
                per_unit[uid][output] = None if any(p is None for p in parts) else sum(parts, Decimal(0))

        elif op == "passthrough_raw":
            pass

        else:
            raise RulesetError(f"operacao desconhecida em execucao: {op!r}")


def logical_hash(result: dict, unit_order: list[str], fields: list[str]) -> str:
    """Hash determinístico do resultado de compute(), independente de
    timestamp — usado para provar determinismo entre execuções (Fase
    3C, Passo 28)."""
    parts = []
    for uid in unit_order:
        row = result["per_unit"].get(uid, {})
        parts.append(uid + "|" + "|".join(
            "" if row.get(f) is None else format(row[f], "f") for f in fields
        ))
    blob = "\n".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
