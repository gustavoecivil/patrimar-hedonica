# 05 — Worklog

Registro cronológico de execuções relevantes. Entradas mais recentes no
topo. Cada agente que fizer trabalho relevante no projeto deve adicionar
uma entrada aqui.

---

## 2026-09-09 — Fase 1A: Recepção e preservação das planilhas do Rodolfo (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** preparação local da zona restrita para recepção de fontes
privadas da Patrimar. Nenhuma alteração em código, modelo, frontend,
API, Netlify ou banco. Nenhum conteúdo privado foi escrito neste
documento (ver `docs/04-DECISIONS.md` D4/D6).

**Estado confirmado antes de agir:** branch `rebuild/pricing-intelligence`,
working tree limpo.

**Ações executadas:**

| Ação | Resultado |
|---|---|
| Criação da árvore `data/restricted/{raw/rodolfo,audit,staging,derived,quarantine}/` | subpastas criadas para preservação, auditoria (hashes/manifesto), normalização, dados derivados e triagem de arquivos suspeitos |
| Validação com `git check-ignore -v` em arquivos de teste temporários dentro de `raw/rodolfo/` e `audit/` | ambos confirmados como ignorados pela regra `data/restricted/` do `.gitignore`; arquivos de teste removidos manualmente após a validação |
| Criação de `data/restricted/README-LOCAL.md` (privado, ignorado pelo Git) | documenta o propósito de cada subpasta e a regra de nunca editar arquivos em `raw/rodolfo/` |
| Verificação do conteúdo de `data/restricted/raw/rodolfo/` | pasta vazia nesta sessão — nenhuma busca automática foi feita no restante do computador |
| Abertura da pasta no Windows Explorer | zona restrita local preparada para recepção de fontes privadas da Patrimar; recepção manual das planilhas fica a cargo do responsável do projeto |

**Dados privados registrados neste documento:** nenhum. Nenhum nome de
arquivo, nome de empreendimento ou conteúdo de planilha foi escrito
aqui ou em qualquer outro documento público.

**Próximo passo recomendado:** ver [[99-HANDOFF]].

---

## 2026-09-09 — Fase 0.6: Backup remoto da fundação (Claude Code)

**Executor:** Claude Code (Sonnet 5), a pedido de Gustavo Santos.
**Escopo:** push explicitamente autorizado, limitado a dois refs.
**Autorização:** push explícito do responsável pelo projeto, restrito a
`rebuild/pricing-intelligence` e à tag
`legacy-hedonica-pre-rebuild-20260909`. Sem merge em `main`, sem
alteração em `main`, sem alteração de Netlify.

**Estado confirmado antes do push:** branch `rebuild/pricing-intelligence`,
HEAD `5ab265b` ("chore: establish Patrimar Pricing Intelligence
baseline"), working tree limpo, tag local apontando para `7dd1d24`.

**Ações executadas:**

| Ação | Resultado |
|---|---|
| `git push -u origin rebuild/pricing-intelligence` | branch remota criada; local passa a rastrear `origin/rebuild/pricing-intelligence` |
| `git push origin legacy-hedonica-pre-rebuild-20260909` | tag remota criada, apontando para `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0` |
| `git ls-remote --heads origin rebuild/pricing-intelligence` | confirma a branch remota no commit `5ab265b` |
| `git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909` | confirma a tag remota em `7dd1d24` |
| `git branch -vv` | `main` permanece em `7dd1d24` (`[origin/main]`), sem alteração |
| `git status` | working tree limpo antes e depois do push |

**Dados privados enviados:** nenhum — o conteúdo enviado é exatamente o
commit `5ab265b` já auditado na Fase 0.5 (`docs/`, `CLAUDE.md`,
`AGENTS.md`, `.gitignore`), mais a tag do legado (que aponta para o
commit legado já público em `main`). Nenhum arquivo de `data/restricted/`
existe no repositório, portanto nada disso pôde ser enviado.

**`main` alterada:** não. **Netlify alterado:** não. **Merge em `main`:**
não realizado.

**Próximo passo recomendado:** Fase 1A — recepção das planilhas do
Rodolfo, salvando qualquer arquivo real recebido em `data/restricted/`
antes de qualquer outra ação. Ver [[99-HANDOFF]].

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
