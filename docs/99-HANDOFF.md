# 99 — Handoff

Este documento deve permitir que qualquer agente (ou pessoa) assuma o
projeto **sem ter acesso à conversa em que este trabalho foi feito**.
Leia isto, depois leia os documentos referenciados, na ordem sugerida.

## Ordem de leitura recomendada

1. [[00-PROJECT-CHARTER]] — por que este projeto existe.
2. [[01-CURRENT-STATE]] — o que de fato existe hoje, comprovado.
3. [[02-ARCHITECTURE]] — como as peças se conectam hoje.
4. [[03-ROADMAP]] — o que vem depois (ainda não implementado).
5. [[04-DECISIONS]] — regras que não devem ser quebradas sem registro
   (D7 dois motores; D8 referência sintética não é metodologia
   oficial; D9 testes de banco real isolados sem alterar servidor;
   D10 banco privado de ingestão separado do banco sintético).
6. [[08-SPREADSHEET-AUDIT-METHOD]], [[09-PRICING-LOGIC-REVERSE-ENGINEERING]],
   [[10-PRICING-DOMAIN-MODEL]], [[11-DATABASE-V2-DESIGN]],
   [[12-REFERENCE-ALLOCATION-ENGINE]] — metodologia/modelo das fases
   anteriores, sem conteúdo privado.
7. [[13-POSTGRESQL-V2-RUNTIME-VALIDATION]] — execução real contra
   PostgreSQL, os dois defeitos encontrados e corrigidos (Fase 2C).
8. [[14-PRIVATE-DATA-INGESTION]] — ingestão controlada RAW/STAGING das
   planilhas reais (Fase 3A).
9. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 3A)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **As duas planilhas reais de Rodolfo agora existem, pela primeira
  vez, dentro de um banco de dados.** Banco novo e **privado**,
  `patrimar_pricing_v2_private_dev` (mesmo servidor PostgreSQL 18.4
  local pré-existente), **totalmente separado** do banco sintético de
  teste `patrimar_pricing_v2_test` (Fase 2C, que permanece intacto —
  ver [[04-DECISIONS]] D10). Credenciais em
  `.env.pricing_v2_private_dev` (local, `.gitignore`, senha gerada
  nesta sessão, nunca impressa em nenhum relatório).
- **Destino exclusivo: schemas `raw`/`staging`
  (`database/v2/008_ingestion.sql`).** Zero linhas em
  `core`/`pricing`/`market` nesse banco. Nenhum preço foi calculado
  ou reproduzido; `REFERENCE_ALLOCATION_V1` (D8) não foi usado sobre
  dado real.
- **Fidelidade total confirmada:** 25.023 células / 18.377 fórmulas
  ingeridas, reconciliação exata com o inventário estrutural da Fase
  1B; 263 células amostradas deterministicamente, 0 divergências.
- **Idempotência confirmada duas vezes contra PostgreSQL real:**
  reingerir o mesmo arquivo (mesmo SHA-256) produz `ALREADY_INGESTED`
  e não duplica nenhuma linha.
- **Mapeamento por confiança:** 27 entradas privadas (14 `HIGH`, 11
  `MEDIUM`, 2 `LOW`). Só `HIGH` foi convertido automaticamente para
  candidato de staging (884 unidade + 884 resultado de preço + 8
  parâmetro + 31 calibração); `MEDIUM`/`LOW` foram para
  `staging.mapping_review` (13 linhas), nunca convertidos
  automaticamente. Zero linhas de staging órfãs.
- **Um bug real de extração foi encontrado e corrigido**: uma coluna
  de identificador de unidade é majoritariamente **fórmula de
  incremento**, não valor manual — a extração inicial só lia
  `raw_value` (NULL nesses casos) e capturou ~8% dos registros
  esperados. Corrigido com `COALESCE(raw_value, cached_value)`. Ver
  [[14-PRIVATE-DATA-INGESTION]] e o worklog desta fase para o
  detalhe completo (incluindo os outros 3 bugs menores corrigidos:
  ambiguidade `""`/`NULL` em CSV do `psql`, coluna de linhagem
  ausente em `staging.calibration_candidates`, corrupção de
  acentuação via argumento de linha de comando no Windows).
- **Avaliação de chave candidata com evidência real**: confirma que
  um identificador de negócio isolado não é suficiente como chave num
  dos dois workbooks (precisa de chave composta com a subdivisão
  interna do empreendimento); no outro, é suficiente isoladamente —
  consistente com a decisão de schema já tomada na Fase 2
  (`UNIQUE(development_id, tower_id, unit_code)`).
