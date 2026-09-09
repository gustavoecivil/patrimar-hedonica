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
   oficial; D9 testes de banco real isolados sem alterar servidor).
6. [[08-SPREADSHEET-AUDIT-METHOD]], [[09-PRICING-LOGIC-REVERSE-ENGINEERING]],
   [[10-PRICING-DOMAIN-MODEL]], [[11-DATABASE-V2-DESIGN]],
   [[12-REFERENCE-ALLOCATION-ENGINE]] — metodologia/modelo das fases
   anteriores, sem conteúdo privado.
7. [[13-POSTGRESQL-V2-RUNTIME-VALIDATION]] — execução real contra
   PostgreSQL, os dois defeitos encontrados e corrigidos.
8. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 2C)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **O schema v2 e o seed sintético agora rodam de verdade em
  PostgreSQL.** Banco de teste isolado `patrimar_pricing_v2_test`
  (PostgreSQL 18.4, servidor local pré-existente, nenhuma instalação
  nova) **permanece ativo** para a próxima fase — não foi removido.
  Credenciais em `.env.pricing_v2_test` (local, `.gitignore`, nunca
  commitado). Ver [[04-DECISIONS]] D9.
- **Dois defeitos reais foram encontrados e corrigidos** só ao
  executar contra PostgreSQL de fato (a validação estrutural da Fase
  2 não os detectava): (1) empate de timestamp entre as duas runs do
  seed deixava a view `pricing.v_unit_price_current` não
  determinística; (2) o hash lógico do motor de referência usava mais
  precisão do que a coluna `participation_share` persiste. Ambos
  corrigidos em `database/v2/007_views.sql`,
  `scripts/generate_v2_seed.py` e
  `scripts/reference_allocation_engine.py` — ver
  [[13-POSTGRESQL-V2-RUNTIME-VALIDATION]] para o detalhe completo.
  **O hash lógico mudou** de `9a955e21...` (Fase 2B) para
  `f065d105...` (Fase 2C, correto) — qualquer referência ao hash
  antigo em conversas/anotações anteriores está obsoleta.
- **Determinismo confirmado ponta a ponta**: hash recalculado a
  partir dos dados persistidos no PostgreSQL é idêntico ao hash do
  motor Python puro, inclusive depois de recriar o ambiente do zero
  duas vezes.
- **7 tentativas de inserção inválida, todas corretamente rejeitadas**
  pelo PostgreSQL real (FK, `CHECK` de preço negativo, `CHECK` de
  status inválido, `UNIQUE` de business_key duplicada, FK composta de
  override incoerente, `UNIQUE` de calibração duplicada, índice único
  parcial de segundo cenário `ACTIVE`).
- **Histórico confirmado preservado**: as duas runs coexistem, preço
  sistemático da unidade com override é idêntico nas duas (nunca
  sobrescrito), a tabela de overrides tem só 1 linha.
