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
6. [[08-SPREADSHEET-AUDIT-METHOD]] — metodologia da auditoria de
   planilhas (sem conteúdo privado).
7. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 1B)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, enviada ao
  remote e rastreando `origin/rebuild/pricing-intelligence`. A branch
  `main` permanece intocada em `7dd1d24`, local e remotamente — nenhum
  merge foi feito.
- **Tag do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`, enviada ao remote na Fase
  0.6.
- **`.gitignore`** na raiz cobre `node_modules/`, `.env`/`.env.*`
  (exceto `.env.example`), `.netlify/`, `.claude/settings.local.json` e
  `data/restricted/`. `data/` em si continua versionada normalmente
  (base sintética `hedonic_seed_hybrid.csv`).
- **Zona restrita local `data/restricted/`** (existe só localmente,
  nunca no Git — [[04-DECISIONS]] D6):
  - `raw/rodolfo/` — 2 arquivos originais recebidos, intactos.
    Integridade (SHA-256) verificada antes e depois da auditoria
    estrutural desta fase, sem divergência.
  - `audit/` — contém `manifest-recebimento.csv` (Fase 1A.1) e, desde
    esta fase, os artefatos da auditoria estrutural:
    `workbook_inventory.csv`, `sheet_inventory.csv`,
    `field_profile.csv`, `formula_inventory.csv`,
    `dependency_inventory.csv`, `hidden_content_inventory.csv`,
    `quality_issues.csv`, `cross_workbook_mapping.csv`,
    `structural-audit.md`. Todos privados, ignorados pelo Git.
  - `staging/`, `derived/`, `quarantine/` — ainda vazias (não usadas
    nesta fase).
  - `README-LOCAL.md` — regras de cada subpasta.
- **Auditoria estrutural concluída** sobre os dois workbooks: 8 abas
  (todas visíveis), 77 campos detectados, ~18,4 mil células com
  fórmula agrupadas em 430 padrões normalizados, 10 arestas de
  dependência entre abas, 0 vínculos externos/macros/pivot tables, 0
  campos com potencial PII, 705 problemas de qualidade registrados
  (majoritariamente linhas vazias dentro de intervalos de dados). Ver
  números completos e sanitizados em [[05-WORKLOG]] (entrada da Fase
  1B) — **nenhum nome real de aba/campo está em documentação pública.**
  O conteúdo de negócio (o que cada fórmula representa, qual é a
  lógica de precificação) **ainda não foi interpretado** — isso é a
  Fase 1C.
- **Ferramenta reutilizável criada:** `scripts/audit_xlsx.py`
  (biblioteca padrão do Python apenas, sem dependência externa nova) +
  teste de fumaça com dados sintéticos `scripts/test_audit_xlsx.py`.
  Ambos versionados (não contêm dado privado). Testados com `--help`,
  `python -m py_compile`, e execução completa do teste sintético —
  todos passaram.
- **Nenhum código de produção, schema de banco, ou comportamento de
  `index.html`/função Netlify foi alterado** em nenhuma fase até agora.
- `npm run test:model` re-executado nesta fase: **PASSOU**, mesmo
  resultado numérico das fases anteriores (modelo/gerador não
  tocados).

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence
   baseline` (`docs/`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`).
2. `e689be9` — `docs: record remote baseline backup`.
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase
   1A).
4. `f21df3d` — `docs: record restricted data receipt` (Fase 1A.1).
5. (Fase 1B) commit — `feat: add workbook structural audit tooling`
   (`scripts/audit_xlsx.py`, `scripts/test_audit_xlsx.py`,
   `docs/03-ROADMAP.md`, `docs/05-WORKLOG.md`, `docs/99-HANDOFF.md`,
   `docs/08-SPREADSHEET-AUDIT-METHOD.md` — todos sem dado privado).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit.

## Arquivos criados até agora neste histórico (Fase 0 a 1B)

```
docs/00-PROJECT-CHARTER.md
docs/01-CURRENT-STATE.md
docs/02-ARCHITECTURE.md
docs/03-ROADMAP.md
docs/04-DECISIONS.md
docs/05-WORKLOG.md
docs/06-LESSONS-LEARNED.md
docs/07-DATA-DICTIONARY.md
docs/08-SPREADSHEET-AUDIT-METHOD.md   (Fase 1B)
docs/99-HANDOFF.md   (este arquivo)
CLAUDE.md
AGENTS.md
.gitignore                              (Fase 0.5)
scripts/audit_xlsx.py                   (Fase 1B — genérico, sem dado privado)
scripts/test_audit_xlsx.py              (Fase 1B — teste com dados sintéticos)
data/restricted/                        (local, NÃO versionado — Fase 1A em diante)
  raw/rodolfo/ — 2 arquivos originais recebidos (Fase 1A.1)
  audit/manifest-recebimento.csv        (Fase 1A.1)
  audit/{workbook,sheet,field,formula,dependency,hidden_content,
         quality,cross_workbook}*.csv + structural-audit.md  (Fase 1B)
  staging/, derived/, quarantine/       (ainda vazias)
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
   local for perdido/trocado, a árvore, os arquivos recebidos e os
   artefatos de auditoria precisam ser recriados/reprocessados — nada
   disso está no Git por desenho.
7. **A interpretação de negócio das planilhas ainda não foi feita.**
   A Fase 1B levantou estrutura (abas, campos, fórmulas, dependências,
   qualidade) mas não interpretou o que cada fórmula/campo significa
   comercialmente. O próximo agente não deve presumir que já existe
   entendimento da lógica de precificação — isso é exatamente o
   objetivo da Fase 1C.
8. **Detecção de cabeçalho, chave candidata e PII na ferramenta de
   auditoria são heurísticas**, não verdade absoluta — ver seção
   "Limitações conhecidas" em [[08-SPREADSHEET-AUDIT-METHOD]]. Em
   particular, nenhum campo foi classificado como candidato a chave
   única nos dois workbooks auditados; isso pode refletir chaves
   compostas (não detectadas por esta primeira versão da ferramenta,
   que só avalia colunas isoladas) ou ausência real de chave única —
   requer revisão manual na Fase 1C.

## Comandos úteis já validados

```bash
npm run test:model            # único teste JS, roda local, sem rede, sem banco — PASSOU em todas as fases até agora
npm run generate:seed          # NÃO executado — sobrescreveria data/hedonic_seed_hybrid.csv
npm run generate:seed-migration # NÃO executado — sobrescreveria a migração de seed
git tag --list "legacy-hedonica*"                          # confirma a tag do legado
git log --oneline -6                                        # confirma os commits acima de 7dd1d24
git ls-remote --heads origin rebuild/pricing-intelligence   # confirma a branch remota
git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909  # confirma a tag remota
git check-ignore -v data/restricted/<arquivo>               # confirma que um arquivo da zona restrita está ignorado
python scripts/audit_xlsx.py --help                         # uso da ferramenta de auditoria
python scripts/test_audit_xlsx.py                           # teste de fumaça (dados sintéticos) da ferramenta
python scripts/audit_xlsx.py --input <a.xlsx> --input <b.xlsx> --output-dir data/restricted/audit --workbook-id <id1> --workbook-id <id2>
```

## Próximo passo recomendado

**Fase 1C — Engenharia reversa da lógica de precificação.** Com a
estrutura já mapeada (Fase 1B), o próximo passo é interpretar
manualmente/assistidamente o que as fórmulas e dependências
significam em termos de negócio (ex.: como o preço final é composto,
quais campos são entrada vs. resultado, qual a relação com as
variáveis já usadas no modelo hedônico sintético — ver `MODEL.md`).
Todo achado de negócio (nomes reais, fórmulas interpretadas, valores)
deve continuar exclusivamente em `data/restricted/` — apenas
conclusões metodológicas genéricas podem eventualmente virar
documentação pública, e só com revisão explícita antes de qualquer
commit.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, ou qualquer conteúdo das planilhas privadas em nenhum
documento dentro de `docs/` — apenas descrições sanitizadas e números
agregados.
