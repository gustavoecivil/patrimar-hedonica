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
   (inclui D7 — dois motores separados; D8 — referência sintética não
   é metodologia oficial).
6. [[08-SPREADSHEET-AUDIT-METHOD]] — metodologia da auditoria
   estrutural de planilhas (sem conteúdo privado).
7. [[09-PRICING-LOGIC-REVERSE-ENGINEERING]] — metodologia da
   engenharia reversa da lógica de precificação (sem conteúdo privado).
8. [[10-PRICING-DOMAIN-MODEL]] — modelo de domínio e a separação
   Market Pricing Engine / Unit Price Allocation Engine.
9. [[11-DATABASE-V2-DESIGN]] — schema físico PostgreSQL v2.
10. [[12-REFERENCE-ALLOCATION-ENGINE]] — motor de referência sintético
    e prova end-to-end sobre o schema v2.
11. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 2B)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **Tag do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`, no remote desde a Fase 0.6.
- **Schema físico PostgreSQL v2** (`database/v2/`, Fase 2) agora tem
  **prova end-to-end com dados 100% sintéticos** (Fase 2B): um
  cenário fictício (1 empreendimento, 2 torres, 4 tipologias, 40
  unidades) foi processado pelo algoritmo público
  `REFERENCE_ALLOCATION_V1` e materializado em
  `database/v2/seeds/001_demo_allocation.sql` (391 `INSERT`s).
  **`REFERENCE_ALLOCATION_V1` não é a metodologia da Patrimar** — ver
  [[04-DECISIONS]] D8. `database/schema.sql` (legado) continua
  intocado. Nenhum banco real (produção ou local) foi tocado — nem
  PostgreSQL nem Docker estavam disponíveis no ambiente; toda
  validação foi estrutural.
- **Fonte única de verdade desta fase:**
  `fixtures/v2/reference_allocation_scenario.json`. Os demais
  artefatos (`reference_allocation_expected.json`,
  `reference_allocation_report.md`, o seed SQL) são **gerados**, não
  editados manualmente — regenerar com `python
  scripts/generate_v2_seed.py` sempre que a fixture ou o motor
  mudarem.
- **Determinismo comprovado:** o mesmo cenário produz sempre o mesmo
  hash lógico SHA-256
  (`9a955e218e71e806ab4906fbf06b0111d635649658732d4f4a6048261d3dcf8c`),
  verificado por teste automatizado, não apenas manualmente.
- **VGV fecha exatamente** no run `SYSTEM_ONLY` (R$ 10.000.000,00 =
  R$ 10.000.000,00, diferença 0,00) via reconciliação de resíduo de
  arredondamento — regra técnica desta referência, documentada, não
  regra de negócio Patrimar.
- **Override demonstrado** sem alterar histórico: preço sistemático
  permanece intocado em `pricing.unit_price_results`; o override é um
  evento novo em `pricing.unit_overrides`, com impacto no VGV exposto
  explicitamente (+R$ 50.000,00), sem qualquer rebalanceamento
  automático das demais unidades.
- **`scripts/validate_db_v2.py` estendido** (`--seed-file`) para
  validar o seed contra o DDL: tabelas/colunas existem, nenhuma coluna
  `GENERATED` recebe `INSERT` explícito, colunas obrigatórias
  presentes, toda FK resolvível na ordem em que as linhas aparecem.
  Executado com sucesso contra os 7 arquivos de DDL + o seed real.
- `npm run test:model` re-executado nesta fase: **PASSOU**, mesmo
  resultado numérico das fases anteriores.

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence baseline`.
2. `e689be9` — `docs: record remote baseline backup`.
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase 1A).
4. `f21df3d` — `docs: record restricted data receipt` (Fase 1A.1).
5. `8472085` — `feat: add workbook structural audit tooling` (Fase 1B).
6. `99a225a` — `feat: add pricing logic reverse engineering` (Fase 1C).
7. `f5a2cb2` — `docs: define Patrimar pricing domain model` (Fase 1D).
8. `e59157e` — `feat: design canonical PostgreSQL v2 schema` (Fase 2).
9. (Fase 2B) commit — `feat: prove unit allocation engine with
   synthetic scenario` (`fixtures/v2/*`,
   `database/v2/seeds/001_demo_allocation.sql`,
   `scripts/reference_allocation_engine.py`,
   `scripts/generate_v2_seed.py`,
   `scripts/test_reference_allocation_engine.py`,
   `scripts/validate_db_v2.py` (estendido),
   `scripts/test_validate_db_v2.py` (estendido),
   `docs/12-REFERENCE-ALLOCATION-ENGINE.md`, `docs/03-ROADMAP.md`,
   `docs/04-DECISIONS.md`, `docs/05-WORKLOG.md`,
   `docs/07-DATA-DICTIONARY.md`, `docs/99-HANDOFF.md` — tudo público/
   sintético, nenhum dado privado).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit.

## Arquivos criados até agora neste histórico (Fase 0 a 2B)

