# Database v2 — Schema canônico PostgreSQL (Fase 2)

## Objetivo

Traduzir em schema físico o modelo conceitual da Fase 1D
(`data/restricted/audit/preliminary-canonical-model.md`, privado, e
[[10-PRICING-DOMAIN-MODEL]], público), priorizando o **Unit Price
Allocation Engine** (Motor B) — que tem metodologia reconstruída com
evidência de fórmula (Fase 1C) — e criando apenas a fundação mínima
extensível do **Market Pricing Engine** (Motor A), que ainda não tem
nenhuma fonte de dado real.

Este schema **não substitui** `database/schema.sql` (legado). Os dois
coexistem até uma decisão explícita de migração — ver
[[docs/11-DATABASE-V2-DESIGN]] (público) para a estratégia
Legacy → v2 e `data/restricted/audit/database-v2-mapping.md` (privado)
para o mapeamento detalhado dos conceitos observados nas planilhas.

## Ordem de execução

```
001_schemas.sql            -- namespaces core/pricing/audit/market + extensão pgcrypto
002_core.sql                -- developments, towers, unit_typologies, units
003_pricing.sql              -- scenarios, parameter_sets, parameters, calibration_*, runs,
                                vgv_targets, unit_adjustments, unit_price_results,
                                unit_overrides, validations
004_audit.sql                 -- data_sources, data_lineage + FKs pendentes de 002/003
005_market_foundation.sql      -- models, model_versions, predictions + FK pendente de 003
006_indexes.sql                  -- índices
007_views.sql                     -- pricing.v_unit_price_current
008_ingestion.sql                  -- raw.* (fidelidade da fonte) + staging.* (candidatos normalizados) — Fase 3A
009_promotion.sql                    -- audit.promotion_runs + colunas de lineage/idempotência/distinção
                                        -- SYSTEM_CALCULATED vs IMPORTED_REFERENCE — Fase 3B
010_reproduction.sql                   -- audit.reproduction_runs + pricing.reproduction_comparisons +
                                          REPRODUCTION_VALIDATION_RUN — Fase 3C
```

**Por que algumas foreign keys são adicionadas via `ALTER TABLE` em
arquivos posteriores, em vez de inline no `CREATE TABLE`:** `core` e
`pricing` referenciam `audit.data_sources`, mas `audit` só é criado no
arquivo 004 (depois de core/pricing, para manter a numeração pedida
pela Fase 2). Da mesma forma, `pricing.vgv_targets` referencia
`market.predictions`, criado só no arquivo 005. Em vez de reordenar os
arquivos (o que quebraria a numeração solicitada) ou usar uma coluna
sem FK permanentemente, a FK é declarada como uma constraint adicionada
por `ALTER TABLE` no arquivo em que a tabela de destino já existe. Isso
é um padrão comum e seguro em SQL puro — nenhuma dessas colunas fica
sem integridade referencial ao final da execução completa (001→007).

## Separação do legado

- `database/schema.sql` (legado) **não foi tocado** nesta fase.
- O schema v2 vive inteiramente em `database/v2/`, com namespaces
  (`core`, `pricing`, `audit`, `market`) próprios — nenhuma tabela
  compartilha nome com o legado (`developments`/`units`/`data_sources`
  existem nos dois, mas em schemas diferentes: sem prefixo = legado,
  `core.`/`audit.` = v2).
- Nenhuma migração de dado real ou sintético foi executada. Ver
  [[docs/11-DATABASE-V2-DESIGN]], seção "Legacy → V2 Migration
  Strategy", para a classificação REUSE/TRANSFORM/DEPRECATE/
  KEEP_FOR_DEMO de cada elemento do schema atual.

## Decisões de design

### UUID + business key separada da identidade técnica

Toda entidade central tem `id UUID` (identidade técnica,
`gen_random_uuid()`) e uma coluna de chave de negócio separada e única
(`business_key`, ou `unit_code` + composição no caso de unidades — ver
seção "Identidade de unidades" abaixo). Motivo: a Fase 1 encontrou
planilhas onde o código de unidade não é comprovadamente único
isoladamente — separar identidade técnica de chave de negócio evita
que uma limitação da fonte de dado se torne uma limitação estrutural
do banco.

