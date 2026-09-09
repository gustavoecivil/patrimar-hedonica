# CLAUDE.md

Instruções para qualquer instância do Claude Code trabalhando neste
repositório (`patrimar-hedonica` → Patrimar Pricing Intelligence).

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
  deve existir só na conversa — escreva em `docs/`.
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
- Não faça commit, push ou crie branch sem o pedido explícito do usuário
  para aquela ação específica.

## Ao final de qualquer sessão de trabalho relevante

Atualize:
- `docs/05-WORKLOG.md` — adicione uma entrada nova (não apague entradas
  anteriores).
- `docs/99-HANDOFF.md` — reescreva para refletir o estado atual.

Isso garante que outro agente (Codex, Gemini, modelo local, ou você
mesmo em uma sessão futura) consiga continuar sem esta conversa.
