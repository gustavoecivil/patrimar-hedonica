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
   (inclui D7 — dois motores separados).
6. [[08-SPREADSHEET-AUDIT-METHOD]] — metodologia da auditoria
   estrutural de planilhas (sem conteúdo privado).
7. [[09-PRICING-LOGIC-REVERSE-ENGINEERING]] — metodologia da
   engenharia reversa da lógica de precificação (sem conteúdo privado).
8. [[10-PRICING-DOMAIN-MODEL]] — modelo de domínio e a separação
   Market Pricing Engine / Unit Price Allocation Engine (sem conteúdo
   privado).
9. [[11-DATABASE-V2-DESIGN]] — schema físico PostgreSQL v2 (sem
   conteúdo privado).
10. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 2)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **Tag do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`, no remote desde a Fase 0.6.
- **Schema físico PostgreSQL v2 criado em `database/v2/`** (7 arquivos
  `.sql` + `README.md`), em 4 schemas próprios (`core`, `pricing`,
  `audit`, `market`), 21 tabelas + 1 view. **`database/schema.sql`
  (legado) não foi tocado** e continua em uso pelo laboratório
  hedônico — os dois coexistem em paralelo, sem migração de dado
  ainda. Nenhum banco de produção, PostgreSQL local, Netlify,
  frontend ou modelo OLS foi alterado.
- **Correção de contagem registrada:** o relatório final da Fase 1D
  dizia 15 entidades candidatas, mas a lista continha 16 nomes (um
  item nomeava duas entidades). O número correto — 16 — está
  registrado em [[11-DATABASE-V2-DESIGN]] e `database/v2/README.md`.
- **Perguntas bloqueadoras de schema (Q-05, Q-12) resolvidas por
  desenho**, não por resposta de Rodolfo — o schema modela a
  incerteza (campo genérico extensível; versionamento por padrão,
  independente da frequência real) em vez de assumir uma hipótese não
  comprovada. As perguntas continuam registradas e pendentes em
  `data/restricted/audit/questions-for-rodolfo.md` para quando
  Rodolfo puder respondê-las — a estrutura física não depende disso.
- **Zona restrita local `data/restricted/`** (só localmente, nunca no
  Git — [[04-DECISIONS]] D6): recebeu, nesta fase, apenas
  `audit/database-v2-mapping.md` (mapeamento das planilhas reais para
  as tabelas físicas v2). Nenhum arquivo de fases anteriores foi
  alterado.
- **Ferramenta criada:** `scripts/validate_db_v2.py` (biblioteca
  padrão do Python, sem PostgreSQL/Docker disponíveis no ambiente) +
  teste de fumaça sintético `scripts/test_validate_db_v2.py`.
  Executada com sucesso contra os 7 arquivos reais de `database/v2/`.
- **Bug real encontrado e corrigido durante revisão manual do DDL**
  (`DISTINCT ON` sem `ORDER BY` na mesma consulta, em
  `007_views.sql`) — documentado no commit e no worklog; não é um
  problema estrutural sinalizável pelo validador genérico (que não
  entende semântica de `DISTINCT ON`), só detectável por leitura
  humana cuidadosa. Qualquer expansão futura deste schema deve
  continuar revisando manualmente semântica de SQL que o validador
  estrutural não cobre.
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
8. (Fase 2) commit — `feat: design canonical PostgreSQL v2 schema`
   (`database/v2/*`, `scripts/validate_db_v2.py`,
   `scripts/test_validate_db_v2.py`, `docs/11-DATABASE-V2-DESIGN.md`,
   `docs/03-ROADMAP.md`, `docs/05-WORKLOG.md`, `docs/99-HANDOFF.md` —
   nenhum dado privado).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit.

## Arquivos criados até agora neste histórico (Fase 0 a 2)

```
docs/00 .. docs/07 (Fase 0, atualizados em fases posteriores)
docs/08-SPREADSHEET-AUDIT-METHOD.md                    (Fase 1B)
docs/09-PRICING-LOGIC-REVERSE-ENGINEERING.md           (Fase 1C)
docs/10-PRICING-DOMAIN-MODEL.md                        (Fase 1D)
docs/11-DATABASE-V2-DESIGN.md                          (Fase 2)
docs/99-HANDOFF.md (este arquivo)
CLAUDE.md, AGENTS.md, .gitignore
scripts/audit_xlsx.py + test_audit_xlsx.py                    (Fase 1B)
scripts/analyze_pricing_logic.py + test_analyze_pricing_logic.py  (Fase 1C)
scripts/validate_db_v2.py + test_validate_db_v2.py            (Fase 2)
database/v2/001_schemas.sql .. 007_views.sql + README.md       (Fase 2 — schema físico novo, database/schema.sql legado intocado)
data/restricted/  (local, NÃO versionado)
  raw/rodolfo/ — 2 arquivos originais                  (Fase 1A.1)
  audit/manifest-recebimento.csv                       (Fase 1A.1)
  audit/{workbook,sheet,field,formula,dependency,hidden_content,
         quality,cross_workbook}*.csv + structural-audit.md  (Fase 1B)
  audit/{pricing_parameters_detected,formula_consistency_flags,
         business_rules_catalog,automation-map}.csv,
  audit/{questions-for-rodolfo,pricing-logic-reconstruction}.md  (Fase 1C)
  audit/{pricing-gap-analysis,pricing-variable-matrix,
         data-acquisition-backlog}.csv,
  audit/{preliminary-canonical-model,gap-analysis-summary}.md  (Fase 1D)
  audit/database-v2-mapping.md                          (Fase 2)
  staging/, derived/, quarantine/  (vazias)
  README-LOCAL.md
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `tests/model-smoke.mjs`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado em nenhuma
fase até agora.

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Ainda não resolvido — e agora existe um terceiro
   schema (`database/v2/`) coexistindo com os outros dois, tornando
   ainda mais importante manter claro qual é a fonte de verdade em
   cada contexto (legado = produção atual; v2 = modelo canônico
   futuro, ainda não aplicado a nenhum banco real).
2. **Não verificado em nenhuma auditoria até agora:** se o Netlify DB
   de produção está provisionado/populado, se o deploy Netlify está
   ativo, e se `GET /api/hedonic-data` responde em produção.
3. **Dados reais da Patrimar não devem ser commitados** — ver
   [[04-DECISIONS]] D4/D6. Qualquer dado real deve ir para
   `data/restricted/`, nunca para caminho versionado.
4. **A tag e a branch já estão no remote** desde a Fase 0.6. Novos
   commits locais ainda precisam de push explícito.
5. **`main` e `rebuild/pricing-intelligence` divergirão** — toda a
   evolução da nova plataforma acontece nesta branch até decisão
   explícita de merge/substituição.
6. **`data/restricted/` existe apenas localmente.** Perda do ambiente
   local exige recriar/reprocessar tudo — nada disso está no Git por
   desenho.
7. **O schema v2 nunca foi executado contra um PostgreSQL real.** A
   validação foi inteiramente estrutural (parsing próprio em Python) —
   não há garantia absoluta de que todo DDL rode sem erro num servidor
   real até que isso seja testado de fato (recomendado como primeiro
   passo da Fase 2B, antes de qualquer seed de dados).
8. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte de
   dado real** — `market.observations`/`comparables`/`transactions`/
   `listings` foram deliberadamente NÃO criadas nesta fase. Não
   presumir que existe estrutura para comparáveis de mercado; ela
   precisa ser desenhada quando (e se) uma fonte real de dado de
   mercado for adquirida.
9. **Perguntas ainda pendentes para quem forneceu a planilha** — ver
   `data/restricted/audit/questions-for-rodolfo.md`. As duas
   bloqueadoras de schema (Q-05, Q-12) foram contornadas por desenho
   nesta fase, mas continuam sem resposta; as 5 que bloqueiam regra de
   negócio (Q-02, Q-03, Q-04, Q-08, Q-11) e a que bloqueia decisão de
   modelo (Q-07) continuam totalmente pendentes e devem ser levadas a
   Rodolfo antes de qualquer implementação de serviço/pipeline que
   dependa delas.
10. **O schema v2 não tem nenhum dado ainda — nem sintético, nem
    real.** A Fase 2B (seed sintético e prova do motor de rateio) é o
    próximo passo natural antes de considerar qualquer migração do
    legado ou uso em produção.

## Comandos úteis já validados

```bash
npm run test:model            # único teste JS — PASSOU em todas as fases até agora
git tag --list "legacy-hedonica*"
git log --oneline -9
git ls-remote --heads origin rebuild/pricing-intelligence
git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909
git check-ignore -v data/restricted/<arquivo>
python scripts/audit_xlsx.py --help
python scripts/analyze_pricing_logic.py --help
python scripts/validate_db_v2.py --help
python scripts/test_audit_xlsx.py
python scripts/test_analyze_pricing_logic.py
python scripts/test_validate_db_v2.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql
```

## Próximo passo recomendado

**Fase 2B — Seed sintético e prova do motor de rateio.** Antes de
migrar qualquer dado real, popular o schema v2 com dado sintético
(gerado, não real) para provar que o Unit Price Allocation Engine
consegue de fato ser executado sobre ele de ponta a ponta (cadastro →
cenário → run → ajustes → resultado → override → validação),
idealmente contra um PostgreSQL real (local ou de teste) para
finalmente validar o DDL além da checagem estrutural. Isso também é o
momento de decidir se/como o laboratório hedônico legado passa a
alimentar `market.predictions` como uma primeira instância do Motor A.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, fórmulas específicas, valores, ou qualquer conteúdo das
planilhas privadas em nenhum documento dentro de `docs/` ou em
qualquer arquivo `.sql` — apenas descrições sanitizadas e números
agregados.