### Identidade de unidades

`core.units` não assume que `unit_code` é globalmente único. A
unicidade é garantida apenas pela composição `(development_id,
tower_id, unit_code)`. Como `tower_id` é opcional (nem toda torre foi
confirmada nas fontes observadas), quando `tower_id` é `NULL` essa
constraint **não** garante unicidade de `unit_code` dentro do
empreendimento — limitação documentada, não uma falha de
implementação (ver comentário na própria coluna, em `002_core.sql`).

### Sem EAV genérico em `core`

Foi avaliada a alternativa de uma tabela `core.unit_attributes`
genérica (chave/valor) em vez de colunas tipadas em `core.units`. A
decisão foi **não criar EAV** para os atributos essenciais e estáveis
já evidenciados (áreas por componente, pavimento, tipologia, vagas,
vista, orientação) — eles são conhecidos, estáveis, e colunas tipadas
preservam integridade (CHECK constraints, tipos corretos) que um EAV
genérico não preservaria sem lógica adicional. Se atributos realmente
variáveis/desconhecidos surgirem no futuro, um EAV pode ser reavaliado
então — não antecipado agora sem necessidade comprovada.

### Parâmetros: colunas tipadas, não uma coluna TEXT única

`pricing.parameters` tem quatro colunas de valor (`numeric_value`,
`text_value`, `boolean_value`, `date_value`) mais `value_type`, com uma
`CHECK` garantindo que exatamente a coluna do tipo declarado esteja
preenchida. Isso evita tanto uma única coluna `TEXT` sem validação de
tipo quanto um modelo genérico demais — é um meio-termo tipado e
validável, sem exigir `JSONB`/serialização.

### Calibrações versionadas, nunca sobrescritas

`pricing.calibration_sets`/`calibration_entries` seguem o mesmo padrão
de `parameter_sets`/`parameters`: versão + janela de validade
(`valid_from`/`valid_to`) + `status`. A variante de ajuste de posição
identificada como dormente numa das fontes analisadas (Fase 1C) é
representável aqui como um `calibration_set` com `status` diferente de
`ACTIVE` — sem apagar nem impedir sua existência.

### Status: `TEXT` + `CHECK`, não `ENUM` nativo

Todas as colunas de status (`scenarios.status`, `parameter_sets.status`,
`calibration_sets.status`, `runs.status`, `vgv_targets.status`,
`model_versions.status`) usam `TEXT` com `CHECK`, não `CREATE TYPE ...
AS ENUM`. Motivo documentado: alterar um `ENUM` do PostgreSQL exige
`ALTER TYPE` (mudança de schema, mais rígida); o vocabulário de status
de um motor de precificação ainda em formação (`DRAFT`/`ACTIVE`/
`SUPERSEDED`/`ARCHIVED`; `PENDING`/`RUNNING`/`COMPLETED`/`FAILED`) tem
chance relevante de precisar de novos valores antes do schema
estabilizar — `CHECK` é mais simples de evoluir.

### Overrides: entidade separada, append-only

`pricing.unit_overrides` nunca é alvo de `UPDATE` para o valor
histórico — cada decisão de override é uma nova linha, com
`previous_price`/`proposed_price`/`final_price`/`reason`/`decided_at`.
A foreign key composta `(run_id, unit_id) → pricing.unit_price_results
(run_id, unit_id)` garante que todo override se refere a um resultado
calculado que de fato existe.

### `SUM(preço final) ≈ VGV alvo`: validação de negócio, não `CHECK`

Essa invariante **não** é uma `CHECK constraint` de linha — ela
depende de agregação entre tabelas e pode divergir legitimamente por
causa de overrides. É registrada como um resultado em
`pricing.validations` (`check_type = 'VGV_RECONCILIATION'`), calculado
pela camada de serviço/pipeline futura, nunca bloqueada pelo banco.

### Invariantes cross-tabela: trigger simples onde compensa, documentação onde não

- `core.units.tower_id` deve pertencer ao mesmo `development_id` da
  unidade — implementado como uma trigger simples (`BEFORE INSERT OR
  UPDATE`, uma única comparação), porque não é expressável como `CHECK`
  de linha e o custo de implementação é baixo.
