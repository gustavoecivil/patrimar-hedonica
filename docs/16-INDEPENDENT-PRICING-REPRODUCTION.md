# 16 — Reprodução Independente da Lógica de Precificação

Metodologia pública da Fase 3C. Nenhum conteúdo privado (fórmula
proprietária, constante, parâmetro real, valor, preço, VGV, nome de
arquivo/aba/campo) é reproduzido aqui — ver [[04-DECISIONS]] D4/D6. Os
números e classificações abaixo descrevem a metodologia e seus
resultados de forma sanitizada; o conteúdo real vive exclusivamente em
`data/restricted/` e num banco PostgreSQL privado dedicado.

## Objetivo

Responder, de forma auditável e sem viés de confirmação: dado o
mesmo conjunto de unidades, parâmetros e calibrações já promovidos
(Fase 3B), **conseguimos chegar, de forma independente, ao mesmo
preço que já existe nas planilhas reais?** Esta fase não é o Market
Pricing Engine, não é recomendação de preço, não é modelo hedônico e
não substitui `REFERENCE_ALLOCATION_V1` (D8) — é uma validação de
reprodução de uma metodologia já reconstruída (Fase 1C).

## Separação central: dado importado vs. resultado reproduzido

Todo valor de preço já existente na fonte é `SOURCE_REFERENCE_PRICE`
(`result_origin='IMPORTED_REFERENCE'`, Fase 3B — nunca sobrescrito).
Todo valor produzido pelo motor desta fase é `REPRODUCED_PRICE`
(`result_origin='SYSTEM_CALCULATED'`, `run_type=
'REPRODUCTION_VALIDATION_RUN'` — nunca confundido com
`SYSTEM_RUN`/produção real). A diferença entre os dois
(`DELTA`) é registrada numa tabela de comparação dedicada
(`pricing.reproduction_comparisons`), nunca dentro da tabela de
resultados em si.

## Isolamento do gabarito (anti-vazamento)

O motor de cálculo (`scripts/pricing_reproduction_engine.py`) nunca
recebe, em nenhum ponto da sua API, qualquer referência a preço
importado — ele opera puramente sobre a lista de unidades/insumos que
recebe como argumento. A leitura do preço de referência só acontece
depois que o cálculo já terminou (fase de VALIDAÇÃO, separada
estruturalmente da fase de CÁLCULO no script que orquestra a
execução real). Um teste público sintético prova essa separação.

## Arquitetura: engine genérico + regras privadas

A lógica reconstruída nas Fases 1B/1C é confidencial. Por isso:

- `scripts/pricing_reproduction_engine.py` (público) só sabe executar
  um catálogo pequeno e genérico de operações — soma, soma ponderada,
  fatores multiplicativos, busca em tabela por chave derivada,
  participação proporcional, combinação linear, divisão — todas em
  `decimal.Decimal`, nunca `float`. Não contém nenhuma fórmula,
  constante ou nome real.
- As regras REAIS (quais operações se aplicam a quais campos, com
  quais parâmetros estruturais) vivem exclusivamente em
  `data/restricted/pricing_rules/` (JSON privado, nunca versionado).
  Tabelas de calibração e parâmetros numéricos reais não ficam nem
  no código nem no ruleset — são lidos ao vivo do banco privado
  (dado já promovido na Fase 3B), sempre a partir da mesma fonte de
  verdade.
- `scripts/run_pricing_reproduction.py` (público) é o único ponto que
  conecta o motor genérico ao schema real — também sem nenhuma
  fórmula ou valor privado hardcoded, apenas a lógica de "onde buscar
  cada insumo declarado pelo ruleset".

## Grafo de execução e classificação de regras

Cada regra da metodologia reconstruída foi classificada como
`EXECUTABLE_CONFIRMED`, `EXECUTABLE_WITH_DERIVATION`,
`BLOCKED_BY_AMBIGUITY`, `DORMANT`, `NOT_REQUIRED_FOR_REPRODUCTION` ou
`UNKNOWN` — nunca inventada para preencher uma lacuna. O motor
constrói um grafo de dependências a partir dessas regras, detecta
ciclos e dependências ausentes antes de qualquer execução, e propaga
bloqueio **transitivamente**: uma regra que depende de uma regra
bloqueada nunca é calculada com um valor inventado — fica
explicitamente marcada como bloqueada também.

## `DERIVED_FOR_REPRODUCTION` — e sua retratação

