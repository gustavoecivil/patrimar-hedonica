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
   D10 banco privado de ingestão separado do banco sintético; D11
   resultado importado nunca confundido com resultado calculado).
6. [[08-SPREADSHEET-AUDIT-METHOD]], [[09-PRICING-LOGIC-REVERSE-ENGINEERING]],
   [[10-PRICING-DOMAIN-MODEL]], [[11-DATABASE-V2-DESIGN]],
   [[12-REFERENCE-ALLOCATION-ENGINE]] — metodologia/modelo das fases
   anteriores, sem conteúdo privado.
7. [[13-POSTGRESQL-V2-RUNTIME-VALIDATION]] — execução real contra
   PostgreSQL, os dois defeitos encontrados e corrigidos (Fase 2C).
8. [[14-PRIVATE-DATA-INGESTION]] — ingestão controlada RAW/STAGING das
   planilhas reais (Fase 3A).
9. [[15-STAGING-TO-CANONICAL-PROMOTION]] — promoção controlada de
   staging para core/pricing (Fase 3B).
10. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 3B)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **As duas planilhas reais de Rodolfo agora têm entidades canônicas
  reais em `core`/`pricing`**, no mesmo banco privado
  `patrimar_pricing_v2_private_dev` (Fase 3A) — 2 desenvolvimentos, 5
  torres, 2 tipologias, 884 unidades, 4 parâmetros, 29 entradas de
  calibração, 884 resultados de preço. **Nenhum preço foi calculado
  por este sistema** — todos os 884 resultados estão marcados
  `result_origin='IMPORTED_REFERENCE'`/`run_type='IMPORTED_REFERENCE_RUN'`
  (nunca `SYSTEM_CALCULATED`/`SYSTEM_RUN`) — ver [[04-DECISIONS]] D11.
- **Extensão de schema aditiva** (`database/v2/009_promotion.sql`):
  `audit.promotion_runs` (mesmo padrão de estado de
  `raw.ingest_batches`, Fase 3A); lineage/idempotência em
  `staging.*_candidates`; classificação de impacto em
  `staging.mapping_review`; `run_type`/`result_origin` em
  `pricing.runs`/`pricing.unit_price_results`; `classification` em
  `core.unit_typologies`. **Compatível com todo dado sintético já
  existente** (Fases 2B/2C) — reconfirmado por execução real após
  aplicar a mesma extensão no banco de teste.
- **Business keys nunca derivadas do nome do arquivo**: esquema
  determinístico a partir do hash SHA-256 do workbook
  (`DEV-<10 primeiros chars do sha, maiúsculo>`). `core.developments.name`
  deixado `NULL` deliberadamente.
- **4 achados reais durante a promoção, todos investigados contra
  `raw.cells` (leitura, nunca escrita) e nenhum corrigido por
  invenção**: (1) 2 parâmetros vazios por bug de extração de célula
  única (mesma classe do bug de `COALESCE` já visto na Fase 3A —
  corrigido em `scripts/ingest_xlsx_postgres.py` para futuras
  reingestões; os 2 valores já staged não foram retroativamente
  corrigidos); (2) 2 parâmetros vazios por referência de célula
  provavelmente incorreta no mapeamento privado (gap registrado, não
  investigado a fundo); (3) 2 entradas de calibração sem fator por
  ausência real de dado na fonte (preservado como anomalia); (4) um
  bug real de infraestrutura em `run_query_csv` (descartava
  silenciosamente linhas de resultado com uma única coluna `NULL`),
  encontrado pelo teste sintético público e corrigido — não afetou
  nenhum dado já promovido. Detalhe completo em
  `data/restricted/audit/core-pricing-promotion-report.md` e no
  worklog desta fase.
- **Reconciliação privada**: soma dos preços importados por
  desenvolvimento fecha com o VGV final já presente na fonte (lido
  só por leitura, nunca escrito) com diferença menor que R$ 0,20 em
  bases de R$ 195M/262M — explicável por arredondamento.
- **Idempotência confirmada contra PostgreSQL real**: reexecutar a
  promoção completa produz `ALREADY_PROMOTED`, zero linhas novas.
