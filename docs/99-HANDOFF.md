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
   lógica real é configuração privada; D13 evidência classificada +
   prova estrutural antes de comparar contra o preço de referência).
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
11. [[17-AMBIGUITY-RESOLUTION-METHOD]] — fechamento forense das
    ambiguidades que bloqueavam a Fase 3C (Fase 3D,
    `NEAR_EXACT_WITH_EXPLAINED_ROUNDING`).
12. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-10, Fase 3D)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **A reprodução independente que a Fase 3C deixou bloqueada
  (884/884 unidades) foi desbloqueada nesta fase.** Resultado:
  **884/884 unidades reproduzidas de forma independente, dentro de 1
  centavo do preço já existente na fonte** — classificação
  `NEAR_EXACT_WITH_EXPLAINED_ROUNDING`. `MATHEMATICAL_REPRODUCTION_CONFIRMED
  = true`. `BUSINESS_SEMANTICS_CONFIRMED` permanece **parcial** — ver
  risco 6 abaixo.
- **Um dos dois bloqueios centrais da Fase 3C era um defeito de
  software, não uma ambiguidade de negócio**: a função que lia
  células de `raw.cells` por linha filtrava só pelo arquivo
  (`workbook_id`), não pela aba específica (`sheet_id`) — como abas
  diferentes do mesmo arquivo reaproveitam as mesmas letras de coluna
  para conteúdo totalmente diferente, a consulta misturava dado de
  abas distintas sob o mesmo número de linha. Corrigido em
  `scripts/run_pricing_reproduction.py`
  (`fetch_raw_columns_by_row` agora recebe `sheet_id`, nunca
  `workbook_id`). Isso também corrigiu, de quebra, a contagem de
  overrides (147 unidades corretas, não 188 como a Fase 3C havia
  reportado).
- **O outro bloqueio (tabela de calibração de posição nunca
  capturada) foi resolvido por engenharia reversa da fórmula real**:
  a fórmula usa uma busca horizontal com chave composta (2 campos já
  disponíveis) contra uma tabela cujo índice de linha é uma fórmula
  auto-documentada (`ROWS(...)` do próprio range) que sempre resolve
  para a última linha — nunca ambígua. A tabela foi reconstruída por
  **parsing genérico da fórmula real** (nova função pública,
  `fetch_composite_lookup_table_from_formula` — nenhuma
  fórmula/constante real hardcoded em código público).
- **Toda descoberta foi comprovada por evidência estrutural interna
  ANTES de qualquer comparação com o preço de referência** — nunca
  ajustada olhando o resultado final. Ver [[04-DECISIONS]] D13 e
  `data/restricted/audit/reproduction-change-log.md` para o histórico
  completo (issue/evidência/mudança/métrica antes-depois de cada
  achado).
- **Extensão genérica do motor público**
  (`scripts/pricing_reproduction_engine.py`): busca por chave
  composta (`lookup_table_composite`) e valor default explicitamente
  evidenciado para uma chave ausente específica
  (`missing_key_defaults`) — ambas testadas só com dados 100%
  fictícios (14/14 verificações).