- **Teste público sintético criado:**
  `scripts/test_ingest_xlsx_postgres.py` — prova o pipeline completo
  (ingest-raw, idempotência, stage com `HIGH`/`MEDIUM`/`LOW`,
  lineage, e reversão de transação com marcação `FAILED`) usando
  exclusivamente um workbook `.xlsx` fabricado em memória. Executado
  com sucesso contra PostgreSQL real neste ambiente.
- **Banco de teste sintético (`patrimar_pricing_v2_test`, Fase 2C)
  confirmado intacto** ao final desta fase — `verify_postgres_v2.py`
  reexecutado com sucesso, hash lógico idêntico ao esperado.
- `npm run test:model` re-executado: **PASSOU**, mesmo resultado das
  fases anteriores.

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence baseline`.
2. `e689be9` — `docs: record remote baseline backup`.
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase 1A).
4. `f21df3d` — `docs: record restricted data receipt` (Fase 1A.1).
5. `8472085` — `feat: add workbook structural audit tooling` (Fase 1B).
6. `99a225a` — `feat: add pricing logic reverse engineering` (Fase 1C).
7. `f5a2cb2` — `docs: define Patrimar pricing domain model` (Fase 1D).
8. `e59157e` — `feat: design canonical PostgreSQL v2 schema` (Fase 2).
9. `866e876` — `feat: prove unit allocation engine with synthetic scenario` (Fase 2B).
10. `c72fe0c` — `test: validate pricing v2 on real PostgreSQL` (Fase 2C).
11. (Fase 3A) commit — `feat: add controlled private data ingestion
    pipeline` (`database/v2/008_ingestion.sql`,
    `scripts/ingest_xlsx_postgres.py`,
    `scripts/test_ingest_xlsx_postgres.py`,
    `scripts/db_v2_apply.ps1` atualizado,
    `docs/14-PRIVATE-DATA-INGESTION.md`, `docs/03-ROADMAP.md`,
    `docs/04-DECISIONS.md`, `docs/05-WORKLOG.md`,
    `docs/07-DATA-DICTIONARY.md`, `docs/99-HANDOFF.md` — tudo
    público/genérico, nenhum dado privado, nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. Nenhum
`.env.*` nunca foi (e não pode ser) adicionado a nenhum commit.

## Arquivos criados/alterados nesta fase (Fase 3A)

```
docs/14-PRIVATE-DATA-INGESTION.md                      (novo)
docs/03-ROADMAP.md, 04-DECISIONS.md, 05-WORKLOG.md,
  07-DATA-DICTIONARY.md, 99-HANDOFF.md                 (atualizados)
database/v2/008_ingestion.sql                          (novo — schemas raw/staging)
database/v2/README.md                                  (atualizado — ordem de execução + contagem de tabelas)
scripts/ingest_xlsx_postgres.py                        (novo)
scripts/test_ingest_xlsx_postgres.py                   (novo — teste público sintético)
scripts/db_v2_apply.ps1                                (atualizado — inclui 008_ingestion.sql)
.env.pricing_v2_private_dev                            (LOCAL, NAO versionado — credenciais do banco privado)
data/restricted/staging/source-to-canonical-mapping.json (LOCAL, NAO versionado)
data/restricted/staging/_gen_mapping.py                (LOCAL, NAO versionado)
data/restricted/audit/staging-profile.csv              (LOCAL, NAO versionado)
data/restricted/audit/ingestion-validation.md          (LOCAL, NAO versionado)
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `tests/model-smoke.mjs`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado em nenhuma
fase até agora — confirmado via `git log` em cada um deles nesta fase.

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Ainda não resolvido.
2. **Não verificado em nenhuma auditoria até agora:** se o Netlify DB
   de produção está provisionado/populado, se o deploy Netlify está
   ativo, e se `GET /api/hedonic-data` responde em produção.
3. **Dados reais da Patrimar não devem ser commitados** — ver
   [[04-DECISIONS]] D4/D6. Qualquer dado real deve ir para
   `data/restricted/` ou para o banco privado `_private_dev`, nunca
   para caminho versionado.
4. **`REFERENCE_ALLOCATION_V1` nunca deve ser confundido com a
   metodologia real** — ver [[04-DECISIONS]] D8. Nesta fase ele
   continua não usado sobre dado real (correto, por design).
