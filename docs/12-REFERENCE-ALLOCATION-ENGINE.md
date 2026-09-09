# 12 — Reference Allocation Engine (REFERENCE_ALLOCATION_V1)

> **Esta implementação não representa a metodologia proprietária da
> Patrimar.** É uma implementação de referência, pública e 100%
> sintética, criada na Fase 2B apenas para provar que o schema
> PostgreSQL v2 (`database/v2/`, Fase 2) é capaz de representar um
> ciclo completo de distribuição de VGV entre unidades — dados,
> parâmetros, unidades e cenário são inteiramente fictícios.

## Objetivo

A Fase 1C reconstruiu, com evidência, a lógica de precificação real
das planilhas de Rodolfo — mas esse conhecimento é privado por
definição (ver [[09-PRICING-LOGIC-REVERSE-ENGINEERING]]) e não pode
aparecer em código público. Para provar que o **schema físico**
desenhado na Fase 2 (não a fórmula privada) funciona de ponta a ponta,
esta fase implementa um algoritmo alternativo, simples e didático,
com dados inteiramente fictícios.

## Algoritmo REFERENCE_ALLOCATION_V1

```
weighted_area      = private_area + uncovered_area * uncovered_area_factor
adjustment_weight  = weighted_area * floor_factor * position_factor
participation      = adjustment_weight / SUM(adjustment_weight)
system_price        = target_vgv * participation   (arredondado)
price_per_m2         = system_price / private_area
```

- `uncovered_area_factor` é um parâmetro único do cenário
  (`pricing.parameters`, chave `UNCOVERED_AREA_FACTOR`).
- `floor_factor` e `position_factor` vêm de tabelas de calibração
  (`pricing.calibration_sets`/`calibration_entries`), com dimensões
  `FLOOR_BAND` (faixas `LOW`/`MID`/`HIGH`) e `POSITION_CATEGORY`
  (categorias `A`/`B`/`C`/`D`) — multiplicadores em torno de `1.00`
  (sem prêmio) até `1.10` (prêmio de 10%), valores didáticos.

Este algoritmo foi escolhido por ser estruturalmente análogo ao tipo
de cálculo evidenciado na Fase 1C (área ponderada → ajuste por
pavimento/posição → rateio proporcional → preço), mas com fórmula,
parâmetros e calibrações **inteiramente diferentes e públicos** — não
é uma cópia, adaptação ou aproximação da metodologia real.

## Dados 100% sintéticos

Cenário de demonstração (`fixtures/v2/reference_allocation_scenario.json`,
a fonte única de verdade desta fase):

- 1 empreendimento fictício (`DEMO-ALLOCATION-001`);
- 2 torres, 4 tipologias, 40 unidades — geradas por fórmula
  determinística (índice da unidade mod N), nunca por sorteio;
- 1 parâmetro (`UNCOVERED_AREA_FACTOR = 0.40`);
- 2 conjuntos de calibração (pavimento, posição), com fatores
  simples e claramente didáticos;
- 1 VGV-alvo redondo e fictício (R$ 10.000.000,00), com nota de
  origem `SYNTHETIC_MANUAL_TARGET` — a coluna física `origin` do
  schema v2 continua usando o vocabulário `MANUAL`/
  `MARKET_PRICING_ENGINE` definido na Fase 2; `SYNTHETIC_MANUAL_TARGET`
  é só um rótulo de metadado da fixture, não um valor físico novo.

Nenhum valor, fórmula ou nome deste cenário foi copiado das planilhas
privadas — ver verificação explícita na seção "Proteção de dados
privados", abaixo.

## Fluxo de artefatos (fonte única de verdade)

```
fixtures/v2/reference_allocation_scenario.json   (ÚNICA fonte de verdade)
        │
        ├─ scripts/reference_allocation_engine.py   (cálculo puro)
        │
        └─ scripts/generate_v2_seed.py   (orquestra o motor + gera:)
                ├─ database/v2/seeds/001_demo_allocation.sql
                ├─ fixtures/v2/reference_allocation_expected.json
                └─ fixtures/v2/reference_allocation_report.md
```

Os três artefatos derivados **nunca são editados manualmente** — toda
mudança de comportamento parte da fixture e/ou do motor, e os
derivados são regenerados executando `scripts/generate_v2_seed.py`.

## Determinismo

O motor não usa nenhuma fonte de aleatoriedade (nem `random`, nem
horário do sistema nas contas) e não mantém estado global. O mesmo
cenário de entrada produz sempre a mesma saída, incluindo um hash
lógico SHA-256 (`logical_hash`) calculado sobre um JSON canônico dos
resultados — participação, preços e fatores por unidade — nunca sobre
timestamps. `scripts/test_reference_allocation_engine.py` confirma
isso executando o mesmo cenário duas vezes e comparando o hash.

## Precisão monetária e arredondamento

Toda decisão monetária usa `decimal.Decimal` (nunca `float`).
Participações e fatores intermediários usam alta precisão (até serem
convertidos em preço); preços finais são arredondados a centavos com
`ROUND_HALF_UP`.

