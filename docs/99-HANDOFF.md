# 99 — Handoff

Este documento deve permitir que qualquer agente (ou pessoa) assuma o
projeto **sem ter acesso à conversa em que este trabalho foi feito**.
Leia isto, depois leia os documentos referenciados, na ordem sugerida.

## Ordem de leitura recomendada

1. [[00-PROJECT-CHARTER]] — por que este projeto existe.
2. [[01-CURRENT-STATE]] — o que de fato existe hoje, comprovado.
3. [[02-ARCHITECTURE]] — como as peças se conectam hoje.
4. [[03-ROADMAP]] — o que vem depois (ainda não implementado).
5. [[04-DECISIONS]] — regras que não devem ser quebradas sem registro.
6. [[08-SPREADSHEET-AUDIT-METHOD]] — metodologia da auditoria
   estrutural de planilhas (sem conteúdo privado).
7. [[09-PRICING-LOGIC-REVERSE-ENGINEERING]] — metodologia da
   engenharia reversa da lógica de precificação (sem conteúdo privado).
8. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 1C)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, enviada ao
  remote e rastreando `origin/rebuild/pricing-intelligence`. A branch
  `main` permanece intocada em `7dd1d24`, local e remotamente.
- **Tag do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`, no remote desde a Fase 0.6.
- **`.gitignore`** cobre `node_modules/`, `__pycache__/`/`*.pyc`,
  `.env`/`.env.*` (exceto `.env.example`), `.netlify/`,
  `.claude/settings.local.json` e `data/restricted/`. `data/` em si
  continua versionada normalmente (base sintética
  `hedonic_seed_hybrid.csv`).
- **Zona restrita local `data/restricted/`** (só localmente, nunca no
  Git — [[04-DECISIONS]] D6):
  - `raw/rodolfo/` — 2 arquivos originais, intactos. SHA-256
    revalidado contra `manifest-recebimento.csv` antes e depois desta
    fase, sem divergência.
  - `audit/` — além dos artefatos da Fase 1B (inventários estruturais
    e `structural-audit.md`), contém agora os artefatos da Fase 1C:
    `pricing_parameters_detected.csv`,
    `formula_consistency_flags.csv`, `business_rules_catalog.csv`
    (21 regras), `automation-map.csv`, `questions-for-rodolfo.md` (13
    perguntas), `pricing-logic-reconstruction.md`. Todos privados,
    ignorados pelo Git.
  - `staging/`, `derived/`, `quarantine/` — ainda vazias (a pasta
    `staging/` foi usada de forma transitória nesta fase para dois
    scripts geradores de CSV, já removidos ao final).
  - `README-LOCAL.md` — regras de cada subpasta.
- **Engenharia reversa da lógica de precificação concluída** sobre os
  dois workbooks: fluxo de cálculo reconstruído com evidência de
  fórmula (entradas → parâmetros → ajustes de pavimento/posição →
  agregação/rateio → preço → preço/m² → ponto de override humano). Os
  dois workbooks compartilham a mesma estrutura de cálculo; diferem
  nos valores de parâmetro e numa anomalia pontual confirmada em
  apenas um deles. Ver números agregados e sanitizados em
  [[05-WORKLOG]] (entrada da Fase 1C) —
  **nenhum nome real de aba/campo, fórmula específica ou valor está em
  documentação pública.**
- **Ferramentas reutilizáveis** (ambas Python, biblioteca padrão
  apenas, sem dependência externa nova, versionadas sem dado privado):
  - `scripts/audit_xlsx.py` (Fase 1B) + `scripts/test_audit_xlsx.py`.
  - `scripts/analyze_pricing_logic.py` (Fase 1C, reaproveita o parsing
    de `audit_xlsx.py`) + `scripts/test_analyze_pricing_logic.py`.
  Todas testadas com `--help`, `python -m py_compile`, e os
  respectivos testes de fumaça sintéticos — passaram.
- **Nenhum código de produção, schema de banco, ou comportamento de
  `index.html`/função Netlify foi alterado** em nenhuma fase até agora.
- `npm run test:model` re-executado nesta fase: **PASSOU**, mesmo
  resultado numérico das fases anteriores.

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence
   baseline`.
2. `e689be9` — `docs: record remote baseline backup`.
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase 1A).
4. `f21df3d` — `docs: record restricted data receipt` (Fase 1A.1).
5. `8472085` — `feat: add workbook structural audit tooling` (Fase 1B).
6. (Fase 1C) commit — `feat: add pricing logic reverse engineering`
   (`scripts/analyze_pricing_logic.py`,
   `scripts/test_analyze_pricing_logic.py`,
   `docs/09-PRICING-LOGIC-REVERSE-ENGINEERING.md`,
   `docs/03-ROADMAP.md`, `docs/05-WORKLOG.md`, `docs/99-HANDOFF.md` —
   todos sem dado privado).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit.

## Arquivos criados até agora neste histórico (Fase 0 a 1C)