5. **Dois bancos PostgreSQL locais agora existem no mesmo servidor
   pré-existente** (`patrimar_pricing_v2_test` e
   `patrimar_pricing_v2_private_dev`) — provavelmente ao lado de
   outros projetos do usuário. Não assumir que é um servidor
   dedicado só a este projeto — nunca rodar comandos administrativos
   amplos nele. Nunca misturar dado real no banco `_test`, nem dado
   sintético de demonstração no banco `_private_dev` (ver D10) — os
   dois devem continuar servindo propósitos diferentes.
6. **`main` e `rebuild/pricing-intelligence` divergirão** até decisão
   explícita de merge/substituição.
7. **`data/restricted/` continua existindo apenas localmente** — esta
   fase adicionou arquivos novos lá (mapeamento, perfil de staging,
   relatório de validação), nenhum deles versionado.
8. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte de
   dado real** — fora de escopo desta fase também.
9. **Perguntas ainda pendentes para quem forneceu a planilha** — ver
   `data/restricted/audit/questions-for-rodolfo.md`. Esta fase reforçou
   pelo menos duas delas com evidência adicional (estrutura de torres
   de um dos workbooks; significado de um rótulo de tipologia que
   parece genérico) — ver `data/restricted/audit/ingestion-validation.md`.
10. **11 registros `MEDIUM`/`LOW` permanecem em `staging.mapping_review`
    sem conversão automática** — decisão correta por design (D-implícita
    desta fase: "não inventar significado"), mas qualquer trabalho
    futuro de promoção staging→core deve tratá-los explicitamente, não
    ignorá-los silenciosamente.
11. **A Fase 3B (mapeamento staging → core/pricing) ainda não foi
    iniciada.** Antes de iniciá-la, considerar levar as perguntas
    pendentes de Rodolfo ao responsável do projeto — várias decisões
    de promoção dependem das respostas.

## Comandos úteis já validados

```bash
npm run test:model
python scripts/test_reference_allocation_engine.py
python scripts/test_validate_db_v2.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql --file 008_ingestion.sql \
  --seed-file database/v2/seeds/001_demo_allocation.sql

# contra o banco de teste SINTÉTICO (requer .env.pricing_v2_test local e psql no PATH/PSQL_BIN):
powershell -File scripts/db_v2_create_test.ps1   # cria/recria banco+role de teste
powershell -File scripts/db_v2_apply.ps1 -WithSeed  # aplica DDL (001-008) + seed, fail-fast
powershell -File scripts/db_v2_verify.ps1        # compara banco real x expected.json (inclui hash)
powershell -File scripts/db_v2_drop_test.ps1     # remove o banco de teste (NÃO executar sem necessidade)

# teste público sintético do pipeline de ingestão (contra qualquer banco "_test"):
python scripts/test_ingest_xlsx_postgres.py --env-file .env.pricing_v2_test

# ingestão real (NUNCA rodar contra o banco "_test" — só contra o banco privado dedicado):
python scripts/ingest_xlsx_postgres.py ingest-raw --input <arquivo.xlsx> --dry-run
python scripts/ingest_xlsx_postgres.py stage --mapping <mapeamento.json privado>
```

## Próximo passo recomendado

**Fase 3B — Mapeamento staging → core/pricing.** Com `raw`/`staging`
povoados de verdade a partir das duas planilhas reais, o próximo
passo natural é decidir e implementar a promoção controlada dos
candidatos `CANDIDATE` (confiança `HIGH`, já em `staging.*`) para as
tabelas de domínio (`core.developments/towers/units`,
`pricing.parameters/calibration_entries/...`) — respeitando D4/D6/D7/
D8/D10, sem tocar nos registros `MEDIUM`/`LOW` ainda em revisão, e
sem calcular nenhum preço real ainda (isso continua sendo escopo de
uma fase posterior, dependente das respostas de Rodolfo). Antes de
iniciar, revisar `data/restricted/audit/ingestion-validation.md` e
`questions-for-rodolfo.md` — várias decisões de promoção dependem de
perguntas ainda sem resposta.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, fórmulas específicas, valores, senhas, connection
strings, ou qualquer conteúdo das planilhas privadas em nenhum
documento dentro de `docs/`, `fixtures/` ou qualquer arquivo `.sql`/
`.ps1`/`.py` — apenas descrições sanitizadas e números agregados.
