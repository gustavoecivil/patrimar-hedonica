# 05 — Worklog

Registro cronológico de execuções relevantes. Entradas mais recentes no
topo. Cada agente que fizer trabalho relevante no projeto deve adicionar
uma entrada aqui.

---

## 2026-09-10 — Fase 3C: Reprodução independente da lógica de precificação (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** reproduzir, fora do Excel, os preços já importados (Fase
3B) a partir das unidades/parâmetros/calibrações reais já promovidos
— sem calcular nada por hipótese, sem misturar dado importado com
resultado calculado, e sem nunca deixar o motor de cálculo acessar o
preço de referência antes de terminar. Ver [[04-DECISIONS]] D11/D12 e
[[16-INDEPENDENT-PRICING-REPRODUCTION]].

**Arquitetura:** motor genérico público
(`scripts/pricing_reproduction_engine.py`, catálogo pequeno de
operações Decimal — soma, soma ponderada, busca por chave derivada,
combinação linear, etc., sem nenhuma fórmula/constante/nome real) +
ruleset privado (`data/restricted/pricing_rules/`, nunca versionado,
com a metodologia real reconstruída na Fase 1C) + runner que conecta
os dois ao schema real (`scripts/run_pricing_reproduction.py`).

**Extensão de schema aditiva** (`database/v2/010_reproduction.sql`,
reconfirmada compatível com o cenário sintético já existente):
`pricing.runs.run_type` ganha `REPRODUCTION_VALIDATION_RUN`;
`audit.reproduction_runs` (mesmo padrão de estado de
`raw.ingest_batches`/`audit.promotion_runs`, identificado por
`development_id`+`ruleset_version`); `pricing.reproduction_comparisons`
(separa `source_reference_price`/`reproduced_price`/`delta` sem nunca
sobrescrever o resultado importado).

**Resultado agregado (números apenas, sem conteúdo):**

| Item | Resultado |
|---|---|
| Classificação final | `PARTIAL_REPRODUCTION` |
| Unidades total / com preço reproduzido / bloqueadas | 884 / 0 / 884 |
| Regra reproduzida de ponta a ponta com dado real | 1 (busca por calibração — 880/884 unidades; 4 bloqueadas por ausência real de fator na fonte, não por bug) |
| Regra central bloqueando o preço final | matriz de calibração adicional nunca capturada nas fases anteriores (lacuna de pipeline, não de lógica) — confiança da fórmula em si: HIGH |
| Overrides inventariados (não validados — cálculo-base bloqueado) | 188/884 unidades com ajuste não-zero |
| Anomalia de fórmula conhecida (Fase 1C) | testada como 2 variantes separadas — resultado idêntico neste conjunto de dados, nunca corrigida silenciosamente |
| Isolamento do preço de referência durante o cálculo | confirmado estruturalmente (teste público) |
| Determinismo | confirmado (hash lógico idêntico entre reexecuções) |
| Idempotência | confirmada contra PostgreSQL real (`ALREADY_REPRODUCED`, 0 linhas novas) |

