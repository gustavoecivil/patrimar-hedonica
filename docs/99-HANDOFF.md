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
   resultado importado nunca confundido com resultado calculado; D12
   lógica real é configuração privada, código público é infra
   genérica).
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
10. [[16-INDEPENDENT-PRICING-REPRODUCTION]] — tentativa de reprodução
    independente da lógica de precificação real (Fase 3C,
    `PARTIAL_REPRODUCTION`).
11. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-10, Fase 3C)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **Primeira tentativa real de calcular preço de forma independente
  da planilha.** Resultado: **`PARTIAL_REPRODUCTION`** — nenhuma das
  884 unidades reais chegou a um preço final reproduzido
  (`result_origin='SYSTEM_CALCULATED'`), mas uma regra de calibração
  (busca por pavimento, com derivação de chave evidenciada por
  fórmula e tabela real já promovida na Fase 3B) foi reproduzida de
  ponta a ponta para 880/884 unidades. Ver [[04-DECISIONS]] D11/D12.
- **Bloqueio central identificado com precisão**: uma segunda tabela
  de calibração (peso de posição) nunca foi capturada como candidato
  de staging nas fases anteriores (Fase 3A só mapeou a dimensão de
  pavimento) — isso bloqueia toda a cadeia até o preço final,
  **independentemente** de qualquer outro problema. Não é uma falha
  de compreensão da lógica (a fórmula em si tem confiança `HIGH`,
  evidenciada desde a Fase 1C) — é uma lacuna de dado disponível.