- **Ferramentas novas:** `scripts/verify_postgres_v2.py` (compara
  banco real × `fixtures/v2/reference_allocation_expected.json`,
  incluindo o hash lógico); `scripts/db_v2_create_test.ps1` /
  `db_v2_apply.ps1` / `db_v2_verify.ps1` / `db_v2_drop_test.ps1`
  (wrappers PowerShell, os que alteram dado recusam operar fora de um
  banco cujo nome contenha `_test` — testado).
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
10. (Fase 2C) commit — `test: validate pricing v2 on real PostgreSQL`
    (`database/v2/007_views.sql` corrigido,
    `scripts/generate_v2_seed.py` corrigido,
    `scripts/reference_allocation_engine.py` corrigido,
    `database/v2/seeds/001_demo_allocation.sql` regenerado,
    `fixtures/v2/reference_allocation_expected.json`/`report.md`
    regenerados, `scripts/verify_postgres_v2.py`,
    `scripts/db_v2_*.ps1`, `docs/13-POSTGRESQL-V2-RUNTIME-VALIDATION.md`,
    `docs/03-ROADMAP.md`, `docs/04-DECISIONS.md`, `docs/05-WORKLOG.md`,
    `docs/99-HANDOFF.md` — tudo público/sintético, nenhum dado
    privado, nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. `.env.pricing_v2_test`
nunca foi (e não pode ser) adicionado a nenhum commit.

## Arquivos criados/alterados até agora neste histórico (Fase 0 a 2C)

```
docs/00 .. docs/12 (fases anteriores)
docs/13-POSTGRESQL-V2-RUNTIME-VALIDATION.md            (Fase 2C)
docs/99-HANDOFF.md (este arquivo)
database/v2/007_views.sql                              (corrigido na Fase 2C — desempate defensivo)
database/v2/seeds/001_demo_allocation.sql              (regenerado na Fase 2C — timestamps deterministicos)
scripts/reference_allocation_engine.py                 (corrigido na Fase 2C — precisao do hash)
scripts/generate_v2_seed.py                            (corrigido na Fase 2C)
scripts/verify_postgres_v2.py                          (Fase 2C)
scripts/db_v2_create_test.ps1, db_v2_apply.ps1,
  db_v2_verify.ps1, db_v2_drop_test.ps1                (Fase 2C)
fixtures/v2/reference_allocation_expected.json,
  reference_allocation_report.md                       (regenerados na Fase 2C — hash novo)
.env.pricing_v2_test                                   (LOCAL, NAO versionado — credenciais do banco de teste)
data/restricted/  (local, NÃO versionado — inalterado nesta fase)
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
   `data/restricted/`, nunca para caminho versionado.
4. **`REFERENCE_ALLOCATION_V1` nunca deve ser confundido com a
   metodologia real** — ver [[04-DECISIONS]] D8.
5. **O banco de teste `patrimar_pricing_v2_test` está ativo num
   servidor PostgreSQL local pré-existente que provavelmente serve
   outros projetos do usuário** (visto em `D:\GSA\PostgreSQL\...`).
   Não assumir que é um servidor dedicado só a este projeto — nunca
   rodar comandos administrativos amplos (`DROP` de outros bancos,
   mudança de config global) nele. Os scripts `db_v2_*.ps1` já têm
   essa proteção embutida para o próprio banco de teste, mas o
   próximo agente deve manter a mesma cautela em qualquer comando
   manual.
6. **O hash lógico de referência mudou nesta fase** (de `9a955e21...`
   para `f065d105...`) por causa da correção de precisão — qualquer
   anotação/memória externa com o hash antigo está obsoleta.
7. **`main` e `rebuild/pricing-intelligence` divergirão** até decisão
   explícita de merge/substituição.
8. **`data/restricted/` existe apenas localmente** e não foi tocada
   nesta fase.
9. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte de
   dado real** — fora de escopo desta fase também.
10. **Perguntas ainda pendentes para quem forneceu a planilha** — ver
    `data/restricted/audit/questions-for-rodolfo.md`.
11. **Os dois defeitos corrigidos nesta fase (timestamp/precisão)
    só apareceram ao executar de verdade** — reforça que qualquer
    mudança futura no schema v2 ou no motor de referência deve ser
    revalidada contra um PostgreSQL real, não só pelo parser
    estrutural (`scripts/validate_db_v2.py`), antes de ser
    considerada confiável.

## Comandos úteis já validados

```bash
npm run test:model
python scripts/test_reference_allocation_engine.py
python scripts/test_validate_db_v2.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql \
  --seed-file database/v2/seeds/001_demo_allocation.sql

# contra o banco de teste real (requer .env.pricing_v2_test local e psql no PATH/PSQL_BIN):
powershell -File scripts/db_v2_create_test.ps1   # cria/recria banco+role de teste
powershell -File scripts/db_v2_apply.ps1 -WithSeed  # aplica DDL + seed, fail-fast
powershell -File scripts/db_v2_verify.ps1        # compara banco real x expected.json (inclui hash)
powershell -File scripts/db_v2_drop_test.ps1     # remove o banco de teste (NÃO executar sem necessidade — ver risco 5)
```

## Próximo passo recomendado

**Fase 3 — Ingestão controlada das planilhas para staging.** Com o
schema v2 provado (conceitual, sintético, e agora real em
PostgreSQL), o próximo passo natural é desenhar (não necessariamente
implementar ainda com dado real) a camada `staging` que vai receber
as planilhas reais de Rodolfo de forma controlada e auditável —
respeitando D4/D6 (nada de dado real fora de `data/restricted/` ou de
um banco que não seja tratado como restrito) e as perguntas ainda
pendentes em `questions-for-rodolfo.md`. Antes disso, considerar levar
essas perguntas ao responsável do projeto — várias decisões de
ingestão dependem das respostas.

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