Quando uma variável necessária ao cálculo está disponível na camada
bruta (nunca promovida a atributo oficial por falta de confiança
`HIGH`), ela pode ser usada **só para fins de reprodução**, marcada
`DERIVED_FOR_REPRODUCTION` com evidência, versão e fonte explícitas —
nunca promovida silenciosamente a atributo oficial do modelo
canônico. Esta fase tentou isso para um componente de área que não
havia sido promovido na Fase 3B. A tentativa inicial (por analogia
estrutural entre duas fontes) produziu valores numericamente
implausíveis quando confrontada com os dados reais — a decisão foi
**retratar** a derivação (não forçar um filtro arbitrário para "fazer
funcionar") e documentar o processo completo de tentativa e correção
como evidência, não descartá-lo. Ver seção seguinte.

## Convergência controlada (nunca "achar um fator que bate")

Toda mudança no motor ou no ruleset, entre a primeira execução e a
versão oficial, foi registrada com: o problema encontrado, a
evidência que o comprova, a mudança feita, e a métrica antes/depois.
Nenhuma constante foi ajustada por tentativa e erro para reduzir
divergência contra o preço de referência — as únicas mudanças feitas
nesta fase tornaram o resultado **mais conservador** (menos unidades
com valor calculado), nunca mais favorável a uma comparação
numérica. As execuções anteriores permanecem no banco privado como
histórico, nunca apagadas.

## Precisão numérica

Toda a aritmética usa `decimal.Decimal`. Nenhuma regra de
arredondamento foi imposta por convenção — cada ponto onde a fonte
evidenciadamente arredonda foi tratado conforme a evidência de
fórmula (Fase 1C); onde essa evidência não existe, a incerteza é
registrada explicitamente, nunca resolvida por suposição.

## Classificação do resultado desta execução

`PARTIAL_REPRODUCTION`: parte da metodologia reconstruída foi
reproduzida de ponta a ponta com dado real do banco (uma regra de
busca por calibração, incluindo a derivação de chave e a tabela real
já promovida), mas o preço final permanece bloqueado — não por falha
de compreensão da lógica (as fórmulas envolvidas têm confiança `HIGH`,
confirmadas por leitura direta na Fase 1C), e sim por lacunas de
**disponibilidade de dado**: uma tabela de calibração adicional nunca
foi capturada nas fases anteriores, e um componente de área não pôde
ser confirmado com confiança suficiente. `PARTIAL_REPRODUCTION`
verdadeiro é o resultado deliberadamente preferido a um `100%`
obtido por hipótese não comprovada.

## Overrides

Unidades com ajuste manual não-zero foram inventariadas (contagem
apenas — o valor em si nunca aparece em documentação pública). A
identidade "cálculo antes do override + override = preço final da
fonte" só pode ser validada quando o cálculo antes do override deixar
de estar bloqueado — registrado como trabalho pendente, não simulado.

## Anomalia de fórmula conhecida (Fase 1C)

A anomalia de fórmula já documentada na Fase 1C foi testada como duas
variantes conceituais separadas — `AS_IMPLEMENTED_IN_SOURCE` (replica
o comportamento real da fonte) e `CONSISTENT_RULE_VARIANT` (aplica a
regra de forma uniforme) — sem nunca corrigir silenciosamente a
versão oficial. A execução oficial desta fase sempre reproduz o que a
fonte efetivamente faz, não uma versão "corrigida" por nós.

## Determinismo

A mesma combinação de (lote de origem, versão de mapeamento, versão
de ruleset, parâmetros, calibrações) produz um hash lógico idêntico,
independente de timestamp — confirmado por teste público sintético.

## O que esta fase explicitamente NÃO fez

- Não promoveu nenhum resultado a "produção" — nenhuma API pública,
  nenhuma alteração de frontend ou Netlify.
- Não chamou nenhum resultado de "recomendação".
- Não usou `REFERENCE_ALLOCATION_V1` (D8) sobre dado real.
- Não corrigiu a anomalia de fórmula conhecida — só a testou como
  análise separada.
- Não inventou nenhuma regra, tabela ou valor para preencher uma
  lacuna — toda lacuna encontrada foi documentada, nunca preenchida
  por hipótese.

## Teste público sintético

`scripts/test_pricing_reproduction_engine.py` usa exclusivamente
regras e nomes fictícios, estruturalmente equivalentes ao que a fase
usa de verdade, cobrindo: grafo/ordem topológica, dependência
ausente, ciclo, `Decimal` obrigatório, regra dormente, bloqueio
transitivo, parâmetro, calibração por chave derivada, cálculo sem
qualquer acesso a preço de referência, determinismo (hash lógico
estável), e comportamento de precisão sem arredondamento implícito.