- **Achado real e retratado durante a fase**: uma tentativa de usar
  2 componentes de área ainda não promovidos (disponíveis só em
  `raw.cells`) produziu valores numericamente implausíveis quando
  testada contra o dado real — 3 tentativas sucessivas, cada uma mais
  conservadora que a anterior, todas preservadas no banco como
  histórico de convergência (nunca um filtro inventado para "fazer
  bater"). Detalhe completo em
  `data/restricted/audit/reproduction-change-log.md`.
- **Isolamento do preço de referência confirmado estruturalmente**: o
  motor de cálculo nunca teve, em nenhum momento, acesso a
  `pricing.unit_price_results` durante o cálculo — só depois, numa
  fase de validação separada.
- **Determinismo e idempotência confirmados contra PostgreSQL real**:
  mesmo input produz mesmo hash lógico; reexecutar a mesma
  `(development, ruleset_version)` produz `ALREADY_REPRODUCED`, zero
  linhas novas.
- **Extensão de schema aditiva** (`database/v2/010_reproduction.sql`):
  `pricing.runs.run_type` ganha `REPRODUCTION_VALIDATION_RUN`;
  `audit.reproduction_runs`; `pricing.reproduction_comparisons`.
  **Compatível com todo dado sintético já existente** (Fases 2B/2C) —
  reconfirmado por execução real após aplicar a mesma extensão no
  banco de teste.
- **Arquitetura engine/ruleset estabelecida como padrão** (D12): todo
  motor futuro que opere sobre a metodologia real deve seguir o mesmo
  padrão — catálogo de operações genéricas em código público,
  parâmetros/constantes/tabelas reais exclusivamente em
  `data/restricted/pricing_rules/`.
- **Teste público sintético criado**:
  `scripts/test_pricing_reproduction_engine.py` — 12 verificações
  (DAG, ciclo, dependência ausente, `Decimal`, regra dormente,
  bloqueio transitivo, isolamento do preço de referência,
  determinismo), usando exclusivamente regras fictícias.
- **Banco de teste sintético (`patrimar_pricing_v2_test`, Fase 2C)
  confirmado intacto** ao final desta fase.
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
12. `72d798c` — `feat: promote private staging into canonical pricing model` (Fase 3B).
13. (Fase 3C) commit — `feat: add independent pricing reproduction
    engine` (`database/v2/010_reproduction.sql`,
    `scripts/pricing_reproduction_engine.py`,
    `scripts/run_pricing_reproduction.py`,
    `scripts/test_pricing_reproduction_engine.py`,
    `docs/16-INDEPENDENT-PRICING-REPRODUCTION.md`,
    `docs/03-ROADMAP.md`, `docs/04-DECISIONS.md`,
    `docs/05-WORKLOG.md`, `docs/07-DATA-DICTIONARY.md`,
    `docs/99-HANDOFF.md`, `database/v2/README.md` — tudo
    público/genérico, nenhuma fórmula/constante/valor privado,
    nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. Nenhum
`.env.*` ou `.dump` nunca foi (e não pode ser) adicionado a nenhum
commit.

## Arquivos criados/alterados nesta fase (Fase 3C)

```
docs/16-INDEPENDENT-PRICING-REPRODUCTION.md            (novo)
docs/03-ROADMAP.md, 04-DECISIONS.md, 05-WORKLOG.md,
  07-DATA-DICTIONARY.md, 99-HANDOFF.md                  (atualizados)
database/v2/010_reproduction.sql                       (novo)
database/v2/README.md                                   (atualizado)
scripts/pricing_reproduction_engine.py                 (novo — motor generico publico)
scripts/run_pricing_reproduction.py                    (novo — runner contra o schema real)
scripts/test_pricing_reproduction_engine.py            (novo — teste publico sintetico)
scripts/db_v2_apply.ps1                                 (atualizado — inclui 010_reproduction.sql)
data/restricted/pricing_rules/reproduction_rules_v1.json (LOCAL, NAO versionado)
data/restricted/audit/reproduction-run-summary.md       (LOCAL, NAO versionado)
data/restricted/audit/reproduction-results.csv          (LOCAL, NAO versionado)
data/restricted/audit/reproduction-differences.csv      (LOCAL, NAO versionado)
data/restricted/audit/reproduction-rule-trace.csv       (LOCAL, NAO versionado)
data/restricted/audit/reproduction-metrics.csv          (LOCAL, NAO versionado)
data/restricted/audit/reproduction-change-log.md        (LOCAL, NAO versionado)
data/restricted/audit/questions-for-rodolfo-shortlist-3c.md (LOCAL, NAO versionado)
data/restricted/backups/private_dev_POST_3C_REPRODUCTION_*.dump (LOCAL, NAO versionado)
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
   a Fase 3C tentou e ficou bloqueada. Qualquer código futuro que
   consulte `pricing.unit_price_results` sem filtrar/exibir
   `result_origin` corre o risco de apresentar um número importado
   como se fosse um cálculo do sistema — ver [[04-DECISIONS]] D11.
6. **O bloqueio central da Fase 3C é uma lacuna de PIPELINE, não de
   lógica**: uma segunda tabela de calibração (peso de posição) nunca
   foi capturada como candidato de staging na Fase 3A. Antes de
   tentar desbloquear isso numa fase futura, revisar
   `data/restricted/audit/questions-for-rodolfo-shortlist-3c.md`
   (prioridade P1) — pode exigir resposta de Rodolfo sobre como essa
   matriz é originalmente construída, não só uma correção técnica de
   pipeline.
7. **H/I (2 componentes de área) foram deliberadamente retratadas**
   como `DERIVED_FOR_REPRODUCTION` nesta fase, após 3 tentativas — os
   valores nas colunas correspondentes de `raw.cells`, para ambos os
   desenvolvimentos, contêm uma fração de linhas com conteúdo
   implausível como área. Não usar essas colunas em nenhuma fase
   futura sem entender essa anomalia primeiro (ver
   `reproduction-change-log.md` e P2 da shortlist).
8. **3 execuções de reprodução (3 `ruleset_version` distintas)
   coexistem no banco privado** como histórico de convergência —
   nunca apagadas, nunca "limpe o histórico" sem necessidade
   explícita; a versão oficial é a mais recente registrada em
   `data/restricted/audit/reproduction-metrics.csv` (privado — o
   hash específico nunca aparece em documentação pública).
9. **Dois bancos PostgreSQL locais no mesmo servidor pré-existente**
   (`patrimar_pricing_v2_test` e `patrimar_pricing_v2_private_dev`) —
   nunca misturar dado real no banco `_test`, nem dado sintético de
   demonstração no banco `_private_dev` (ver D10). Ambos agora têm o
   schema 001-010 aplicado.
10. **`main` e `rebuild/pricing-intelligence` divergirão** até decisão
    explícita de merge/substituição.
11. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte
    de dado real** — fora de escopo desta fase também.
12. **A Fase 3D (fechamento das ambiguidades que bloquearam a
    reprodução) ainda não foi iniciada.** Ver
    `data/restricted/audit/questions-for-rodolfo-shortlist-3c.md`
    para a lista priorizada do que precisa de resposta de Rodolfo
    antes de tentar desbloquear PR-007 (peso de posição) — o item que,
    sozinho, já impede qualquer preço final de ser reproduzido.

## Comandos úteis já validados

```bash
npm run test:model
python scripts/test_reference_allocation_engine.py
python scripts/test_validate_db_v2.py
python scripts/test_pricing_reproduction_engine.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql --file 008_ingestion.sql \
  --file 009_promotion.sql --file 010_reproduction.sql \
  --seed-file database/v2/seeds/001_demo_allocation.sql

# contra o banco de teste SINTÉTICO (requer .env.pricing_v2_test local e psql no PATH/PSQL_BIN):
powershell -File scripts/db_v2_create_test.ps1   # cria/recria banco+role de teste
powershell -File scripts/db_v2_apply.ps1 -WithSeed  # aplica DDL (001-010) + seed, fail-fast
powershell -File scripts/db_v2_verify.ps1        # compara banco real x expected.json (inclui hash)
powershell -File scripts/db_v2_drop_test.ps1     # remove o banco de teste (NÃO executar sem necessidade)

# testes públicos sintéticos do pipeline (contra qualquer banco "_test"):
python scripts/test_ingest_xlsx_postgres.py --env-file .env.pricing_v2_test
python scripts/test_promote_staging_to_core.py --env-file .env.pricing_v2_test
python scripts/test_pricing_reproduction_engine.py

# reprodução real (NUNCA rodar contra o banco "_test" — só contra o banco privado dedicado):
python scripts/run_pricing_reproduction.py --mode summary
python scripts/run_pricing_reproduction.py --mode dry-run --ruleset <ruleset.json privado>
python scripts/run_pricing_reproduction.py --mode apply --ruleset <ruleset.json privado>
```

## Próximo passo recomendado

**Fase 3D — Fechamento das ambiguidades e regras que bloquearam a
reprodução completa.** A Fase 3C isolou com precisão o que falta:
(1) a matriz de calibração de posição nunca foi capturada como
candidato de staging — precisa de uma nova rodada de mapeamento
(possivelmente Fase 3A revisitada) e/ou resposta de Rodolfo sobre
como ela é construída; (2) os componentes de área "varanda"/
"dependência" têm uma anomalia de conteúdo ainda não explicada. Antes
de iniciar, revisar
`data/restricted/audit/questions-for-rodolfo-shortlist-3c.md`
(prioridade P1 e P2) — as duas lacunas centrais dependem de
esclarecimento externo, não apenas de mais engenharia. Só depois
disso a reprodução deve ser reexecutada visando `EXACT_REPRODUCTION`
ou `NEAR_EXACT_WITH_EXPLAINED_ROUNDING`.

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
