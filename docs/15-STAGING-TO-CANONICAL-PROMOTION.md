# 15 — Promoção Controlada de Staging para Core/Pricing

Metodologia pública da Fase 3B. Nenhum conteúdo privado (nome de
arquivo, nome de aba, nome de empreendimento, identificador de
unidade, parâmetro, preço, VGV, valor, fórmula, hash privado) é
reproduzido aqui — ver [[04-DECISIONS]] D4/D6. Os números e regras
abaixo descrevem a metodologia e seus resultados de forma sanitizada;
o conteúdo real vive exclusivamente em `data/restricted/` e num banco
PostgreSQL privado dedicado.

## Objetivo

A Fase 3A ingeriu as duas planilhas reais em `raw`/`staging`, mas
nenhuma linha chegou a `core`/`pricing`/`market`. A Fase 3B promove,
de forma controlada e reprodutível, os candidatos de staging com
confiança `HIGH` para as entidades canônicas — **sem calcular nenhum
preço**. Toda a fase gira em torno de uma separação rigorosa: **dado
importado da planilha** nunca pode ser confundido com **resultado
calculado pelo Patrimar Pricing Intelligence**.

## Identidade da promoção (reprodutibilidade)

Cada execução de promoção é identificada por
`(ingest_batch_id, mapping_version)`, registrada em
`audit.promotion_runs` — mesmo padrão de estado
`PENDING`/`RUNNING`/`COMPLETED`/`FAILED` já usado em
`raw.ingest_batches` (Fase 3A), incluindo o mesmo cuidado: o registro
do batch de promoção é criado/comitado **antes** do bloco de escrita
arriscado, para que um `FAILED` real seja possível mesmo após um
rollback completo.

`mapping_version` é derivado deterministicamente do conteúdo do
arquivo de mapeamento privado (hash), nunca de um número escolhido a
mão — duas promoções com o mesmo `mapping_version` usaram exatamente
o mesmo arquivo de mapeamento.

## Política de confiança (reafirmada, não redefinida)

- **`HIGH` + `CANDIDATE`**: o único estado promovido automaticamente.
- **`MEDIUM`/`LOW`**: nunca promovido nesta fase, mesmo que presente
  na mesma execução — permanece em `staging.mapping_review`.
- Um candidato `HIGH`/`CANDIDATE` cujo **valor extraído está vazio**
  (achado real desta fase — nem todo mapeamento `HIGH` garante que a
  célula, na prática, tenha conteúdo) também **não é promovido** —
  fica como candidato pendente para uma promoção futura, sem inventar
  um valor. "Sem valor" é tratado como um estado válido, não como
  erro que aborta a promoção inteira.

## Business keys — nunca o nome do arquivo

Cada `core.developments` promovido recebe uma `business_key`
determinística derivada do hash do arquivo-fonte (nunca do nome do
arquivo, nunca de um nome de empreendimento). Torres e tipologias
reaproveitam, como `business_key`, valores que já eram dados privados
dentro do mesmo banco privado desde a Fase 3A — nenhum dado novo é
exposto, apenas reorganizado dentro do mesmo perímetro de privacidade.

## Distinção obrigatória: `IMPORTED_REFERENCE` vs. `SYSTEM_CALCULATED`

Extensão mínima ao schema v2 (`database/v2/009_promotion.sql`),
aditiva e compatível com todo dado sintético já existente (Fases
2B/2C):

- `pricing.runs.run_type`: `SYSTEM_RUN` (execução real do motor de
  alocação) vs. `IMPORTED_REFERENCE_RUN` (representa uma importação
  histórica de resultados que já existiam numa fonte externa).
- `pricing.unit_price_results.result_origin`: `SYSTEM_CALCULATED`
  (valor produzido por uma run real) vs. `IMPORTED_REFERENCE` (valor
  que já existia na fonte, apenas armazenado para referência/análise —
  as colunas de preço guardam, nesse caso, o valor **importado**,
  nunca um valor recalculado).
- `pricing.vgv_targets.origin` ganhou o valor `IMPORTED_REFERENCE`,
  ao lado dos já existentes `MANUAL`/`MARKET_PRICING_ENGINE`.

