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
6. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado no fim desta sessão (2026-09-09, Fase 0.5)

- **Branch atual:** `rebuild/pricing-intelligence` (criada a partir de
  `7dd1d24`, ponto de partida da nova plataforma). A branch `main`
  permanece intocada em `7dd1d24`.
- **Tag local do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`. **Não foi enviada ao
  remote** (sem `git push`).
- **`.gitignore` criado** na raiz — cobre `node_modules/`, `.env`/
  `.env.*` (exceto `.env.example`), `.netlify/`,
  `.claude/settings.local.json` e `data/restricted/`. `data/` em si
  **continua versionada** (contém apenas a base sintética
  `hedonic_seed_hybrid.csv`).
- **Zona restrita `data/restricted/`** convencionada como local
  obrigatório para qualquer planilha real/privada da Patrimar/Rodolfo
  trazida ao ambiente local — ver [[04-DECISIONS]] D6. Nada dentro dela
  pode ser commitado.
- **Commit local único** nesta branch, acima de `7dd1d24`:
  `chore: establish Patrimar Pricing Intelligence baseline` — contém
  apenas `docs/`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`. Nenhum dado,
  nenhum segredo.
- **Nenhum código de produção, schema de banco, ou comportamento de
  `index.html`/função Netlify foi alterado.**
- **Nenhum push foi feito.** O remote `origin/main` continua em
  `7dd1d24`, sem a tag e sem a nova branch.
- `npm run test:model` executado após todas as mudanças: **PASSOU**,
  com o mesmo resultado numérico da Fase 0 (ver [[05-WORKLOG]]),
  confirmando que modelo/gerador não foram tocados.

## Arquivos criados nesta sessão (Fase 0 + Fase 0.5)

```
docs/00-PROJECT-CHARTER.md
docs/01-CURRENT-STATE.md
docs/02-ARCHITECTURE.md
docs/03-ROADMAP.md
docs/04-DECISIONS.md
docs/05-WORKLOG.md
docs/06-LESSONS-LEARNED.md
docs/07-DATA-DICTIONARY.md
docs/99-HANDOFF.md   (este arquivo)
CLAUDE.md
AGENTS.md
.gitignore            (novo na Fase 0.5)
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `scripts/`, `tests/`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado.

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Os dois arquivos precisam ser editados juntos até que
   um deles seja eliminado em favor do outro como única fonte de
   verdade — decisão ainda não tomada.
2. **Não verificado nesta ou na auditoria anterior:** se o Netlify DB de
   produção está provisionado e populado, se o deploy Netlify está
   ativo, e se `GET /api/hedonic-data` responde em produção. Não há
   `netlify.toml` no repositório.
3. **Dados reais da Patrimar não devem ser commitados** neste
   repositório enquanto ele permanecer com o remote atual (público) —
   ver [[04-DECISIONS]] D4 e D6. Qualquer planilha real deve ir para
   `data/restricted/`, nunca para a raiz de `data/`.
4. **A tag e a branch novas existem apenas localmente.** Se o
   repositório local for perdido antes de um push futuro (autorizado
   explicitamente por Gustavo), o ponto de recuperação do legado se
   perde. Isso é aceito por ora porque push não foi autorizado nesta
   sessão.
5. **`main` e `rebuild/pricing-intelligence` divergirão** a partir de
   agora — `main` continua sendo o histórico do laboratório legado tal
   como estava em `7dd1d24`; toda a evolução da nova plataforma deve
   acontecer em `rebuild/pricing-intelligence` (ou branches derivadas
   dela) até uma decisão explícita de merge/substituição.

## Comandos úteis já validados nesta sessão

```bash
npm run test:model            # único teste, roda local, sem rede, sem banco — PASSOU em 2026-09-09 (Fase 0 e Fase 0.5)
npm run generate:seed          # NÃO executado — sobrescreveria data/hedonic_seed_hybrid.csv
npm run generate:seed-migration # NÃO executado — sobrescreveria a migração de seed
git tag --list "legacy-hedonica*"           # confirma a tag do legado
git log -2 --oneline                        # confirma o novo commit acima de 7dd1d24
```

## Próximo passo recomendado

Validar com o responsável do projeto (Gustavo) qual item do
[[03-ROADMAP]] deve ser a Fase 1 dentro de
`rebuild/pricing-intelligence` — a recomendação natural, dado o
princípio de independência das planilhas ([[00-PROJECT-CHARTER]]) e a
zona restrita já criada ([[04-DECISIONS]] D6), é começar pela
**auditoria das planilhas do Rodolfo**, salvando qualquer arquivo real
recebido em `data/restricted/` antes de qualquer outra ação.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/reescrito,
pois reflete sempre o estado *atual*, não o histórico).