### Fechamento do VGV (resíduo de arredondamento)

Arredondar 40 preços independentes e depois somá-los quase nunca bate
exatamente com o VGV-alvo (diferença de alguns centavos, para mais ou
para menos). A referência resolve isso deterministicamente:

1. calcula e arredonda o preço de todas as unidades;
2. calcula a diferença entre a soma arredondada e o VGV-alvo;
3. aplica essa diferença à unidade de **maior participação** no
   cenário (empate: menor `unit_code`, ordem lexicográfica) — regra
   técnica desta referência, documentada aqui, **não uma regra de
   negócio Patrimar**.

Resultado: `SUM(system_calculated_price) == target_vgv`, exatamente,
sempre — verificado como `pricing.validations` (`check_type =
'VGV_RECONCILIATION'`, `severity = 'INFO'`) em cada run gerado.

**Efeito colateral conhecido e documentado:** a unidade que absorve o
resíduo carrega um ajuste de arredondamento específico daquele VGV —
por isso, ao comparar o mesmo cenário com um VGV diferente, essa
unidade específica não escala exatamente proporcional (as demais
escalam). Isso é esperado e coberto pelos testes.

## Overrides

Uma segunda execução (`RUN-WITH-OVERRIDE`) demonstra o override
humano sobre uma unidade específica, sem nunca alterar o preço
sistemático já calculado (`pricing.unit_price_results` permanece
intocado — o override é sempre um evento novo em
`pricing.unit_overrides`, nunca um `UPDATE`):

```
SYSTEM_CALCULATED_PRICE  →  HUMAN_OVERRIDE  →  FINAL_PRICE
```

O relatório de execução mostra explicitamente o impacto, sem esconder
a diferença:

- `TARGET_VGV` (VGV-alvo do cenário);
- `SYSTEM_VGV` (soma dos preços sistemáticos — sempre igual ao alvo,
  por construção);
- `FINAL_VGV` (após o override — `SYSTEM_VGV + impacto do override`);
- `VGV_DELTA_AFTER_OVERRIDE` (o próprio impacto).

Esta fase **prova que o sistema detecta e expõe o impacto** de um
override sobre o VGV total — ela não decide (nem deveria decidir)
qualquer regra comercial de rebalanceamento das demais unidades depois
de um override. Isso continua sendo uma decisão de negócio futura, não
tomada aqui.

## Validações e rastreabilidade

Cada run gera uma linha em `pricing.validations` (reconciliação de
VGV) e cada unidade tem, em `pricing.unit_adjustments`, um registro
por etapa do cálculo (ponderação de área, prêmio de pavimento, prêmio
de posição), cada um referenciando explicitamente o parâmetro ou a
entrada de calibração que originou o fator aplicado
(`parameter_id`/`calibration_entry_id`) — permitindo reconstruir "como
se chegou nesse preço" sem depender de nenhuma fórmula externa.

## Testes

`scripts/test_reference_allocation_engine.py` cobre, entre outros:
soma das participações, fechamento exato do VGV, ausência de preços/
participações negativos, determinismo (mesmo input → mesmo output e
mesmo hash), sensibilidade a mudança de parâmetro/calibração,
comportamento de override (não altera histórico, calcula impacto
corretamente), e falha explícita sobre dados inválidos (torre
inexistente, parâmetro ausente, VGV negativo, override em unidade
inexistente). `scripts/validate_db_v2.py` foi estendido nesta fase
para também validar o seed SQL gerado contra o DDL — tabelas/colunas
existem, nenhuma coluna `GENERATED` recebe `INSERT` explícito, colunas
obrigatórias presentes, e toda foreign key é resolvível na ordem em
que as linhas aparecem no arquivo.

## Proteção de dados privados

Todo artefato desta fase (`fixtures/v2/`, `database/v2/seeds/`,
`scripts/reference_allocation_engine.py`,
`scripts/generate_v2_seed.py`) foi verificado por busca textual contra
os nomes, hashes e magnitudes de parâmetro observados privadamente nas
Fases 1B/1C — nenhuma ocorrência encontrada. Nada de
`data/restricted/` foi copiado para nenhum arquivo público desta fase.

## Limitações

- O algoritmo é deliberadamente simples — não modela, por exemplo,
  múltiplos modos de ajuste de posição (a metodologia real tem um
  mecanismo dormente para isso, não replicado aqui) nem qualquer
  seleção de comparáveis de mercado (isso é escopo do Market Pricing
  Engine, Motor A, ainda sem fundação de dado real — ver
  [[10-PRICING-DOMAIN-MODEL]]).
- Esta fase não executa o DDL contra um PostgreSQL real (ver
  [[11-DATABASE-V2-DESIGN]]) — a validação do seed é estrutural
  (`scripts/validate_db_v2.py`), não uma execução de fato. Isso é
  explicitamente o objetivo da próxima fase.
- O resíduo de arredondamento sempre recai sobre a unidade de maior
  participação — uma escolha técnica desta referência, não uma regra
  de negócio a ser assumida em qualquer implementação real futura.