Nenhuma linha promovida nesta fase usa `SYSTEM_CALCULATED`/`SYSTEM_RUN`
— **nenhum preço foi calculado por este sistema**. `REFERENCE_ALLOCATION_V1`
(D8) não foi executado sobre dado real.

## Classificação de tipologia

`core.unit_typologies.classification` distingue `OFFICIAL_TYPOLOGY`
(rótulo que existe explicitamente na fonte, com evidência de
cabeçalho) de `DERIVED_GROUPING` (agrupamento que nós inferiríamos,
nunca apresentado como oficial) e `UNKNOWN`. Nenhuma tipologia foi
criada por inferência nesta fase — só as que já existiam como campo
confirmado na fonte.

## Lineage

Cada entidade promovida em `core`/`pricing` recebe uma linha em
`audit.data_lineage` (`entity_schema`/`entity_table`/`entity_id` →
`audit.data_sources`), e cada candidato de staging promovido grava
`promoted_entity_id`/`promoted_at` apontando para a entidade que ele
gerou — dupla trilha de rastreabilidade, sem nenhuma linha órfã
aceita.

## Idempotência e correspondência unidade↔resultado

Reexecutar a promoção para o mesmo `(ingest_batch_id, mapping_version)`
produz `ALREADY_PROMOTED`, sem duplicar nenhuma linha — confirmado
contra um banco real. O casamento entre um resultado de preço
importado e a unidade correspondente usa a posição física de origem
(linha da planilha), nunca apenas o identificador de unidade como
texto — porque esse identificador pode repetir entre subdivisões
diferentes de um mesmo empreendimento (achado da Fase 3A).

## Fila de revisão — classificação de impacto

Itens ainda em `staging.mapping_review` (confiança `MEDIUM`/`LOW`,
nunca promovidos) passaram a ter uma classificação de impacto:
`BLOCKING_CORE`, `BLOCKING_PRICING`, `NON_BLOCKING`, ou
`BUSINESS_CLARIFICATION` — uma priorização de revisão futura, nunca
uma tentativa de adivinhar o significado do campo em si.

## O que esta fase explicitamente NÃO fez

- Não calculou nenhum preço nem reproduziu nenhum resultado por
  fórmula própria — todo valor de preço promovido é uma cópia
  rotulada (`IMPORTED_REFERENCE`) do que já existia na fonte.
- Não converteu nenhuma das regras de negócio reconstruídas na Fase
  1C em código executável real (isso é escopo da Fase 3C).
- Não comparou um cálculo novo contra o resultado do Excel.
- Não promoveu nenhum item `MEDIUM`/`LOW`.
- Não alterou `raw.*` — permanece imutável, evidência de origem.
- Não misturou dados de mais de um `ingest_batch` numa mesma
  promoção.

## Backups privados

Dois checkpoints (`pg_dump`, formato custom) foram criados no banco
privado ao redor desta fase — antes de qualquer escrita em
`core`/`pricing` (`PRE_3B`) e depois da promoção bem-sucedida
(`POST_3B_PRE_REPRODUCTION`) — salvos exclusivamente em
`data/restricted/backups/` (nunca versionados).

## Teste público sintético

`scripts/test_promote_staging_to_core.py` prova o pipeline completo
usando exclusivamente dados fabricados diretamente em `raw`/`staging`
(nunca um workbook ou valor real): promoção de candidatos `HIGH` em
todas as categorias, um candidato com valor vazio corretamente não
promovido, um candidato `MEDIUM` corretamente nunca tocado, lineage
sem órfãos, idempotência, e — como as demais fases — que uma
duplicidade real de identidade é detectada **antes** de qualquer
escrita, a promoção inteira é abortada, e o registro de promoção
correspondente termina `FAILED`, nunca "parcialmente concluído".
Executado com sucesso contra um PostgreSQL real neste ambiente, sem
afetar o cenário sintético de demonstração (Fase 2B/2C) que já existe
no mesmo banco de teste.

## Ferramenta

`scripts/promote_staging_to_core.py` — três modos: `--mode dry-run`
(conta o que seria promovido, sem escrever), `--mode summary`
(relatório read-only de progresso) e `--mode apply` (promove de fato,
numa única transação). Conecta exclusivamente via `psql` e variáveis
de ambiente padrão do libpq; sem nome/valor privado hardcoded; sem
caminho absoluto; idempotente; fail-fast; nunca calcula preço.