- **Teste público sintético criado**:
  `scripts/test_promote_staging_to_core.py` — 12 verificações,
  incluindo detecção de duplicidade real e rollback com marcação
  `FAILED`, usando somente dados fabricados em `raw`/`staging`
  (nunca um workbook real).
- **Dois checkpoints privados** (`pg_dump`, formato custom) em
  `data/restricted/backups/` (nunca versionado): `PRE_3B` (antes de
  qualquer escrita em `core`/`pricing`) e `POST_3B_PRE_REPRODUCTION`
  (depois da promoção bem-sucedida).
- **Banco de teste sintético (`patrimar_pricing_v2_test`, Fase 2C)
  confirmado intacto** ao final desta fase — `verify_postgres_v2.py`
  reexecutado com sucesso, hash lógico idêntico, mesmo depois de
  aplicar a extensão de schema 009 nele também (aditiva, sem afetar
  dado existente).
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
11. `55139eb` — `feat: add controlled private data ingestion pipeline` (Fase 3A).
12. (Fase 3B) commit — `feat: promote private staging into canonical
    pricing model` (`database/v2/009_promotion.sql`,
    `scripts/promote_staging_to_core.py`,
    `scripts/test_promote_staging_to_core.py`,
    `scripts/ingest_xlsx_postgres.py` corrigido (2 bugs),
    `scripts/db_v2_apply.ps1` atualizado,
    `docs/15-STAGING-TO-CANONICAL-PROMOTION.md`, `docs/03-ROADMAP.md`,
    `docs/04-DECISIONS.md`, `docs/05-WORKLOG.md`,
    `docs/07-DATA-DICTIONARY.md`, `docs/11-DATABASE-V2-DESIGN.md`,
    `docs/99-HANDOFF.md`, `database/v2/README.md` — tudo
    público/genérico, nenhum dado privado, nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. Nenhum
`.env.*` ou `.dump` nunca foi (e não pode ser) adicionado a nenhum
commit.

## Arquivos criados/alterados nesta fase (Fase 3B)

```
docs/15-STAGING-TO-CANONICAL-PROMOTION.md              (novo)
docs/03-ROADMAP.md, 04-DECISIONS.md, 05-WORKLOG.md,
  07-DATA-DICTIONARY.md, 11-DATABASE-V2-DESIGN.md,
  99-HANDOFF.md                                         (atualizados)
database/v2/009_promotion.sql                          (novo)
database/v2/README.md                                   (atualizado)
scripts/promote_staging_to_core.py                     (novo)
scripts/test_promote_staging_to_core.py                (novo — teste público sintético)
scripts/ingest_xlsx_postgres.py                         (corrigido — 2 bugs reais, ver worklog)
scripts/db_v2_apply.ps1                                 (atualizado — inclui 009_promotion.sql)
data/restricted/audit/core-pricing-promotion-report.md  (LOCAL, NAO versionado)
data/restricted/audit/core-pricing-profile.csv          (LOCAL, NAO versionado)
data/restricted/backups/private_dev_PRE_3B_*.dump       (LOCAL, NAO versionado)
data/restricted/backups/private_dev_POST_3B_PRE_REPRODUCTION_*.dump (LOCAL, NAO versionado)
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
   metodologia real** — ver [[04-DECISIONS]] D8. Ainda não usado
   sobre dado real.
5. **Nenhum resultado de preço real ainda é `SYSTEM_CALCULATED`** —
   os 884 resultados promovidos na Fase 3B são todos
   `IMPORTED_REFERENCE`. Qualquer código futuro que consulte
   `pricing.unit_price_results` sem filtrar/exibir `result_origin`
   corre o risco de apresentar um número importado como se fosse um
   cálculo do sistema — ver [[04-DECISIONS]] D11.
6. **4 achados reais da Fase 3B ainda pendentes de resolução** (não
   bloqueiam nada, mas não foram corrigidos): 2 parâmetros
   `CALIBRATION_LOOKUP_COLUMN_INDEX` prontos para repromoção (bug de
   extração já corrigido, valor staged ainda não atualizado); 2
   parâmetros `POSITION_ADJUSTMENT_MODE` com referência de célula
   possivelmente incorreta no mapeamento privado (não investigado a
   fundo); 2 entradas de calibração sem fator por ausência real na
   fonte (não é um bug, é dado ausente). Ver
   `data/restricted/audit/core-pricing-promotion-report.md`.
7. **Dois bancos PostgreSQL locais no mesmo servidor pré-existente**
   (`patrimar_pricing_v2_test` e `patrimar_pricing_v2_private_dev`) —
   nunca misturar dado real no banco `_test`, nem dado sintético de
   demonstração no banco `_private_dev` (ver D10). Ambos agora têm o
   schema 001-009 aplicado.
8. **13 itens em `staging.mapping_review`, agora classificados por
   impacto** (`review_classification`) — 3 `BLOCKING_CORE`, 2
   `BLOCKING_PRICING`, 4 `BUSINESS_CLARIFICATION`, 4 `NON_BLOCKING`.
   Nenhum foi promovido; útil para priorizar qual pergunta levar a
   Rodolfo primeiro.
9. **`main` e `rebuild/pricing-intelligence` divergirão** até decisão
   explícita de merge/substituição.
10. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte
    de dado real** — fora de escopo desta fase também.
11. **Perguntas ainda pendentes para quem forneceu a planilha** — ver
    `data/restricted/audit/questions-for-rodolfo.md`.
12. **A Fase 3C (reprodução independente da lógica de precificação
    real — motor real que produza `SYSTEM_CALCULATED`) ainda não foi
    iniciada.** Antes de iniciá-la, considerar levar as perguntas
    pendentes de Rodolfo ao responsável do projeto — várias decisões
    de cálculo dependem das respostas, e os 6 achados/gaps da Fase 3B
    (item 6 acima) devem ser revisitados primeiro.

## Comandos úteis já validados

```bash
npm run test:model
python scripts/test_reference_allocation_engine.py
python scripts/test_validate_db_v2.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql --file 008_ingestion.sql \
  --file 009_promotion.sql \
  --seed-file database/v2/seeds/001_demo_allocation.sql

# contra o banco de teste SINTÉTICO (requer .env.pricing_v2_test local e psql no PATH/PSQL_BIN):
powershell -File scripts/db_v2_create_test.ps1   # cria/recria banco+role de teste
powershell -File scripts/db_v2_apply.ps1 -WithSeed  # aplica DDL (001-009) + seed, fail-fast
powershell -File scripts/db_v2_verify.ps1        # compara banco real x expected.json (inclui hash)
powershell -File scripts/db_v2_drop_test.ps1     # remove o banco de teste (NÃO executar sem necessidade)

# testes públicos sintéticos do pipeline (contra qualquer banco "_test"):
python scripts/test_ingest_xlsx_postgres.py --env-file .env.pricing_v2_test
python scripts/test_promote_staging_to_core.py --env-file .env.pricing_v2_test

# ingestão/promoção real (NUNCA rodar contra o banco "_test" — só contra o banco privado dedicado):
python scripts/ingest_xlsx_postgres.py ingest-raw --input <arquivo.xlsx> --dry-run
python scripts/promote_staging_to_core.py --mode summary
python scripts/promote_staging_to_core.py --mode dry-run --ingest-batch-id <id> --mapping <mapeamento.json privado>
python scripts/promote_staging_to_core.py --mode apply --ingest-batch-id <id> --mapping <mapeamento.json privado>
```

## Próximo passo recomendado

**Fase 3C — Reprodução independente da lógica de precificação real.**
Com `core`/`pricing` já populados com as entidades reais (Fase 3B), o
próximo passo natural é implementar, como código executável, a
metodologia real reconstruída na Fase 1C (as 21 regras de negócio) —
produzindo, pela primeira vez, resultados `result_origin=
'SYSTEM_CALCULATED'` a partir dos parâmetros/calibrações já
promovidos — e comparar esse cálculo independente contra os
resultados `IMPORTED_REFERENCE` já persistidos, como validação. Antes
de iniciar, revisar os 6 achados/gaps pendentes da Fase 3B (seção de
riscos, item 6) e `data/restricted/audit/questions-for-rodolfo.md` —
várias decisões de cálculo (ex.: o mecanismo alternativo de ajuste de
posição, a origem da matriz de referência da aba Dispersão) dependem
de respostas ainda não obtidas.

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
