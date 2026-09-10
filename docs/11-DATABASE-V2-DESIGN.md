# 11 — Database v2 Design

Este documento descreve o schema físico PostgreSQL v2 criado na Fase 2
(`database/v2/`), a partir do modelo conceitual da Fase 1D (ver
[[10-PRICING-DOMAIN-MODEL]]). Não contém nomes de arquivo, nomes de
empreendimento, valores, fórmulas ou parâmetros privados — apenas
estrutura e decisões de modelagem. Detalhe privado (mapeamento das
planilhas para as tabelas físicas) fica em
`data/restricted/audit/database-v2-mapping.md` — ver [[04-DECISIONS]]
D4/D6.

## Reconciliação de contagem (Fase 1D → Fase 2)

O relatório final da Fase 1D informou `ENTIDADES_CANDIDATAS=15`, mas a
lista textual correspondente (seção 4 de
`preliminary-canonical-model.md`) continha 16 nomes de entidade — um
dos 15 itens da lista ("`ParameterSet` / `PricingParameter`") na
verdade nomeava duas entidades distintas num único item. **O número
correto é 16 entidades candidatas**, e é esse número que orientou o
desenho físico desta fase. Este documento e `database/v2/README.md`
não devem voltar a divergir entre si nem do modelo privado — qualquer
alteração futura de contagem deve ser replicada nos dois lugares.

## Escopo desta fase

- **Motor B (Unit Price Allocation Engine)**: schema completo (12
  tabelas em `pricing`), todas as entidades candidatas da Fase 1D
  implementadas.
- **Motor A (Market Pricing Engine)**: apenas fundação mínima e
  extensível (`market.models`, `market.model_versions`,
  `market.predictions`) — nenhuma tabela de comparáveis/transações/
  ofertas foi criada, porque nenhuma fonte real dessas existe hoje em
  nenhuma parte do projeto.
- **Nada foi migrado.** `database/schema.sql` (legado) continua
  intocado e em uso; o schema v2 coexiste em paralelo, em namespaces
  próprios (`core`, `pricing`, `audit`, `market`).
- **Nenhum schema físico foi aplicado a um banco de produção.** O DDL
  foi validado estruturalmente (ver seção "Validação", abaixo) — não
  contra um PostgreSQL real, por não haver um disponível no ambiente
  desta execução.

## Perguntas bloqueadoras de schema (Q-05, Q-12) — como foram tratadas

A Fase 1D classificou duas perguntas pendentes como bloqueadoras de
schema. Nenhuma das duas impediu, de fato, um desenho seguro e
extensível — ambas foram resolvidas modelando para a incerteza, em vez
de codificar uma hipótese não comprovada:

- **Atributo de posição/lado usado numa busca de calibração**: mantido
  como um campo de texto genérico (`core.units.position_code`), sem
  nome de domínio específico e sem `CHECK` de valores permitidos. A
  resposta pendente vai informar como *interpretar* o valor, não como
  *armazená-lo* — o campo já é extensível para qualquer resposta.
- **Frequência de recalibração de uma tabela de referência**: o
  schema já versiona toda calibração por padrão (nunca sobrescreve,
  sempre gera uma nova versão) — independentemente da frequência real,
  a estrutura já suporta desde recalibração diária até uma única vez
  por empreendimento. A resposta pendente vai informar a *operação*,
  não a *estrutura física*.

## Separação em schemas PostgreSQL

| Schema | Papel | Tabelas físicas nesta fase |
|---|---|---|
| `core` | Cadastro físico estável, compartilhado pelos dois motores | 4 |
| `pricing` | Motor B — Unit Price Allocation Engine | 12 |
| `audit` | Proveniência e linhagem de dados | 2 |
| `market` | Fundação mínima do Motor A | 3 |

Total: 21 tabelas físicas + 1 view.

`raw` e `staging` (camadas de ingestão bruta/normalizada) são um plano
**futuro**, documentado mas não implementado — nenhuma tabela
derivada de qualquer planilha privada foi criada nesta fase, em nenhum
schema.

## Decisões de design (resumo — detalhe completo em `database/v2/README.md`)

- **UUID como identidade técnica**, sempre com uma `business_key` (ou
  chave composta) separada e única — resposta estrutural à deficiência
  encontrada na Fase 1 (ausência de chave simples confiável nas fontes
  originais).
- **Sem EAV genérico** para atributos essenciais/estáveis de unidade —
  avaliado e descartado; colunas tipadas preservam integridade que um
  modelo chave/valor genérico não preservaria sem lógica adicional.
- **Parâmetros com colunas tipadas** (`numeric_value`/`text_value`/
  `boolean_value`/`date_value` + `value_type`), não uma única coluna de
  texto sem validação.
- **Calibrações versionadas por padrão** (`valid_from`/`valid_to` +
  `status` + número de versão) — uma variante hoje observada como
  dormente numa das fontes analisadas é representável sem perder
  histórico.
- **`TEXT` + `CHECK`** para todo status, em vez de `ENUM` nativo do
  PostgreSQL — o vocabulário de status ainda deve evoluir, e `CHECK` é
  mais simples de ajustar do que `ALTER TYPE`.