**Achado real e processo de convergência controlada** (documentado
integralmente em `data/restricted/audit/reproduction-change-log.md`,
issue/evidência/mudança/métrica antes-depois, nunca "ajuste para
bater"): uma tentativa de usar 2 componentes de área ainda não
promovidos (disponíveis só em `raw.cells`, nunca em `core.units`)
produziu valores implausíveis quando testada contra o dado real (3
tentativas, 3 `ruleset_version` distintas, todas preservadas no banco
como histórico) — a decisão final foi retratar essa derivação
inteiramente, nunca inventar um filtro para forçar um resultado
plausível.

**Ferramentas criadas:** `scripts/pricing_reproduction_engine.py`
(motor genérico); `scripts/run_pricing_reproduction.py` (runner
contra o schema real); `scripts/test_pricing_reproduction_engine.py`
(12 verificações, 100% sintético — DAG, ciclo, dependência ausente,
`Decimal`, regra dormente, bloqueio transitivo, isolamento do preço
de referência, determinismo).

**Artefatos privados criados** (todos em `data/restricted/`, nunca
versionados): `pricing_rules/reproduction_rules_v1.json`;
`audit/reproduction-run-summary.md`, `reproduction-results.csv`,
`reproduction-differences.csv`, `reproduction-rule-trace.csv`,
`reproduction-metrics.csv`, `reproduction-change-log.md`,
`questions-for-rodolfo-shortlist-3c.md`;
`backups/private_dev_POST_3C_REPRODUCTION_*.dump`.

**Documentação pública criada/atualizada:**
[[16-INDEPENDENT-PRICING-REPRODUCTION]] (novo); [[04-DECISIONS]] (D12,
nova); [[03-ROADMAP]], [[07-DATA-DICTIONARY]] (referências
sanitizadas).

**Verificação de segurança:** nenhuma fórmula, constante ou valor
real em código público; nenhuma senha/dump/ruleset versionado;
`data/restricted/` confirmado não rastreado; busca textual nos
artefatos novos contra nomes/hashes privados conhecidos — nenhuma
ocorrência.

**Testes:** `scripts/test_pricing_reproduction_engine.py` (12/12) —
**PASSOU**; `test_promote_staging_to_core.py` (12/12, reconfirmado),
`test_ingest_xlsx_postgres.py` (19/19, reconfirmado),
`test_reference_allocation_engine.py` (21/21) — **PASSOU**;
`validate_db_v2.py` (10 arquivos de DDL + seed) — **PASSOU**;
`test_validate_db_v2.py` — **PASSOU**; `verify_postgres_v2.py` contra
`patrimar_pricing_v2_test` — **PASSOU** (banco sintético confirmado
intacto, hash lógico idêntico, mesmo após a extensão de schema 010
aplicada nele também); `npm run test:model` — **PASSOU**.
`database/schema.sql`, `index.html`,
`netlify/functions/hedonic-data.mts` e as migrations Netlify
existentes confirmados sem alteração.

**Estado final:** `patrimar_pricing_v2_private_dev` agora tem 3
execuções de reprodução registradas (histórico de convergência
preservado), a oficial marcada `COMPLETED` com 0 preços reproduzidos
e 884 comparações `BLOCKED` documentadas por causa.
`patrimar_pricing_v2_test` permanece intacto.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 3B: Mapeamento controlado de staging para core/pricing (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** promover, no mesmo banco privado da Fase 3A
(`patrimar_pricing_v2_private_dev`), os candidatos de staging com
confiança `HIGH` para `core.*`/`pricing.*` — sem calcular nenhum
preço, e com separação explícita entre dado importado da planilha e
resultado calculado pelo sistema. Ver [[04-DECISIONS]] D11 e
[[15-STAGING-TO-CANONICAL-PROMOTION]].

**Checkpoints privados:** `pg_dump` (formato custom) antes
(`PRE_3B`) e depois (`POST_3B_PRE_REPRODUCTION`) da promoção, em
`data/restricted/backups/` (nunca versionado).

**Extensão de schema** (`database/v2/009_promotion.sql`, aditiva,
reconfirmada compatível com o cenário sintético já existente):
`audit.promotion_runs` (mesmo padrão de estado de
`raw.ingest_batches`); `promoted_entity_id`/`promoted_at` em
`staging.*_candidates`; `review_classification` em
`staging.mapping_review`; `pricing.runs.run_type` e
`pricing.unit_price_results.result_origin` distinguindo
`SYSTEM_CALCULATED` de `IMPORTED_REFERENCE`; `IMPORTED_REFERENCE`
adicionado a `pricing.vgv_targets.origin`; `classification` em
`core.unit_typologies`.

**Identidade da promoção:** `(ingest_batch_id, mapping_version)` —
`mapping_version` derivado do hash do conteúdo do arquivo de
mapeamento privado, nunca de um número escolhido a mão.

**Resultado agregado (números apenas, sem conteúdo):**

| Item | Resultado |
|---|---|
| Desenvolvimentos criados | 2 (business_key derivada do hash do workbook, nunca do nome do arquivo) |
| Torres / tipologias | 5 / 2 (ambas só num dos 2 desenvolvimentos — não inventadas para o outro) |
| Unidades: candidatas / promovidas / rejeitadas / colisões | 884 / 884 / 0 / 0 |
| Parâmetros: candidatos / promovidos / não promovidos (valor vazio) | 8 / 4 / 4 |
| Calibrações: candidatas / promovidas / não promovidas (ausência real na fonte) | 31 / 29 / 2 |
| Resultados de preço importados promovidos | 884 (100% `result_origin='IMPORTED_REFERENCE'`, 0% `SYSTEM_CALCULATED`) |
| VGV-alvo criado | 0 (nenhum candidato HIGH disponível — não inventado) |
| Linhas de lineage / órfãs | 1.803 / 0 |
| Reconciliação privada (soma de preços importados vs. VGV final já na fonte) | diferença < R$ 0,20 em bases de R$ 195M/262M — explicável por arredondamento |
| Idempotência (reexecução completa) | `ALREADY_PROMOTED`, 0 linhas novas |
| Fila de revisão classificada por impacto | 13 itens: 3 `BLOCKING_CORE`, 2 `BLOCKING_PRICING`, 4 `BUSINESS_CLARIFICATION`, 4 `NON_BLOCKING` |

**Achados reais durante a promoção** (investigados contra `raw.cells`,
nunca corrigidos por invenção):
1. 2 parâmetros (`CALIBRATION_LOOKUP_COLUMN_INDEX`, um por workbook)
   vieram vazios porque a extração de célula única do pipeline da Fase
   3A só lia `raw_value`, não `cached_value` — a célula é, na
   prática, uma fórmula. Mesma classe de bug já corrigida para
   extração em massa na Fase 3A, agora também corrigida para célula
   única em `scripts/ingest_xlsx_postgres.py`. Os 2 valores já
   staged não foram retroativamente corrigidos nesta fase — ficam
   como candidatos prontos para uma promoção futura.
2. 2 parâmetros (`POSITION_ADJUSTMENT_MODE`) vieram vazios porque a
   célula referenciada no mapeamento privado não existe em
   `raw.cells` para nenhum dos dois workbooks — gap de mapeamento
   registrado, não investigado a fundo nesta fase.
3. 2 entradas de calibração vieram sem fator porque a célula
   correspondente está genuinamente ausente na fonte (não é fórmula
   nem vazio-com-fórmula, é ausência real) — preservado como
   anomalia, não corrigido (mesmo espírito da anomalia PR-018/Fase
   1C).
4. Bug de infraestrutura em `run_query_csv` (usado por
   `ingest_xlsx_postgres.py` e `promote_staging_to_core.py`):
   `csv.DictReader` descartava silenciosamente qualquer linha de
   resultado inteiramente vazia — o que ocorre quando uma consulta
   seleciona 1 única coluna com valor `NULL`. Corrigido usando
   `csv.reader` com pareamento manual ao cabeçalho. Não afetou nenhum
   dado já promovido (nenhuma consulta da promoção real usava esse
   padrão); encontrado e corrigido via o teste sintético público.

**Ferramentas criadas:** `scripts/promote_staging_to_core.py`
(`--mode dry-run/summary/apply`; reaproveita `ingest_xlsx_postgres.py`;
idempotente; fail-fast; nunca calcula preço);
`scripts/test_promote_staging_to_core.py` (teste público de
integração contra PostgreSQL real, cenário 100% sintético — 12
verificações, incluindo idempotência e rollback com marcação
`FAILED` sobre uma duplicidade real). `database/v2/db_v2_apply.ps1`
atualizado para incluir `009_promotion.sql`.

**Artefatos privados criados** (todos em `data/restricted/`, nunca
versionados): `audit/core-pricing-promotion-report.md`,
`audit/core-pricing-profile.csv`,
`backups/private_dev_PRE_3B_*.dump`,
`backups/private_dev_POST_3B_PRE_REPRODUCTION_*.dump`.

**Documentação pública criada/atualizada:**
[[15-STAGING-TO-CANONICAL-PROMOTION]] (novo); [[04-DECISIONS]] (D11,
nova); [[03-ROADMAP]], [[07-DATA-DICTIONARY]],
[[11-DATABASE-V2-DESIGN]] (referências sanitizadas).

**Verificação de segurança:** nenhuma senha versionada; nenhum
`.env`/dump rastreado; `data/restricted/` confirmado não rastreado;
busca textual nos artefatos novos contra nomes/hashes privados
conhecidos das fases anteriores — nenhuma ocorrência.

**Testes:** `scripts/test_promote_staging_to_core.py` (12/12, contra
PostgreSQL real) — **PASSOU**; `scripts/test_ingest_xlsx_postgres.py`
(19/19, reconfirmado após a correção do `run_query_csv`) — **PASSOU**;
`validate_db_v2.py` (9 arquivos de DDL + seed) — **PASSOU**;
`test_validate_db_v2.py`, `test_reference_allocation_engine.py`
(21/21) — **PASSOU**; `verify_postgres_v2.py` contra
`patrimar_pricing_v2_test` — **PASSOU** (banco sintético confirmado
intacto, hash lógico idêntico, mesmo depois da extensão de schema
009 aplicada nele também); `npm run test:model` — **PASSOU**.
`database/schema.sql`, `index.html`,
`netlify/functions/hedonic-data.mts` e as migrations Netlify
existentes confirmados sem alteração.

**Estado final:** `patrimar_pricing_v2_private_dev` agora tem 2
desenvolvimentos reais promovidos em `core`/`pricing`, todos os
resultados de preço marcados `IMPORTED_REFERENCE`; `raw.*`
inalterado; `staging.*` enriquecido com lineage de promoção, nunca
alterado destrutivamente. `patrimar_pricing_v2_test` permanece
intacto.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 3A: Ingestão controlada das planilhas reais em RAW/STAGING PostgreSQL (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** carregar, por primeira vez, as duas planilhas reais de
Rodolfo (recebidas na Fase 1A/1A.1, auditadas na Fase 1B, com lógica
reconstruída na Fase 1C) para um banco PostgreSQL — **local e
privado, separado do banco sintético de teste** (ver [[04-DECISIONS]]
D10). Destino exclusivo: schemas genéricos `raw`/`staging`. Nenhuma
linha inserida em `core`/`pricing`/`market`; nenhum preço calculado
ou reproduzido; nenhuma constraint definitiva criada em `core`.

**Ambiente:** banco novo `patrimar_pricing_v2_private_dev` (mesmo
PostgreSQL 18.4 local já usado na Fase 2C), role dedicada, senha
gerada localmente nesta sessão (nunca reutilizada, nunca impressa em
nenhum log/relatório), credenciais só em
`.env.pricing_v2_private_dev` (local, `.gitignore`). DDL 001-008
aplicado do zero — banco iniciado sem nenhum dado sintético (a seed
de demonstração da Fase 2B NÃO foi aplicada aqui).

**Resultado agregado (números apenas, sem conteúdo):**

| Item | Resultado |
|---|---|
| Workbooks/abas ingeridos | 2 / 8 |
| Células/fórmulas ingeridas | 25.023 / 18.377 — **reconciliação exata** com o inventário estrutural da Fase 1B |
| Reingestão do mesmo arquivo (2×, incluindo verificação final dedicada) | `ALREADY_INGESTED`, 0 linhas novas em ambas as tentativas |
| Amostragem determinística de fidelidade | 263 células verificadas, 0 divergências |
| Entradas no mapeamento de campos | 27 (14 `HIGH`, 11 `MEDIUM`, 2 `LOW`) |
| Candidatos de staging populados (a partir de `HIGH` apenas) | 884 unidade + 884 resultado de preço + 8 parâmetro + 31 calibração |
| Registros em revisão (`MEDIUM`/`LOW`, nunca convertidos automaticamente) | 13 (2 `UNMAPPED`, 11 `REVIEW_REQUIRED`) |
| Linhas de staging órfãs (sem linhagem até `raw.*`) | 0 |
| Avaliação de chave candidata | confirma, com evidência real, que um identificador de negócio isolado não é suficiente como chave num dos dois workbooks (precisa de chave composta); no outro workbook, é suficiente isoladamente — consistente com a decisão de schema já tomada na Fase 2 |
| Reconciliação entre os dois workbooks | estrutura e conteúdo (não nome/data) apontam para desenvolvimentos distintos usando a mesma metodologia — confiança média-alta, registrada privadamente |

**Bug real encontrado e corrigido durante a extração para staging**
(só detectável executando contra dado real): uma coluna de
identificador de unidade, aparentemente digitada manualmente, é na
maior parte das linhas uma **fórmula de incremento sequencial** — só
a primeira linha de cada sequência é valor literal. A extração
inicial só lia `raw_value` (NULL para a maioria dessas células) e
capturou apenas ~8% dos registros esperados. Corrigido usando
`COALESCE(raw_value, cached_value)` na extração para staging — a
fórmula em si continua preservada, intacta, em `raw.cells`. Corrigido
também: ambiguidade `""` vs. `NULL` na geração de SQL a partir de
CSV do `psql` (afetava colunas numéricas/texto vindas de
`fetch_sheet_rows`); coluna de linhagem ausente em
`staging.calibration_candidates` (adicionada, DDL reaplicado do
zero); corrupção de acentuação ao passar SQL via argumento de linha
de comando no Windows — corrigido escrevendo a consulta em arquivo
UTF-8 e usando `psql -f` em vez de `-c`.

**Ferramentas criadas:** `scripts/ingest_xlsx_postgres.py`
(subcomandos `ingest-raw`/`stage`; reaproveita `audit_xlsx.py`; sem
nome privado hardcoded; conexão só via variável de ambiente padrão do
libpq); `scripts/test_ingest_xlsx_postgres.py` (teste público de
integração contra PostgreSQL real, usando exclusivamente um workbook
`.xlsx` fabricado em memória — cobre ingestão, idempotência,
mapeamento `HIGH`/`MEDIUM`/`LOW`, lineage, e reversão de transação
com marcação `FAILED`). `scripts/db_v2_apply.ps1` atualizado para
incluir `008_ingestion.sql` na ordem de aplicação padrão.

**Artefatos privados criados** (todos em `data/restricted/`, nunca
versionados): `staging/source-to-canonical-mapping.json`,
`staging/_gen_mapping.py`, `audit/staging-profile.csv`,
`audit/ingestion-validation.md`. `.env.pricing_v2_private_dev` (local,
credencial gerada nesta sessão).

**Documentação pública criada/atualizada:**
[[14-PRIVATE-DATA-INGESTION]] (novo); [[04-DECISIONS]] (D10, nova);
[[03-ROADMAP]], [[07-DATA-DICTIONARY]] (referências sanitizadas).

**Verificação de segurança:** nenhuma senha versionada; nenhum
`.env` rastreado; `data/restricted/` confirmado não rastreado
(`git status`/`git ls-files`); busca textual nos artefatos novos
contra nomes/hashes privados conhecidos das fases 1B/1C — nenhuma
ocorrência.

**Testes:** `scripts/test_ingest_xlsx_postgres.py` (19 verificações,
contra PostgreSQL real) — **PASSOU**; `validate_db_v2.py` (8 arquivos
de DDL + seed sintético) — **PASSOU**; `test_validate_db_v2.py`,
`test_reference_allocation_engine.py` (21/21) — **PASSOU**;
`verify_postgres_v2.py` contra `patrimar_pricing_v2_test` — **PASSOU**
(banco de teste sintético da Fase 2C confirmado intacto, hash lógico
idêntico); `npm run test:model` — **PASSOU**. `database/schema.sql`,
`index.html`, `netlify/functions/hedonic-data.mts` e as migrations
Netlify existentes confirmados sem alteração.

**Estado final:** dois bancos PostgreSQL locais ativos —
`patrimar_pricing_v2_test` (sintético, Fase 2C, intacto) e
`patrimar_pricing_v2_private_dev` (privado, Fase 3A, com as duas
planilhas reais em `raw`/`staging`, zero linhas em
`core`/`pricing`/`market`).

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 2C: Execução real do schema v2 em PostgreSQL isolado (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** executar de fato (não só validar por parser) o schema v2
e o seed sintético contra um PostgreSQL real e isolado. Nenhum dado
privado, banco de produção, Netlify DB, frontend ou modelo OLS
tocado. Ver [[04-DECISIONS]] D9 e
[[13-POSTGRESQL-V2-RUNTIME-VALIDATION]].

**Ambiente:** PostgreSQL 18.4 já instalado no ambiente local (via
winget, pré-existente — nenhuma instalação nova necessária). Banco de
teste isolado `patrimar_pricing_v2_test`, role dedicada com senha
gerada aleatoriamente, credenciais só em `.env.pricing_v2_test`
(local, ignorado pelo Git). Nenhuma configuração global do servidor
alterada — `pg_hba.conf` pré-existente já restringe autenticação a
loopback.

**Resultado agregado:**

| Item | Resultado |
|---|---|
| DDL aplicado (7 arquivos, fail-fast) | Sem erro, 1ª tentativa |
| Inventário real (catálogo, não parser) | 4 schemas, 21 tabelas (4/12/2/3), 1 view, 34 FKs, 13 `UNIQUE`, 36 `CHECK`, 59 índices — tudo conferindo com a Fase 2 |
| Seed aplicado (transação única) | 391 `INSERT`s, sem erro |
| Contagens reais pós-seed | 1 development, 2 towers, 4 typologies, 40 units, 1 scenario, 2 runs, 80 unit_price_results, 240 unit_adjustments, 1 unit_override — todas conferindo |
| VGV (SQL puro) | alvo R$ 10.000.000,00 = sistemático R$ 10.000.000,00 (diferença 0,00) nos dois runs |
| Override (SQL puro) | sistemático R$ 10.000.000,00 + impacto R$ 50.000,00 = final R$ 10.050.000,00 |
| View `pricing.v_unit_price_current` | 40 linhas; após correção, reflete o override em exatamente 1 unidade |
| Rastreabilidade | reconstruída via SQL para 1 unidade sintética (torre→unidade→run→cenário→parâmetros→calibrações→ajustes→resultado→override→validação) |
| Testes de constraint reais | 7/7 inserções inválidas corretamente rejeitadas (FK, 2×`CHECK`, 2×`UNIQUE`, FK composta, índice único parcial) |
| Histórico | confirmado preservado entre as 2 runs (preço sistemático idêntico nas duas; override nunca sobrescreve) |
| Determinismo ponta a ponta | hash recalculado do banco = hash esperado, após 2 recriações completas do ambiente |

**Dois defeitos reais encontrados e corrigidos** (só detectáveis
executando contra PostgreSQL de fato):
1. Empate de `completed_at` entre as 2 runs do seed (`now()` na mesma
   transação) deixava a escolha de "run mais recente" da view não
   determinística — corrigido com timestamps literais/escalonados no
   seed + desempate defensivo adicional na view
   (`database/v2/007_views.sql`).
2. Hash lógico calculado com precisão Decimal quase ilimitada não
   reproduzia a partir do banco, porque `participation_share
   NUMERIC(9,6)` arredonda para 6 casas — o dinheiro nunca foi
   afetado, só o hash de verificação. Corrigido alinhando a
   quantização do hash à precisão real da coluna
   (`scripts/reference_allocation_engine.py`).

**Ferramentas criadas:** `scripts/verify_postgres_v2.py` (conecta via
`psql`, sem `psycopg2`; credenciais só por variável de ambiente,
nunca no código); `scripts/db_v2_create_test.ps1`,
`db_v2_apply.ps1`, `db_v2_verify.ps1`, `db_v2_drop_test.ps1`
(wrappers PowerShell; os três que alteram dados recusam operar se o
nome do banco não contiver `_test` — testado explicitamente).

**Documentação pública criada/atualizada:**
[[13-POSTGRESQL-V2-RUNTIME-VALIDATION]] (novo); [[04-DECISIONS]] (D9,
nova); [[03-ROADMAP]] (referências sanitizadas).

**Verificação de segurança:** nenhuma senha versionada; nenhum
`.env` rastreado; nenhum dado de `data/restricted/` usado; servidor
PostgreSQL pré-existente não teve configuração global alterada.

**Testes:** `npm run test:model` — **PASSOU**;
`test_reference_allocation_engine.py` (21/21),
`test_validate_db_v2.py`, `validate_db_v2.py --seed-file`,
`verify_postgres_v2.py` — **todos passaram**. `database/schema.sql`,
`index.html`, `netlify/functions/hedonic-data.mts` e as migrations
Netlify existentes confirmados sem alteração.

**Estado final:** o banco `patrimar_pricing_v2_test` **permanece
ativo** localmente para a próxima fase — não foi removido.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 2B: Seed sintético e prova end-to-end do Unit Price Allocation Engine (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** provar que o schema v2 (Fase 2) representa um ciclo
completo de distribuição de VGV, usando **exclusivamente** dados e
parâmetros sintéticos/públicos (`REFERENCE_ALLOCATION_V1`, ver
[[04-DECISIONS]] D8 e [[12-REFERENCE-ALLOCATION-ENGINE]]). Nenhum dado
privado foi utilizado; nenhum PostgreSQL real disponível no ambiente;
`database/schema.sql` (legado), Netlify, frontend e modelo OLS não
foram tocados.

**Fonte única de verdade:**
`fixtures/v2/reference_allocation_scenario.json` — todos os demais
artefatos (SQL seed, resultados esperados, relatório) são gerados a
partir dela por `scripts/generate_v2_seed.py`, nunca editados a mão.

**Resultado agregado:**

| Métrica | Valor |
|---|---|
| Empreendimento / torres / tipologias / unidades (fictícios) | 1 / 2 / 4 / 40 |
| Runs | 2 (`RUN-SYSTEM-ONLY`, `RUN-WITH-OVERRIDE`) |
| VGV-alvo (sintético) | R$ 10.000.000,00 |
| VGV sistemático (soma dos preços calculados) | R$ 10.000.000,00 — fecha exatamente |
| Validação `VGV_RECONCILIATION` | `INFO`, diferença `0.00`, em ambos os runs |
| Override de demonstração | preço anterior R$ 125.066,70 → final R$ 175.066,70 (impacto +R$ 50.000,00) |
| VGV final após override | R$ 10.050.000,00 (delta +R$ 50.000,00, exposto explicitamente) |
| Hash lógico determinístico (RUN 1) | `9a955e218e71e806ab4906fbf06b0111d635649658732d4f4a6048261d3dcf8c`, idêntico em reexecuções |
| INSERTs gerados no seed SQL | 391 (40 unidades × 2 runs × 3 tipos de ajuste = 240 `unit_adjustments`; 80 `unit_price_results`; demais tabelas de apoio) |
| Grupos de verificação em `test_reference_allocation_engine.py` | 21 (numéricos, determinismo, sensibilidade, override, falha explícita sobre dado inválido) |

**Ferramentas criadas:**
- `scripts/reference_allocation_engine.py` — motor puro (biblioteca
  padrão, `decimal.Decimal`, sem `float` em decisão monetária),
  separado de qualquer persistência.
- `scripts/generate_v2_seed.py` — gera, a partir da fixture canônica,
  o seed SQL + resultados esperados + relatório, com IDs UUID
  determinísticos (`uuid5`).
- `scripts/test_reference_allocation_engine.py` — 21 grupos de
  verificação, incluindo as 14 exigidas pela fase mais invariantes de
  domínio e testes de sensibilidade.
- `scripts/validate_db_v2.py` **estendido** com `--seed-file`: valida
  o seed contra o DDL (tabelas/colunas existem, nenhum `INSERT`
  explícito em coluna `GENERATED`, colunas `NOT NULL` sem `DEFAULT`
  presentes, toda FK resolvível na ordem em que as linhas aparecem).
  Teste de fumaça ampliado para confirmar que a extensão detecta de
  fato coluna obrigatória ausente e FK não resolvida, além do caminho
  feliz.

**Regra técnica documentada (não é regra Patrimar):** o resíduo de
arredondamento do fechamento do VGV é aplicado deterministicamente à
unidade de maior participação (empate: menor `unit_code`). Efeito
colateral documentado e coberto por teste: essa unidade específica não
escala proporcionalmente ao comparar VGVs diferentes; todas as demais
escalam dentro de 1 centavo.

**Artefatos públicos criados** (100% sintéticos, versionados):
`fixtures/v2/reference_allocation_scenario.json`,
`reference_allocation_expected.json`, `reference_allocation_report.md`;
`database/v2/seeds/001_demo_allocation.sql`.

**Documentação pública criada/atualizada:**
[[12-REFERENCE-ALLOCATION-ENGINE]] (novo); [[04-DECISIONS]] (D8, nova);
[[03-ROADMAP]], [[07-DATA-DICTIONARY]] (referências sanitizadas).

**Verificação de proteção de dados:** busca textual em todos os
artefatos desta fase contra nomes/hashes/magnitudes privados
conhecidos das Fases 1B/1C — nenhuma ocorrência.

**Testes:** `npm run test:model` — **PASSOU**; `python -m py_compile`
nos 3 scripts novos + `validate_db_v2.py` — **OK**;
`test_reference_allocation_engine.py` (21/21),
`test_validate_db_v2.py` (incluindo os novos casos de seed) — **todos
passaram**. `database/schema.sql` confirmado sem alteração.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 2: Desenho do schema canônico PostgreSQL v2 (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** tradução do modelo conceitual da Fase 1D em DDL PostgreSQL
físico, em `database/v2/`, sem tocar `database/schema.sql` (legado),
sem migrar dado nenhum, sem alterar Netlify/frontend/modelo OLS/banco
de produção.

**Reconciliação solicitada (Passo 1):** o relatório final da Fase 1D
dizia `ENTIDADES_CANDIDATAS=15`, mas a lista continha 16 nomes (um
item, "`ParameterSet` / `PricingParameter`", nomeava duas entidades).
**Número correto: 16.** Registrado em [[11-DATABASE-V2-DESIGN]] e em
`database/v2/README.md` para não haver mais divergência entre
documentação/modelo privado/schema físico.

**Perguntas bloqueadoras de schema (Q-05, Q-12):** resolvidas
modelando para a incerteza em vez de assumir uma hipótese — Q-05
(significado de um atributo de posição) virou um campo de texto
genérico e extensível; Q-12 (frequência de recalibração) deixou de
bloquear porque o schema já versiona toda calibração por padrão,
independente da frequência real. Nenhuma das duas exigiu resposta de
Rodolfo para prosseguir com um desenho seguro.

**Resultado agregado (números apenas, sem conteúdo):**

| Métrica | Valor |
|---|---|
| Schemas PostgreSQL criados | 4 (`core`, `pricing`, `audit`, `market`) |
| Tabelas físicas — core / pricing / audit / market | 4 / 12 / 2 / 3 (total 21) |
| Views | 1 (`pricing.v_unit_price_current`, semântica documentada explicitamente) |
| Foreign keys (inline + `ALTER TABLE` para as 4 dependências cruzadas entre schemas) | 34 |
| Constraints `UNIQUE` | 11 |
| `CHECK` constraints | 36 |
| Índices em `006_indexes.sql` (além dos implícitos de PK/UNIQUE) | 25, incluindo 1 índice único parcial (1 cenário ACTIVE por empreendimento) |
| Histórico preservado por padrão | parâmetros, calibrações, VGV, resultados por run, overrides — todos versionados/append-only |
| Overrides | append-only, nunca `UPDATE` do valor histórico; FK composta garante coerência com o resultado calculado |
| Trigger simples criada | 1 (consistência torre/empreendimento em `core.units`) |
| Decisões adiadas | `market.observations/comparables/transactions/listings`, `audit.decisions`, `raw`/`staging` físicos — todas documentadas, nenhuma tabela vazia criada por antecipação |

**Bug encontrado e corrigido durante a revisão manual do DDL** (sem
PostgreSQL local disponível para testar de fato): a view inicial usava
`DISTINCT ON` numa CTE separada de seu `ORDER BY`, o que não garante a
ordem em PostgreSQL — corrigido unificando `DISTINCT ON` e `ORDER BY`
na mesma consulta antes de considerar o DDL válido.

**Ferramenta criada:** `scripts/validate_db_v2.py` (Python, biblioteca
padrão apenas) — validação estrutural genérica de um conjunto de
arquivos `.sql`: arquivos existem, nenhum `DROP` destrutivo,
`snake_case`, toda referência aponta para algo já criado no ponto da
execução. Teste de fumaça sintético
(`scripts/test_validate_db_v2.py`) confirma que a ferramenta detecta
de fato: referência para frente, nome fora do padrão, `DROP`
destrutivo, e termo proibido — não só que aprova arquivos válidos.
Executada com sucesso contra os 7 arquivos reais de `database/v2/`.

**Artefatos privados criados:**
`data/restricted/audit/database-v2-mapping.md` (mapeamento dos
conceitos reais das planilhas para as tabelas físicas v2 — nenhum
valor deste arquivo aparece no SQL ou na documentação pública).

**Documentação pública criada:** [[11-DATABASE-V2-DESIGN]] (decisões
de modelagem, estratégia Legacy→V2 REUSE/TRANSFORM/DEPRECATE/
KEEP_FOR_DEMO, sem conteúdo privado).

**Testes:** `npm run test:model` — **PASSOU**, mesmo resultado das
fases anteriores; `python -m py_compile` nos 3 scripts — **OK**;
`scripts/test_audit_xlsx.py`, `test_analyze_pricing_logic.py`,
`test_validate_db_v2.py` — **todos passaram**. `database/schema.sql`
confirmado sem alteração (`git status`/`git diff` vazios).

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 1D: Gap analysis e modelo canônico preliminar (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** modelagem conceitual e análise de lacunas a partir do
conhecimento reconstruído nas Fases 1B/1C. Nenhum schema físico,
migration, alteração de banco, frontend, Netlify ou modelo OLS.
Nenhum conteúdo privado (nome de aba/campo real, fórmula, valor,
parâmetro) reproduzido neste documento — ver [[04-DECISIONS]] D4/D6/D7
e [[10-PRICING-DOMAIN-MODEL]].

**Decisão arquitetural registrada:** separação formal entre **Market
Pricing Engine** (Motor A — estimativa de valor de mercado) e **Unit
Price Allocation Engine** (Motor B — distribuição do VGV entre
unidades), com o VGV/preço-base recomendado como único ponto de
integração entre os dois — ver [[04-DECISIONS]] D7.

**Resultado agregado (números apenas, sem conteúdo):**

| Métrica | Valor |
|---|---|
| Conceitos/domínios avaliados na taxonomia | 25 (PROJECT/DEVELOPMENT a HUMAN_REVIEW) |
| Linhas na matriz de gap analysis | 27 |
| — classificadas MUST_HAVE / SHOULD_HAVE / NICE_TO_HAVE | 15 / 10 / 2 |
| — sem gap identificado (NO_GAP) | 8 |
| — com gap de fonte de dado (MISSING_SOURCE) | 6 |
| — com gap de definição, histórico ou governança | 4, 4, 2 respectivamente |
| — necessárias só para alocação interna / só para mercado / para ambos | 12 / 6 / 9 |
| Variáveis na matriz de precificação (Motor A × Motor B) | 18 |
| — com evidência observada na metodologia atual | 10 |
| — apoiadas pelo laboratório hedônico legado | 6 |
| — hipótese futura, sem evidência ainda | 2 |
| Itens no backlog de aquisição de dados | 10 (4 MUST_HAVE, 4 SHOULD_HAVE, 1 NICE_TO_HAVE, 1 RESEARCH) |
| — bloqueantes para decisões imediatas | 4 |
| Variáveis do modelo hedônico legado reavaliadas para o Motor A | 13 — nenhuma classificada como irrelevante; a maioria como reaproveitável com adaptação, 2 marcadas como dependentes de confirmação de dado real |
| Perguntas para quem forneceu a planilha, reclassificadas por bloqueio | 13 — 2 bloqueiam schema, 5 bloqueiam regra de negócio, 1 bloqueia decisão de modelo, 5 não bloqueiam nada crítico agora |
| Anomalia de fórmula da Fase 1C | preservada como evidência privada; não corrigida; registrada conceitualmente como necessidade futura de validação/versionamento/testes/rastreabilidade |

**Artefatos privados criados** (todos em `data/restricted/audit/`,
ignorados pelo Git): `pricing-gap-analysis.csv`,
`pricing-variable-matrix.csv`, `data-acquisition-backlog.csv`,
`preliminary-canonical-model.md` (com diagramas Mermaid),
`gap-analysis-summary.md`. `questions-for-rodolfo.md` (da Fase 1C) foi
atualizado com uma seção de classificação de bloqueio, sem novas
perguntas.

**Documentação pública criada/atualizada:**
[[10-PRICING-DOMAIN-MODEL]] (novo); [[04-DECISIONS]] (D7, nova);
[[00-PROJECT-CHARTER]], [[03-ROADMAP]], [[07-DATA-DICTIONARY]]
(referências sanitizadas à nova decisão arquitetural).

**Testes:** `npm run test:model` re-executado — **PASSOU**;
`python -m py_compile` em `scripts/audit_xlsx.py` e
`scripts/analyze_pricing_logic.py` — **OK**. Nenhum script novo foi
criado nesta fase (trabalho puramente de modelagem/análise).

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 1C: Engenharia reversa da lógica de precificação (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** reconstrução, com evidência de fórmula, do fluxo de
cálculo de preço presente nos dois workbooks já auditados
estruturalmente na Fase 1B. Nenhum banco definitivo foi desenhado,
nenhum dado foi migrado, e nenhuma alteração foi feita em frontend,
modelo hedônico, API ou Netlify. Nenhum conteúdo privado (nome de
aba/campo real, fórmula específica, valor, parâmetro) é reproduzido
neste documento — ver [[04-DECISIONS]] D4/D6 e
[[09-PRICING-LOGIC-REVERSE-ENGINEERING]].

**Cadeia de custódia:** SHA-256 dos dois originais revalidado antes e
depois desta fase contra `data/restricted/audit/
manifest-recebimento.csv` — idêntico. Nenhuma escrita sobre
`raw/rodolfo/`.

**Ferramenta criada:** `scripts/analyze_pricing_logic.py` (reaproveita
o parsing de `scripts/audit_xlsx.py`; nenhuma dependência externa
nova). Extrai constantes numéricas embutidas em fórmulas e sinaliza
regiões onde o padrão de fórmula de uma coluna diverge do padrão
majoritário. Validada com `--help`, `python -m py_compile`, e um
teste de fumaça sintético (`scripts/test_analyze_pricing_logic.py`,
sem dado real) — **PASSOU**.

**Resultado agregado (números apenas, sem conteúdo):**

| Métrica | Valor |
|---|---|
| Workbooks analisados | 2 |
| Fluxos de precificação reconstruídos | 2 (estruturalmente idênticos entre si) |
| Regras de negócio catalogadas | 21 |
| — regras de agregação | 4 |
| — regras de busca/ajuste (lookup + transformação) | 5 |
| — regra de override explícito | 1 (+ 6 regras no total classificadas como intervenção humana opcional) |
| — regras de saída (output) | 2 diretas + 2 de conferência agregada |
| — regras de filtro/seleção de comparáveis externos | 0 (nenhum mecanismo desse tipo encontrado; comparação é interna, entre unidades do próprio empreendimento) |
| Confiança das regras catalogadas | 15 ALTA, 5 MÉDIA, 1 BAIXA |
| Constantes numéricas brutas identificadas pela ferramenta (antes de curadoria) | 807 |
| — das quais sinalizadas como possivelmente exigindo explicação humana | 286 |
| Parâmetros de negócio curados no catálogo | 7 |
| Regiões de possível inconsistência de fórmula sinalizadas pela ferramenta | 101 (43 UNKNOWN, 40 possível override manual, 18 possível erro/variação) |
| Anomalia de fórmula confirmada manualmente contra o XML bruto (não artefato da ferramenta) | 1 (presente em apenas um dos dois workbooks) |
| Regras comuns entre os dois workbooks (alta confiança estrutural) | 19 |
| Regras/observações exclusivas de um dos workbooks | 2 |
| Ambiguidades críticas registradas | 5 |
| Perguntas geradas para quem forneceu a planilha | 13 (3 críticas, 6 importantes, 4 opcionais) |
| Classificação de automação | 8 automatizáveis agora, 3 automatizáveis com mais dados, 3 exigem regra de negócio configurável, 4 exigem julgamento humano permanente, 3 indefinidas |

**Achado metodológico relevante para a ferramenta:** confirmada uma
limitação de leitura de fórmulas compartilhadas do formato XLSX (texto
da fórmula-mestre reaproveitado sem recalcular deslocamento relativo
para células não-mestre do mesmo grupo). Documentada em
[[09-PRICING-LOGIC-REVERSE-ENGINEERING]]; nenhuma regra do catálogo
final foi baseada em fórmula não confirmada contra o XML bruto.

**Artefatos privados criados** (todos em `data/restricted/audit/`,
ignorados pelo Git): `pricing_parameters_detected.csv`,
`formula_consistency_flags.csv`, `business_rules_catalog.csv`,
`automation-map.csv`, `questions-for-rodolfo.md`,
`pricing-logic-reconstruction.md`.

**Documentação pública criada:**
[[09-PRICING-LOGIC-REVERSE-ENGINEERING]] (metodologia genérica, sem
nenhum conteúdo das planilhas).

**Testes:** `npm run test:model` re-executado — **PASSOU**, mesmo
resultado numérico das fases anteriores.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 1B: Auditoria estrutural das planilhas do Rodolfo (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** auditoria estrutural (metadados, abas, fórmulas,
dependências, conteúdo oculto, qualidade, comparação entre workbooks)
dos dois arquivos já recebidos em `data/restricted/raw/rodolfo/`
(Fase 1A.1). Nenhuma interpretação de regra de negócio, conversão de
formato, importação para PostgreSQL, ou alteração de frontend/modelo/
API/Netlify foi feita. Nenhum conteúdo privado (nome de arquivo, de
empreendimento, de aba ou de campo) é reproduzido neste documento —
ver [[04-DECISIONS]] D4/D6 e [[08-SPREADSHEET-AUDIT-METHOD]].

**Cadeia de custódia:** SHA-256 dos dois originais recalculado antes e
depois da auditoria e comparado com `data/restricted/audit/
manifest-recebimento.csv` — **idêntico nas duas verificações**.
Nenhuma escrita foi feita sobre os arquivos em `raw/rodolfo/`; a
ferramenta os abre somente em modo leitura.

**Ferramenta criada:** `scripts/audit_xlsx.py` (Python, biblioteca
padrão apenas — `zipfile` + `xml.etree.ElementTree` — sem adicionar
dependência externa, já que nenhuma biblioteca de leitura de XLSX
estava disponível no ambiente e o escopo não justificou instalar uma).
Recebe caminhos de entrada/saída por argumento; não contém nomes de
arquivo, caminhos absolutos, hashes ou valores privados. Validada com
`python scripts/audit_xlsx.py --help`, `python -m py_compile`, e um
teste de fumaça com workbooks **sintéticos** gerados em memória
(`scripts/test_audit_xlsx.py`, sem nenhum dado real) — **PASSOU**.

**Resultado agregado da auditoria (números apenas, sem conteúdo):**

| Métrica | Valor |
|---|---|
| Workbooks auditados | 2 |
| Abas totais | 8 (4 por workbook) |
| Abas visíveis / ocultas / muito ocultas | 8 / 0 / 0 |
| Campos (colunas) detectados | 77 |
| Células preenchidas (soma dos 2 workbooks) | 25.023 |
| Células com fórmula (soma) | 18.377 |
| Padrões únicos de fórmula (após normalização) | 430 |
| Arestas de dependência aba→aba | 10 |
| Vínculos externos / macros / pivot tables detectados | 0 / 0 / 0 |
| Conteúdo oculto (nomes definidos ocultos + colunas ocultas) | 3 |
| Campos candidatos a chave única | 0 |
| Campos com POTENCIAL_PII=SIM | 0 |
| Problemas de qualidade registrados | 705 (majoritariamente linhas vazias no meio de intervalos de dados, típico de planilhas com formatação além da área de dados real) |
| Correspondências entre os 2 workbooks (abas+campos) | 10 (9 confiança ALTA, 1 BAIXA) |

**Artefatos privados gerados** (todos em `data/restricted/audit/`,
ignorados pelo Git): `workbook_inventory.csv`, `sheet_inventory.csv`,
`field_profile.csv`, `formula_inventory.csv`,
`dependency_inventory.csv`, `hidden_content_inventory.csv`,
`quality_issues.csv`, `cross_workbook_mapping.csv`,
`structural-audit.md`.

**Documentação pública criada:** [[08-SPREADSHEET-AUDIT-METHOD]]
(metodologia genérica, sem nenhum conteúdo das planilhas).

**Testes:** `npm run test:model` re-executado — **PASSOU**, mesmo
resultado numérico das fases anteriores (modelo/gerador não tocados).

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 1A.1: Fechamento da recepção das planilhas (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** registro de metadados técnicos (inventário) dos arquivos
que Gustavo já havia copiado manualmente para a zona restrita local.
Nenhum conteúdo interno das planilhas foi aberto, lido ou registrado.
Nenhum arquivo original foi modificado, renomeado, movido ou
convertido. Nenhuma alteração em código, modelo, frontend, API,
Netlify ou banco.

**Estado confirmado antes de agir:** branch `rebuild/pricing-intelligence`,
working tree limpo; dois arquivos já presentes em
`data/restricted/raw/rodolfo/` (recepção manual feita por Gustavo fora
desta sessão).

**Ações executadas:**

| Ação | Resultado |
|---|---|
| Listagem de `data/restricted/raw/rodolfo/` | 2 arquivos `.xlsx` encontrados (nomes não reproduzidos aqui — ver [[04-DECISIONS]] D4/D6) |
| Cálculo de SHA-256, tamanho e data de modificação de cada arquivo | registrado privadamente em `data/restricted/audit/manifest-recebimento.csv` (ignorado pelo Git) — colunas: `filename, extension, size_bytes, modified_time, sha256` |
| Re-hash dos arquivos após o registro | hashes idênticos aos originais — nenhuma alteração ocorreu |
| `git check-ignore -v` nos dois originais e no manifesto | todos confirmados ignorados pela regra `data/restricted/` do `.gitignore` |
| `git status` / `git ls-files` | nenhum arquivo de `data/restricted/` aparece rastreado ou pendente de commit |

**Dados privados registrados em documentação pública:** nenhum. Nomes
de arquivo, nomes de empreendimento e qualquer conteúdo das planilhas
permanecem exclusivamente em `data/restricted/` (local, fora do Git).

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 1A: Recepção e preservação das planilhas do Rodolfo (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** preparação local da zona restrita para recepção de fontes
privadas da Patrimar. Nenhuma alteração em código, modelo, frontend,
API, Netlify ou banco. Nenhum conteúdo privado foi escrito neste
documento (ver `docs/04-DECISIONS.md` D4/D6).

**Estado confirmado antes de agir:** branch `rebuild/pricing-intelligence`,
working tree limpo.

**Ações executadas:**

| Ação | Resultado |
|---|---|
| Criação da árvore `data/restricted/{raw/rodolfo,audit,staging,derived,quarantine}/` | subpastas criadas para preservação, auditoria (hashes/manifesto), normalização, dados derivados e triagem de arquivos suspeitos |
| Validação com `git check-ignore -v` em arquivos de teste temporários dentro de `raw/rodolfo/` e `audit/` | ambos confirmados como ignorados pela regra `data/restricted/` do `.gitignore`; arquivos de teste removidos manualmente após a validação |
| Criação de `data/restricted/README-LOCAL.md` (privado, ignorado pelo Git) | documenta o propósito de cada subpasta e a regra de nunca editar arquivos em `raw/rodolfo/` |
| Verificação do conteúdo de `data/restricted/raw/rodolfo/` | pasta vazia nesta sessão — nenhuma busca automática foi feita no restante do computador |
| Abertura da pasta no Windows Explorer | zona restrita local preparada para recepção de fontes privadas da Patrimar; recepção manual das planilhas fica a cargo do responsável do projeto |

**Dados privados registrados neste documento:** nenhum. Nenhum nome de
arquivo, nome de empreendimento ou conteúdo de planilha foi escrito
aqui ou em qualquer outro documento público.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 0.6: Backup remoto da fundação (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** push explicitamente autorizado, limitado a dois refs.
**Autorização:** push explícito do responsável pelo projeto, restrito a
`rebuild/pricing-intelligence` e à tag
`legacy-hedonica-pre-rebuild-20260909`. Sem merge em `main`, sem
alteração em `main`, sem alteração de Netlify.

**Estado confirmado antes do push:** branch `rebuild/pricing-intelligence`,
HEAD `5ab265b` ("chore: establish Patrimar Pricing Intelligence
baseline"), working tree limpo, tag local apontando para `7dd1d24`.

**Ações executadas:**

| Ação | Resultado |
|---|---|
| `git push -u origin rebuild/pricing-intelligence` | branch remota criada; local passa a rastrear `origin/rebuild/pricing-intelligence` |
| `git push origin legacy-hedonica-pre-rebuild-20260909` | tag remota criada, apontando para `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0` |
| `git ls-remote --heads origin rebuild/pricing-intelligence` | confirma a branch remota no commit `5ab265b` |
| `git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909` | confirma a tag remota em `7dd1d24` |
| `git branch -vv` | `main` permanece em `7dd1d24` (`[origin/main]`), sem alteração |
| `git status` | working tree limpo antes e depois do push |

**Dados privados enviados:** nenhum — o conteúdo enviado é exatamente o
commit `5ab265b` já auditado na Fase 0.5 (`docs/`, `CLAUDE.md`,
`AGENTS.md`, `.gitignore`), mais a tag do legado (que aponta para o
commit legado já público em `main`). Nenhum arquivo de `data/restricted/`
existe no repositório, portanto nada disso pôde ser enviado.

**`main` alterada:** não. **Netlify alterado:** não. **Merge em `main`:**
não realizado.

**Próximo passo recomendado:** Fase 1A — recepção das planilhas do
Rodolfo, salvando qualquer arquivo real recebido em `data/restricted/`
antes de qualquer outra ação. Ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 0.5: Congelamento do legado e fundação segura (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** ponto de recuperação do legado, branch da nova plataforma,
`.gitignore`, governança de dados restritos, versionamento da
documentação da Fase 0. Sem push, sem alteração de modelo, banco,
frontend, função Netlify ou dados.

**Estado git confirmado no início:** branch `main`, HEAD `7dd1d24`
("fix: nomear série do gráfico de ajuste"), working tree com apenas
`AGENTS.md`, `CLAUDE.md`, `docs/` não rastreados (produzidos na Fase 0).

**Ações executadas:**

| Ação | Resultado |
|---|---|
| `git tag legacy-hedonica-pre-rebuild-20260909 7dd1d24` | tag local criada, confirmada apontando para `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0` |
| `git checkout -b rebuild/pricing-intelligence 7dd1d24` | nova branch criada a partir do legado; arquivos não rastreados da Fase 0 preservados |
| criação de `.gitignore` na raiz | inclui `node_modules/`, `.env`/`.env.*` (exceto `.env.example`), `.netlify/`, `.claude/settings.local.json`, `data/restricted/` — `data/` em si permanece versionada |
| atualização de [[04-DECISIONS]] (nova entrada D6) e [[03-ROADMAP]] | formalizam a zona restrita `data/restricted/` e a Fase 0.5 |
| `npm run test:model` | **PASSOU.** Saída: `{"rows":626,"R2":0.9017695081744214,"RMSE_test":4186.3075308912585,"MAPE_test":13.684152781394218,"max_VIF":11.83580058286043}` — idêntico à execução da Fase 0, confirmando que nada no modelo/gerador foi alterado |
| verificação de rastreamento de `.env`, `.claude/settings.local.json`, `data/restricted/` e busca por segredos óbvios | nenhum arquivo sensível rastreado; nenhum segredo encontrado |
| commit local único (`docs/`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`) | mensagem `chore: establish Patrimar Pricing Intelligence baseline` — ver hash em [[99-HANDOFF]] |

**Não realizado (fora do escopo desta fase):** push, qualquer alteração
em `index.html`, modelo OLS, `netlify/`, banco de dados, ou importação
de planilhas.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 0: Auditoria, inventário e documentação (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** somente leitura + 1 execução de teste local + criação de
documentação. Sem commit, sem push, sem branch, sem alteração de banco,
deploy ou comportamento de código existente.

**Estado git confirmado no início:**
- branch: `main`, up to date with `origin/main`
- working tree: clean
- último commit: `7dd1d24` "fix: nomear série do gráfico de ajuste"

**Comandos executados:**

| Comando | Resultado |
|---|---|
| `git status`, `git branch -vv`, `git log --oneline -20`, `git remote -v` | confirmaram estado acima |
| `find . -maxdepth 3` (excluindo `.git`, `node_modules`) | inventário de 12 arquivos versionados em 5 diretórios |
| `node -v` / `npm -v` | `v24.18.1` / `11.16.0` |
| `npm run test:model` | **PASSOU.** Saída: `{"rows":626,"R2":0.9017695081744214,"RMSE_test":4186.3075308912585,"MAPE_test":13.684152781394218,"max_VIF":11.83580058286043}` |
| `git status --short` (após o teste) | vazio — teste não alterou nenhum arquivo versionado |
| grep por `DATABASE_URL\|API_KEY\|SECRET\|PASSWORD\|postgres://` (case-insensitive) em todo o repo | ocorrências apenas em `tests/model-smoke.mjs` (checagem negativa) e `MODEL.md` (texto descritivo) — nenhum valor de segredo encontrado |
| `git check-ignore -v .claude/settings.local.json` | ignorado por regra **global** do usuário (`~/.config/git/ignore`), não por um `.gitignore` do projeto (que não existe) |
| `diff database/schema.sql netlify/database/migrations/20260829090000_create_hedonic_schema.sql` | arquivos semanticamente idênticos, com diferenças triviais de formatação (`BEGIN/COMMIT` e espaçamento de `JOIN`) |

**Scripts inspecionados mas NÃO executados** (para não gerar/sobrescrever
arquivos sem necessidade): `scripts/generate-hybrid-seed.mjs`,
`scripts/generate-seed-migration.mjs`.

**Documentos criados:** ver [[99-HANDOFF]] → seção "Arquivos criados
nesta sessão".

**Testes:** 1 de 1 disponível, executado, aprovado, sem warnings visíveis
na saída padrão/erro.

**Riscos identificados:** ver relatório final desta sessão e
[[06-LESSONS-LEARNED]] (estrutura criada, sem conteúdo ainda — riscos
já conhecidos estão descritos em [[01-CURRENT-STATE]] e no relatório
final, não duplicados aqui).

**Próximo passo recomendado ao final desta sessão:** ver [[99-HANDOFF]].