- **Nova versão do ruleset privado** (`reproduction_rules_v2`, versão-
  mãe declarada) — a v1 da Fase 3C (com suas 3 sub-tentativas)
  permanece intacta no banco privado como histórico, nunca
  sobrescrita.
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
13. `9c06f38` — `feat: add independent pricing reproduction engine` (Fase 3C).
14. (Fase 3D) commit — `feat: add forensic ambiguity resolution
    workflow` (`scripts/pricing_reproduction_engine.py` ampliado,
    `scripts/run_pricing_reproduction.py` corrigido (bug de escopo de
    aba) + ampliado (parsing genérico de fórmula composta),
    `scripts/test_pricing_reproduction_engine.py` (14/14),
    `docs/17-AMBIGUITY-RESOLUTION-METHOD.md`, `docs/03-ROADMAP.md`,
    `docs/04-DECISIONS.md`, `docs/05-WORKLOG.md`,
    `docs/99-HANDOFF.md` — tudo público/genérico, nenhuma fórmula/
    constante/valor privado, nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. Nenhum
`.env.*` ou `.dump` nunca foi (e não pode ser) adicionado a nenhum
commit.

## Arquivos criados/alterados nesta fase (Fase 3D)

```
docs/17-AMBIGUITY-RESOLUTION-METHOD.md                 (novo)
docs/03-ROADMAP.md, 04-DECISIONS.md, 05-WORKLOG.md,
  99-HANDOFF.md                                         (atualizados)
scripts/pricing_reproduction_engine.py                 (ampliado — lookup_table_composite, missing_key_defaults)
scripts/run_pricing_reproduction.py                    (corrigido — bug de escopo de aba; ampliado — parsing generico de HLOOKUP composto)
scripts/test_pricing_reproduction_engine.py            (ampliado — 14/14, 2 verificacoes novas)
data/restricted/pricing_rules/reproduction_rules_v2.json (LOCAL, NAO versionado)
data/restricted/audit/ambiguity-resolution-summary.md   (LOCAL, NAO versionado)
data/restricted/audit/position-formula-trace.csv        (LOCAL, NAO versionado)
data/restricted/audit/area-semantics-analysis.csv       (LOCAL, NAO versionado)
data/restricted/audit/override-pattern-analysis.csv     (LOCAL, NAO versionado)
data/restricted/audit/missing-floor-factor-analysis.md  (LOCAL, NAO versionado)
data/restricted/audit/questions-for-rodolfo-final.md    (LOCAL, NAO versionado)
data/restricted/audit/reproduction-metrics.csv          (LOCAL, NAO versionado -- v1 preservada, secao v2 anexada)
data/restricted/audit/reproduction-change-log.md        (LOCAL, NAO versionado -- historico da Fase 3C preservado, secao Fase 3D anexada)
data/restricted/backups/private_dev_POST_3D_AMBIGUITY_RESOLUTION_*.dump (LOCAL, NAO versionado)
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `tests/model-smoke.mjs`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado em nenhuma
fase até agora — confirmado via `git log` em cada um deles nesta fase.
Nenhum arquivo de `database/v2/*.sql` foi alterado nesta fase (só
código Python/JSON e docs) — nenhuma migração nova foi necessária.

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
5. **Os 884 resultados reproduzidos (`result_origin='SYSTEM_CALCULATED'`,
   `run_type='REPRODUCTION_VALIDATION_RUN'`) ainda NÃO são produção**
   — vivem só como um run de validação no banco privado. Nenhuma API
   pública, frontend ou Netlify foi alterado. Nenhum código deve
   tratar esse run como recomendação de preço ou motor de produção
   sem uma decisão explícita futura.
6. **`BUSINESS_SEMANTICS_CONFIRMED` permanece parcial** — sabemos
   **como** a metodologia calcula (matematicamente confirmado), mas
   não **por que** ela usa os valores que usa em 2 pontos: (a) origem/
   critério dos valores da tabela de peso de posição (não a mecânica
   de uso — isso já está resolvido); (b) critério de negócio do
   ajuste manual por unidade. Ver
   `data/restricted/audit/questions-for-rodolfo-final.md` (2
   perguntas, prontas para consulta humana — NÃO enviadas a
   ninguém, apenas preparadas).
7. **Dois bancos PostgreSQL locais no mesmo servidor pré-existente**
   (`patrimar_pricing_v2_test` e `patrimar_pricing_v2_private_dev`) —
   nunca misturar dado real no banco `_test`, nem dado sintético de
   demonstração no banco `_private_dev` (ver D10).
8. **A resolução do "peso de posição" (P1) é sobre a MECÂNICA da
   tabela (onde ela fica, como é consultada), não sobre a ORIGEM dos
   valores dela** (por que cada percentual é o que é) — essa origem
   continua sendo uma pergunta de negócio pendente (risco 6a).
9. **`main` e `rebuild/pricing-intelligence` divergirão** até decisão
   explícita de merge/substituição.
10. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte
    de dado real** — fora de escopo desta fase também.
11. **Se uma fase futura promover os resultados reproduzidos a
    produção**, revisar antes: (a) as 2 perguntas pendentes de
    `questions-for-rodolfo-final.md`; (b) se o resíduo de meio
    centavo por unidade (explicado por precisão de dízima periódica
    na divisão de participação) precisa de um tratamento de
    arredondamento específico antes de virar preço "oficial" de
    produção — hoje ele é apenas documentado, nunca corrigido.

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

Com a reprodução matemática confirmada (`NEAR_EXACT_WITH_EXPLAINED_ROUNDING`),
há duas linhas de trabalho possíveis, não mutuamente exclusivas:

1. **Validação com Rodolfo** — levar as 2 perguntas de
   `data/restricted/audit/questions-for-rodolfo-final.md` (em
   português simples, sem jargão) para fechar
   `BUSINESS_SEMANTICS_CONFIRMED`. Recomendado antes de qualquer
   promoção a produção.
2. **Fase 4 — Market Pricing Engine e parâmetros de precificação** —
   com o Motor B (alocação) matematicamente reproduzido, o próximo
   domínio em aberto é o Motor A (estimativa de valor de mercado),
   que ainda não tem nenhuma fonte de dado real (ver
   [[10-PRICING-DOMAIN-MODEL]] e [[04-DECISIONS]] D7).

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
