# AGENTS.md

Instruções para qualquer agente de IA (Codex, Gemini, modelos locais,
etc.) trabalhando neste repositório (`patrimar-hedonica` → Patrimar
Pricing Intelligence). Equivalente a `CLAUDE.md`, para agentes que lêem
`AGENTS.md` em vez de `CLAUDE.md`.

## Antes de fazer qualquer coisa

Leia, nesta ordem:

1. `docs/00-PROJECT-CHARTER.md`
2. `docs/01-CURRENT-STATE.md`
3. `docs/02-ARCHITECTURE.md`
4. `docs/03-ROADMAP.md`
5. `docs/04-DECISIONS.md`
6. `docs/99-HANDOFF.md`

Esses documentos são a fonte de verdade sobre o que existe, o que é
plano futuro, e o que já foi decidido. Não repita aqui o que já está
lá — apenas leia.

## Regras não negociáveis

- O repositório é a fonte permanente da verdade (ver `docs/04-DECISIONS.md`
  D1–D3). Nenhuma decisão, resultado de teste ou próximo passo relevante
  deve existir só numa conversa — escreva em `docs/`.
- Dados reais/restritos da Patrimar nunca vão para este repositório
  (ver D4).
- Nunca commite segredos (`DATABASE_URL` real, tokens, etc.). O
  `.gitignore` da raiz cobre `.env`, `.claude/settings.local.json` e
  `data/restricted/` — ainda assim, confira com `git status` antes de
  qualquer `git add`.
- Planilhas originais e qualquer dado real/privado da Patrimar/Rodolfo
  só podem existir localmente em `data/restricted/` (nunca na raiz de
  `data/`). Nada dentro dessa pasta pode ser commitado — ver
  `docs/04-DECISIONS.md` D6.
- Não faça commit, push ou crie branch sem o pedido explícito do
  responsável pelo projeto para aquela ação específica.

## Ao final de qualquer sessão de trabalho relevante

Atualize:
- `docs/05-WORKLOG.md` — adicione uma entrada nova (não apague entradas
  anteriores).
- `docs/99-HANDOFF.md` — reescreva para refletir o estado atual.

Isso garante que qualquer outro agente (incluindo Claude Code) consiga
continuar o trabalho sem depender do histórico desta sessão específica.