- **Overrides como entidade separada, append-only** — nunca um
  `UPDATE` destrutivo de preço; cada decisão de override é uma nova
  linha, com valor anterior, valor proposto, valor final, motivo e
  timestamp preservados.
- **`SUM(preço final) ≈ VGV alvo` é validação de negócio, não `CHECK`
  de linha** — registrada como dado (`pricing.validations`), porque
  overrides podem legitimamente criar desvio entre o calculado e o
  final.
- **NUMERIC, nunca FLOAT**, para todo valor monetário, área, fator ou
  percentual — com precisão documentada por coluna em
  `database/v2/README.md`.
- **Uma trigger simples** (não complexa) garante que uma unidade só
  referencie uma torre do mesmo empreendimento — invariante que não é
  expressável como `CHECK` de linha, mas é barata de garantir. Outras
  invariantes que cruzam mais tabelas ficam como validação de negócio
  documentada, não como trigger.

## Legacy → V2 Migration Strategy

Nenhuma migração de dado foi executada nesta fase. Classificação de
cada elemento do schema atual (`database/schema.sql`) quanto ao seu
futuro:

| Elemento legado | Classificação | Nota |
|---|---|---|
| `data_sources` (tabela + `origin_type`) | **REUSE** (conceito) | Reaproveitado como `audit.data_sources` — mesmo conceito, novo namespace/schema. |
| `developments` | **TRANSFORM** | Conceito mantido em `core.developments`, mas a estratégia de identidade muda: chave natural como PK (legado) → UUID técnico + `business_key` separada (v2). |
| `units` | **TRANSFORM** | Conceito mantido em `core.units`, com decomposição de área em componentes (fechada/varanda/dependência/terraço) — mais granular que a área única do legado, para suportar o Motor B. |
| `unit_price_observations` | **TRANSFORM** | O conceito de "observação de preço no tempo" se desdobra em `pricing.unit_price_results` (resultado sistemático por run) + `pricing.unit_overrides` (decisão humana) — separação que o legado não tinha. |
| `v_hedonic_model` (view) | **KEEP_FOR_DEMO** | Continua servindo o laboratório hedônico sintético (Motor A/protótipo) inalterada; não foi modelada uma equivalente v2 nesta fase — o Motor A ainda não tem dado real para justificar isso. |
| Geração sintética (`generateSampleData`, seed CSV) | **KEEP_FOR_DEMO** | Continua útil como prova de conceito e teste funcional do modelo hedônico legado; não é a fonte de verdade da Fase 2. |

Nenhum elemento foi classificado como puro **DEPRECATE** nesta fase —
mesmo o que muda de estratégia (developments/units) mantém o conceito
subjacente; nada foi identificado como totalmente descartável ainda.

## Validação do DDL

Sem PostgreSQL nem Docker disponíveis no ambiente desta execução, a
validação foi feita com uma ferramenta genérica
(`scripts/validate_db_v2.py`, biblioteca padrão do Python apenas) que
confirma, sobre os arquivos `.sql`: existência e ordem dos arquivos,
ausência de `DROP` destrutivo, convenção `snake_case`, e que toda
referência (`REFERENCES` inline ou `ALTER TABLE ... FOREIGN KEY`)
aponta para um `schema.tabela` já conhecido no ponto da execução —
incluindo o padrão de FK adicionada em arquivo posterior via `ALTER
TABLE`. Um teste de fumaça sintético
(`scripts/test_validate_db_v2.py`) confirma que a ferramenta detecta
de fato problemas de referência para frente, nomenclatura fora do
padrão, e `DROP` destrutivo — não apenas que ela aprova arquivos
válidos.

## Extensões pós-Fase 2 (Fases 3A/3B)

Este documento descreve o schema como desenhado na Fase 2. Duas
extensões aditivas e genéricas foram feitas depois, sem alterar
nenhuma decisão acima:

- **Fase 3A** (`database/v2/008_ingestion.sql`): schemas `raw`/
  `staging` — ver [[14-PRIVATE-DATA-INGESTION]].
- **Fase 3B** (`database/v2/009_promotion.sql`): `audit.promotion_runs`
  + colunas de lineage/idempotência em `staging.*`, e a distinção
  `pricing.runs.run_type`/`pricing.unit_price_results.result_origin`
  entre `SYSTEM_CALCULATED` (uma execução real do motor de alocação)
  e `IMPORTED_REFERENCE` (um valor que já existia numa fonte externa,
  apenas armazenado para referência) — ver
  [[15-STAGING-TO-CANONICAL-PROMOTION]] e [[04-DECISIONS]] D11. Ambas
  as extensões são aditivas (novas tabelas/colunas com `DEFAULT`) e
  não alteraram nenhuma linha do cenário sintético de demonstração já
  existente (Fases 2B/2C), reconfirmado por execução real.

## Onde fica o detalhe privado

O mapeamento de conceitos observados nas planilhas privadas para as
tabelas físicas v2 (ex.: qual coluna real corresponde a qual campo
físico) está em `data/restricted/audit/database-v2-mapping.md` — nunca
neste documento nem em nenhum arquivo `.sql`.
