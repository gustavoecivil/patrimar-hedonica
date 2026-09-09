# 05 — Worklog

Registro cronológico de execuções relevantes. Entradas mais recentes no
topo. Cada agente que fizer trabalho relevante no projeto deve adicionar
uma entrada aqui.

---

## 2026-09-09 — Fase 0.5: Congelamento do legado e fundação segura (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** ponto de recuperação do legado, branch da nova plataforma,
`.gitignore`, governança de dados restritos, versionamento da
documentação da Fase 0. Sem push, sem alteração de modelo, banco,
frontend, função Netlify ou dados.

**Estado git confirmado no início:** branch `main`, HEAD `7dd1d24`
("fix: nomear série do gráfico de ajuste"), working tree com apenas
`AGENTS.md`, `CLAUDE.md`, `docs/` não rastreados (produzidos na Fase 0).

**Ações executadas:**

| Ação | Resultado |
|---|---|
| `git tag legacy-hedonica-pre-rebuild-20260909 7dd1d24` | tag local criada, confirmada apontando para `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0` |
| `git checkout -b rebuild/pricing-intelligence 7dd1d24` | nova branch criada a partir do legado; arquivos não rastreados da Fase 0 preservados |
| criação de `.gitignore` na raiz | inclui `node_modules/`, `.env`/`.env.*` (exceto `.env.example`), `.netlify/`, `.claude/settings.local.json`, `data/restricted/` — `data/` em si permanece versionada |
| atualização de [[04-DECISIONS]] (nova entrada D6) e [[03-ROADMAP]] | formalizam a zona restrita `data/restricted/` e a Fase 0.5 |
| `npm run test:model` | **PASSOU.** Saída: `{"rows":626,"R2":0.9017695081744214,"RMSE_test":4186.3075308912585,"MAPE_test":13.684152781394218,"max_VIF":11.83580058286043}` — idêntico à execução da Fase 0, confirmando que nada no modelo/gerador foi alterado |
| verificação de rastreamento de `.env`, `.claude/settings.local.json`, `data/restricted/` e busca por segredos óbvios | nenhum arquivo sensível rastreado; nenhum segredo encontrado |
| commit local único (`docs/`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`) | mensagem `chore: establish Patrimar Pricing Intelligence baseline` — ver hash em [[99-HANDOFF]] |

**Não realizado (fora do escopo desta fase):** push, qualquer alteração
em `index.html`, modelo OLS, `netlify/`, banco de dados, ou importação
de planilhas.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 0: Auditoria, inventário e documentação (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** somente leitura + 1 execução de teste local + criação de
documentação. Sem commit, sem push, sem branch, sem alteração de banco,
deploy ou comportamento de código existente.

**Estado git confirmado no início:**
- branch: `main`, up to date with `origin/main`
- working tree: clean
- último commit: `7dd1d24` "fix: nomear série do gráfico de ajuste"

**Comandos executados:**

| Comando | Resultado |
|---|---|
| `git status`, `git branch -vv`, `git log --oneline -20`, `git remote -v` | confirmaram estado acima |
| `find . -maxdepth 3` (excluindo `.git`, `node_modules`) | inventário de 12 arquivos versionados em 5 diretórios |
| `node -v` / `npm -v` | `v24.18.1` / `11.16.0` |
| `npm run test:model` | **PASSOU.** Saída: `{"rows":626,"R2":0.9017695081744214,"RMSE_test":4186.3075308912585,"MAPE_test":13.684152781394218,"max_VIF":11.83580058286043}` |
| `git status --short` (após o teste) | vazio — teste não alterou nenhum arquivo versionado |
| grep por `DATABASE_URL\|API_KEY\|SECRET\|PASSWORD\|postgres://` (case-insensitive) em todo o repo | ocorrências apenas em `tests/model-smoke.mjs` (checagem negativa) e `MODEL.md` (texto descritivo) — nenhum valor de segredo encontrado |
| `git check-ignore -v .claude/settings.local.json` | ignorado por regra **global** do usuário (`~/.config/git/ignore`), não por um `.gitignore` do projeto (que não existe) |
| `diff database/schema.sql netlify/database/migrations/20260829090000_create_hedonic_schema.sql` | arquivos semanticamente idênticos, com diferenças triviais de formatação (`BEGIN/COMMIT` e espaçamento de `JOIN`) |

**Scripts inspecionados mas NÃO executados** (para não gerar/sobrescrever
arquivos sem necessidade): `scripts/generate-hybrid-seed.mjs`,
`scripts/generate-seed-migration.mjs`.

**Documentos criados:** ver [[99-HANDOFF]] → seção "Arquivos criados
nesta sessão".

**Testes:** 1 de 1 disponível, executado, aprovado, sem warnings visíveis
na saída padrão/erro.

**Riscos identificados:** ver relatório final desta sessão e
[[06-LESSONS-LEARNED]] (estrutura criada, sem conteúdo ainda — riscos
já conhecidos estão descritos em [[01-CURRENT-STATE]] e no relatório
final, não duplicados aqui).

**Próximo passo recomendado ao final desta sessão:** ver [[99-HANDOFF]].