```
docs/00-PROJECT-CHARTER.md .. docs/07-DATA-DICTIONARY.md   (Fase 0)
docs/08-SPREADSHEET-AUDIT-METHOD.md                         (Fase 1B)
docs/09-PRICING-LOGIC-REVERSE-ENGINEERING.md                (Fase 1C)
docs/99-HANDOFF.md   (este arquivo)
CLAUDE.md, AGENTS.md
.gitignore                                                  (Fase 0.5, ajustado na 1B)
scripts/audit_xlsx.py + test_audit_xlsx.py                  (Fase 1B)
scripts/analyze_pricing_logic.py + test_analyze_pricing_logic.py  (Fase 1C)
data/restricted/                        (local, NÃO versionado — Fase 1A em diante)
  raw/rodolfo/ — 2 arquivos originais recebidos (Fase 1A.1)
  audit/manifest-recebimento.csv                            (Fase 1A.1)
  audit/{workbook,sheet,field,formula,dependency,hidden_content,
         quality,cross_workbook}*.csv + structural-audit.md  (Fase 1B)
  audit/{pricing_parameters_detected,formula_consistency_flags,
         business_rules_catalog,automation-map}.csv,
  audit/{questions-for-rodolfo,pricing-logic-reconstruction}.md  (Fase 1C)
  staging/, derived/, quarantine/       (vazias)
  README-LOCAL.md
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `tests/model-smoke.mjs`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado em nenhuma
fase até agora.

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Ainda não resolvido.
2. **Não verificado em nenhuma auditoria até agora:** se o Netlify DB
   de produção está provisionado/populado, se o deploy Netlify está
   ativo, e se `GET /api/hedonic-data` responde em produção.
3. **Dados reais da Patrimar não devem ser commitados** — ver
   [[04-DECISIONS]] D4/D6. Qualquer dado real deve ir para
   `data/restricted/`, nunca para caminho versionado.
4. **A tag e a branch já estão no remote** desde a Fase 0.6. Novos
   commits locais ainda precisam de push explícito.
5. **`main` e `rebuild/pricing-intelligence` divergirão** — toda a
   evolução da nova plataforma acontece nesta branch (ou derivadas)
   até decisão explícita de merge/substituição.
6. **`data/restricted/` existe apenas localmente.** Se o ambiente
   local for perdido/trocado, a árvore, os arquivos recebidos e todos
   os artefatos de auditoria/reconstrução precisam ser
   recriados/reprocessados — nada disso está no Git por desenho.
7. **Detecção de cabeçalho/chave/PII na Fase 1B são heurísticas** — ver
   [[08-SPREADSHEET-AUDIT-METHOD]]. Nenhum campo foi classificado como
   chave única isolada nos dois workbooks; pode indicar chave composta
   não avaliada pela ferramenta, não ausência real de chave.
8. **Fórmulas compartilhadas do XLSX têm uma limitação de leitura
   conhecida**: para células que reaproveitam uma fórmula compartilhada
   sem texto próprio, as ferramentas mostram o texto da célula-mestre
   sem recalcular o deslocamento relativo de linha/coluna — ver seção
   "Cuidado com fórmulas compartilhadas" em
   [[09-PRICING-LOGIC-REVERSE-ENGINEERING]]. Toda regra no catálogo da
   Fase 1C foi confirmada contra o XML bruto antes de ser registrada,
   mas qualquer expansão futura da análise deve reconfirmar célula a
   célula antes de tratar uma divergência de fórmula como achado real.
9. **A interpretação de negócio (Fase 1C) tem pontos ambíguos e
   perguntas pendentes** para quem forneceu a planilha original —
   ver `data/restricted/audit/questions-for-rodolfo.md` (13 perguntas,
   3 críticas). O próximo agente não deve tratar a reconstrução da
   Fase 1C como definitiva antes dessas perguntas serem respondidas,
   especialmente as 3 críticas.
10. **Nem todas as 101 regiões de possível inconsistência de fórmula
    sinalizadas automaticamente na Fase 1C foram revisadas
    individualmente** — uma amostra foi confirmada manualmente (1
    anomalia real, várias linhas de total/subtotal identificadas como
    variação esperada), mas não há garantia de que as demais già
    tenham sido triadas. Não presumir que tudo o que está em
    `formula_consistency_flags.csv` já foi classificado com
    confiança alta.

## Comandos úteis já validados

```bash
npm run test:model            # único teste JS — PASSOU em todas as fases até agora
npm run generate:seed          # NÃO executado — sobrescreveria data/hedonic_seed_hybrid.csv
npm run generate:seed-migration # NÃO executado
git tag --list "legacy-hedonica*"
git log --oneline -7
git ls-remote --heads origin rebuild/pricing-intelligence
git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909
git check-ignore -v data/restricted/<arquivo>
python scripts/audit_xlsx.py --help
python scripts/analyze_pricing_logic.py --help
python scripts/test_audit_xlsx.py                     # teste sintético da auditoria estrutural
python scripts/test_analyze_pricing_logic.py           # teste sintético da engenharia reversa
python scripts/audit_xlsx.py --input <a.xlsx> --input <b.xlsx> --output-dir data/restricted/audit --workbook-id <id1> --workbook-id <id2>
python scripts/analyze_pricing_logic.py --input <a.xlsx> --input <b.xlsx> --output-dir data/restricted/audit --workbook-id <id1> --workbook-id <id2>
```

## Próximo passo recomendado

**Fase 1D — Gap analysis e modelo canônico preliminar.** Com a lógica
de precificação já reconstruída (Fase 1C) e a estrutura mapeada (Fase
1B), o próximo passo é comparar o que existe nas planilhas contra o
que já existe no laboratório atual (`MODEL.md`, schema em
`database/schema.sql`) para identificar lacunas (gaps) e desenhar,
ainda sem implementar, um modelo de dados canônico preliminar capaz de
representar tanto os dados sintéticos atuais quanto a lógica real
reconstruída. Antes disso, considerar levar as 3 perguntas CRITICAL de
`questions-for-rodolfo.md` ao responsável pelo projeto — várias
decisões de modelagem dependem das respostas (em especial: se o modo
alternativo de ajuste de posição é usado em algum cenário real, e o
critério que decide quando um override manual é aplicado).

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, fórmulas específicas, valores, ou qualquer conteúdo das
planilhas privadas em nenhum documento dentro de `docs/` — apenas
descrições sanitizadas e números agregados.