```
docs/00 .. docs/07 (Fase 0, atualizados em fases posteriores)
docs/08-SPREADSHEET-AUDIT-METHOD.md                    (Fase 1B)
docs/09-PRICING-LOGIC-REVERSE-ENGINEERING.md           (Fase 1C)
docs/10-PRICING-DOMAIN-MODEL.md                        (Fase 1D)
docs/11-DATABASE-V2-DESIGN.md                          (Fase 2)
docs/12-REFERENCE-ALLOCATION-ENGINE.md                 (Fase 2B)
docs/99-HANDOFF.md (este arquivo)
CLAUDE.md, AGENTS.md, .gitignore
scripts/audit_xlsx.py + test_audit_xlsx.py                    (Fase 1B)
scripts/analyze_pricing_logic.py + test_analyze_pricing_logic.py  (Fase 1C)
scripts/validate_db_v2.py + test_validate_db_v2.py            (Fase 2, estendido na 2B)
scripts/reference_allocation_engine.py                        (Fase 2B)
scripts/generate_v2_seed.py                                    (Fase 2B)
scripts/test_reference_allocation_engine.py                   (Fase 2B)
database/v2/001_schemas.sql .. 007_views.sql + README.md       (Fase 2 — database/schema.sql legado intocado)
database/v2/seeds/001_demo_allocation.sql                      (Fase 2B — 100% sintético)
fixtures/v2/reference_allocation_scenario.json                (Fase 2B — fonte única de verdade)
fixtures/v2/reference_allocation_expected.json                (Fase 2B — gerado)
fixtures/v2/reference_allocation_report.md                    (Fase 2B — gerado)
data/restricted/  (local, NÃO versionado — inalterado nesta fase)
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `tests/model-smoke.mjs`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado em nenhuma
fase até agora.

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Ainda não resolvido. Agora existem três schemas
   coexistindo (legado, v2, e o seed sintético dentro do v2) — manter
   claro qual é a fonte de verdade em cada contexto.
2. **Não verificado em nenhuma auditoria até agora:** se o Netlify DB
   de produção está provisionado/populado, se o deploy Netlify está
   ativo, e se `GET /api/hedonic-data` responde em produção.
3. **Dados reais da Patrimar não devem ser commitados** — ver
   [[04-DECISIONS]] D4/D6. Qualquer dado real deve ir para
   `data/restricted/`, nunca para caminho versionado.
4. **`REFERENCE_ALLOCATION_V1` nunca deve ser confundido com a
   metodologia real** — ver [[04-DECISIONS]] D8. Qualquer decisão de
   precificação real deve esperar a reconstrução privada da Fase 1C e
   as respostas pendentes de Rodolfo.
5. **O schema v2 ainda nunca foi executado contra um PostgreSQL
   real** — toda validação até agora (Fase 2 e 2B) foi estrutural
   (parsing Python próprio). A Fase 2C (execução real, ambiente local
   ou isolado) é o próximo passo natural antes de qualquer uso além
   de prova de conceito.
6. **`main` e `rebuild/pricing-intelligence` divergirão** — toda a
   evolução da nova plataforma acontece nesta branch até decisão
   explícita de merge/substituição.
7. **`data/restricted/` existe apenas localmente.** Perda do ambiente
   local exige recriar/reprocessar tudo — nada disso está no Git por
   desenho. (Não foi tocada nesta fase.)
8. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte de
   dado real** — nem estrutura de comparáveis/transações/ofertas foi
   criada (Fase 2), nem esta fase (2B) tentou provar o Motor A.
9. **Perguntas ainda pendentes para quem forneceu a planilha** — ver
   `data/restricted/audit/questions-for-rodolfo.md`. Não avançar para
   um motor de precificação real sem elas.
10. **Os artefatos `fixtures/v2/*` são derivados e regeneráveis** —
    se editados manualmente sem regenerar a partir da fixture
    canônica, podem divergir do motor/seed. Sempre regenerar via
    `scripts/generate_v2_seed.py` após qualquer mudança na fixture ou
    no motor.

## Comandos úteis já validados

```bash
npm run test:model            # único teste JS — PASSOU em todas as fases até agora
git tag --list "legacy-hedonica*"
git log --oneline -10
git ls-remote --heads origin rebuild/pricing-intelligence
git check-ignore -v data/restricted/<arquivo>

python scripts/reference_allocation_engine.py build-scenario --output fixtures/v2/reference_allocation_scenario.json
python scripts/reference_allocation_engine.py run --scenario fixtures/v2/reference_allocation_scenario.json
python scripts/reference_allocation_engine.py apply-override --scenario fixtures/v2/reference_allocation_scenario.json
python scripts/generate_v2_seed.py    # regenera seed SQL + expected + report a partir da fixture

python scripts/test_reference_allocation_engine.py
python scripts/test_validate_db_v2.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql \
  --seed-file database/v2/seeds/001_demo_allocation.sql
```

## Próximo passo recomendado

**Fase 2C — Execução real do schema em PostgreSQL local ou isolado.**
Com o DDL estruturalmente validado (Fase 2) e provado logicamente com
dados sintéticos (Fase 2B), o próximo passo é finalmente aplicar
`database/v2/*.sql` e `database/v2/seeds/001_demo_allocation.sql`
contra um PostgreSQL de fato (local, container, ou serviço de teste
isolado — nunca produção), para confirmar que o DDL roda sem erro de
sintaxe/semântica que a validação estrutural não pôde pegar, e que a
view `pricing.v_unit_price_current` retorna os valores esperados.
Isso deve preceder qualquer trabalho com dado real da Patrimar.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, fórmulas específicas, valores, ou qualquer conteúdo das
planilhas privadas em nenhum documento dentro de `docs/`, `fixtures/`
ou qualquer arquivo `.sql` — apenas descrições sanitizadas e números
agregados. Dados 100% sintéticos (como os de `fixtures/v2/` e
`database/v2/seeds/`) podem ser versionados livremente, desde que
verificados contra vazamento antes do commit.
