# 04 — Decisions

Registro de decisões estruturais do projeto. Cada entrada deve ter data,
decisão e motivo. Decisões aqui têm precedência sobre preferências
individuais de qualquer agente ou sessão de chat.

---

### D1 — O repositório é a fonte permanente da verdade
**Data:** 2026-09-09
**Decisão:** Todo conhecimento relevante sobre o projeto (estado,
arquitetura, progresso, problemas, comandos, próximos passos) deve estar
documentado dentro do repositório (`docs/`, `CLAUDE.md`, `AGENTS.md`,
código e comentários onde apropriado) — não apenas na conversa com um
assistente de IA.
**Motivo:** o projeto precisa sobreviver à troca de ferramenta, de
assistente e de pessoa.

### D2 — Agentes e modelos de IA são substituíveis
**Data:** 2026-09-09
**Decisão:** O projeto deve poder continuar com Claude Code, Codex,
Gemini, NVIDIA, modelos locais, ou qualquer outro agente, sem depender do
histórico de conversa de nenhum deles especificamente.
**Motivo:** evitar lock-in em uma ferramenta específica e garantir
continuidade do trabalho independentemente de qual assistente está
disponível em um dado momento.

### D3 — Nenhum conhecimento importante pode existir somente no chat
**Decisão:** Se uma decisão, um resultado de teste, um risco encontrado
ou um próximo passo importa para o futuro do projeto, ele precisa ser
escrito em `docs/`, não apenas mencionado em uma resposta de chat.
**Motivo:** consequência direta de D1 — uma decisão que só existe no chat
está, na prática, perdida assim que a sessão termina.

### D4 — Dados restritos da Patrimar não devem ser publicados
**Data:** 2026-09-09
**Decisão:** Dados reais de vendas, preços, clientes ou qualquer
informação comercial restrita da Patrimar não devem ser commitados neste
repositório (que tem remote público em
`https://github.com/gustavoecivil/patrimar-hedonica.git`), nem em texto
plano, nem em exemplos, nem em fixtures de teste.
**Motivo:** o repositório é público (ou tratado como potencialmente
público); dados sintéticos/híbridos (como o CSV atual) são aceitáveis
para testes, dados reais não são.
**Como aplicar:** ao importar dados reais em fases futuras (ver
[[03-ROADMAP]]), avaliar se o repositório precisa se tornar privado ou se
os dados reais devem viver fora do Git (ex.: apenas no banco de
produção), antes de fazer qualquer commit com dados reais.

### D5 — Fase 0 é somente auditoria, sem alteração de comportamento
**Data:** 2026-09-09
**Decisão:** Esta execução (Fase 0) não alterou código de produção,
banco, deploy, nem fez commit/push/branch. Apenas leu o repositório,
executou o teste local seguro existente, e criou documentação nova em
`docs/`, `CLAUDE.md` e `AGENTS.md`.
**Motivo:** instrução explícita do responsável pelo projeto para separar
auditoria de execução.

### D6 — Zona restrita `data/restricted/` para dados privados da Patrimar
**Data:** 2026-09-09
**Decisão:** Toda planilha original de Rodolfo/Patrimar, todo dado real
de vendas/preços/clientes, e todo dado derivado que possa revelar essas
informações privadas devem ficar exclusivamente em `data/restricted/`
na cópia local do repositório. Essa pasta é listada em `.gitignore` e
**nenhum arquivo dentro dela pode ser commitado** neste repositório, que
tem remote público (`github.com/gustavoecivil/patrimar-hedonica`).
Nenhum dado real da Patrimar entra no Git público sem classificação
explícita do dado e autorização explícita do responsável pelo projeto
para aquele commit específico. Dados públicos, sintéticos ou
anonimizados (como `data/hedonic_seed_hybrid.csv`) continuam versionados
normalmente e devem ser claramente identificados como tal (ver
`origem`/proveniência em `MODEL.md` e no dicionário de dados).
**Motivo:** reforço operacional de D4 — o repositório passou a ter
`.gitignore` (Fase 0.5) e precisa de um local convencionado e protegido
para dados restritos antes que qualquer planilha real seja trazida ao
ambiente de trabalho, evitando que caia no Git por descuido.
**Como aplicar:** antes de importar qualquer planilha ou dado real
(ver Fase 1 do [[03-ROADMAP]]), salvar o arquivo dentro de
`data/restricted/` (nunca na raiz de `data/`), e verificar com
`git status`/`git check-ignore` que ele não ficou rastreado antes de
qualquer `git add`.