- "Resultado pertence a uma unidade do mesmo empreendimento da run" e
  "parâmetro usado pertence ao parameter_set da run" cruzam duas ou
  mais tabelas e são deixados como validação de negócio (uma futura
  linha em `pricing.validations`, ou verificação na camada de serviço
  antes do `INSERT`) — implementar isso como trigger seria a
  "trigger complexa" que a Fase 2 pediu para evitar quando uma
  constraint mais simples ou lógica de serviço for suficiente.

## Entidades implementadas

Ver [[docs/11-DATABASE-V2-DESIGN]] para a tabela completa da Fase 2.
Resumo (Fase 2): `core` (4 tabelas), `pricing` (12 tabelas), `audit`
(2 tabelas), `market` (3 tabelas) — 21 tabelas físicas, mais 1 view.
**Fase 3A** adicionou `raw` (4 tabelas: `ingest_batches`, `workbooks`,
`sheets`, `cells`) e `staging` (5 tabelas: `unit_candidates`,
`parameter_candidates`, `calibration_candidates`,
`price_output_candidates`, `mapping_review`) — ver
[[docs/14-PRIVATE-DATA-INGESTION]]. **Fase 3B** adicionou 1 tabela nova
(`audit.promotion_runs`) e colunas em tabelas existentes (nenhuma
tabela nova em `core`/`pricing`/`staging`): lineage/idempotência em
`staging.*_candidates` (`promoted_entity_id`/`promoted_at`),
classificação de revisão em `staging.mapping_review`
(`review_classification`), distinção `SYSTEM_CALCULATED` vs.
`IMPORTED_REFERENCE` em `pricing.runs.run_type` e
`pricing.unit_price_results.result_origin`, `IMPORTED_REFERENCE`
adicionado a `pricing.vgv_targets.origin`, e classificação de
tipologia em `core.unit_typologies.classification` — ver
[[docs/15-STAGING-TO-CANONICAL-PROMOTION]]. **Fase 3C** adicionou 2
tabelas novas (`audit.reproduction_runs`,
`pricing.reproduction_comparisons`) e um terceiro valor
(`REPRODUCTION_VALIDATION_RUN`) em `pricing.runs.run_type` — ver
[[docs/16-INDEPENDENT-PRICING-REPRODUCTION]]. Total agora: 6 schemas,
33 tabelas físicas, 1 view.

## Pendências e decisões adiadas

- **`market.observations`/`comparables`/`transactions`/`listings`**:
  não criadas — nenhuma fonte real existe hoje (ver
  `005_market_foundation.sql`, comentário de topo).
- **`audit.decisions`** (aprovação/revisão humana formal): adiada —
  `pricing.unit_overrides` já cobre a decisão de override em si; um
  fluxo de aprovação separado não tem requisito confirmado ainda.
- **Promoção `staging` → `core`/`pricing`**: implementada na Fase 3B,
  apenas para candidatos `HIGH`/`CANDIDATE` — ver
  [[docs/15-STAGING-TO-CANONICAL-PROMOTION]]. Itens `MEDIUM`/`LOW`
  continuam exclusivamente em `staging.mapping_review`, nunca
  promovidos automaticamente. Nenhuma linha em `market.*` foi criada
  (fora de escopo — Motor A ainda sem fonte real).
- **Atributo de posição/lado (`core.units.position_code`)**: mantido
  genérico (texto livre) porque o significado exato ainda não foi
  confirmado — pergunta bloqueante de schema pendente (equivalente a
  "Q-05" no rastreamento privado da Fase 1C/1D).
- **Frequência de recalibração** (equivalente a "Q-12"): resolvida
  *sem* precisar da resposta — o schema já versiona toda calibração
  por padrão (nunca sobrescreve), então a resposta de Rodolfo vai
  informar a *operação* (com que frequência uma nova versão é criada),
  não a *estrutura* (que já suporta qualquer frequência).
- **Vagas por tipo/combinação** (ex.: vaga livre vs. presa):
  simplificado para uma contagem inteira (`core.units.parking_spaces`)
  nesta fase — a fonte observada tem uma categorização mais rica, que
  pode justificar uma tabela de referência própria numa iteração
  futura, hoje não implementada.
