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

## Estado atual (2026-09-09, Fase 1A.1)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, já enviada ao
  remote e rastreando `origin/rebuild/pricing-intelligence`. A branch
  `main` permanece intocada em `7dd1d24`, tanto local quanto no remote
  — nenhum merge foi feito.
- **Tag do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`. Enviada ao remote (Fase
  0.6), sob autorização explícita restrita a essa branch e essa tag.
- **`.gitignore`** na raiz cobre `node_modules/`, `.env`/`.env.*`
  (exceto `.env.example`), `.netlify/`, `.claude/settings.local.json` e
  `data/restricted/`. `data/` em si continua versionada normalmente
  (contém só a base sintética `hedonic_seed_hybrid.csv`).
- **Zona restrita local `data/restricted/` já existe e está
  populada com a estrutura de subpastas** (Fase 1A):
  - `raw/rodolfo/` — arquivos originais recebidos, nunca editados.
    **Não está mais vazia**: Gustavo já copiou manualmente os arquivos
    fornecidos por Rodolfo/Patrimar para essa pasta (fora desta sessão
    de agente). Nomes de arquivo e conteúdo não são reproduzidos em
    nenhum documento público — ver [[04-DECISIONS]] D4/D6.
  - `audit/` — contém `manifest-recebimento.csv` (privado, ignorado
    pelo Git): inventário técnico dos arquivos recebidos (nome,
    extensão, tamanho em bytes, data de modificação, SHA-256).
    Conteúdo interno das planilhas **não** foi aberto/lido nesta fase.
  - `staging/` — cópias transformadas/normalizadas para análise.
  - `derived/` — dados calculados/derivados ainda privados.
  - `quarantine/` — arquivos suspeitos/corrompidos pendentes de
    triagem.
  - `README-LOCAL.md` (privado, ignorado pelo Git) documenta as regras
    de cada subpasta.
  Toda essa árvore existe **apenas localmente** e está confirmada como
  ignorada pelo Git (validado com `git check-ignore -v` em arquivos de
  teste temporários, removidos após a validação) — ver
  [[04-DECISIONS]] D6.
- **Dois arquivos originais já foram recebidos** em
  `data/restricted/raw/rodolfo/` e catalogados (metadados + SHA-256) em
  `data/restricted/audit/manifest-recebimento.csv`. **O conteúdo
  interno das planilhas ainda não foi aberto/lido.** Nenhuma
  importação para PostgreSQL, conversão de Excel/CSV, ou análise de
  regras de negócio foi feita — isso é a Fase 1B, ainda não iniciada.
- **Nenhum código de produção, schema de banco, ou comportamento de
  `index.html`/função Netlify foi alterado** em nenhuma fase até agora.
- `npm run test:model` — última execução confirmada na Fase 0.5:
  **PASSOU**, mesmo resultado numérico da Fase 0 (ver [[05-WORKLOG]]).
  Nenhuma fase posterior alterou modelo/gerador, então o resultado
  permanece válido.

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence
   baseline` (`docs/`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`).
2. `e689be9` — `docs: record remote baseline backup` (apenas
   `docs/05-WORKLOG.md` e `docs/99-HANDOFF.md`).
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase
   1A, apenas `docs/05-WORKLOG.md` e `docs/99-HANDOFF.md`, sanitizado).
4. (Fase 1A.1) commit de documentação — `docs: record restricted data
   receipt` (apenas `docs/05-WORKLOG.md` e `docs/99-HANDOFF.md`,
   sanitizado — sem nomes de arquivo, de empreendimento, ou qualquer
   conteúdo de planilha).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit.

## Arquivos criados até agora neste histórico (Fase 0 a 1A.1)

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
.gitignore                              (Fase 0.5)
data/restricted/                        (Fase 1A — local, NÃO versionado)
  raw/rodolfo/, audit/, staging/, derived/, quarantine/
  README-LOCAL.md                       (local, NÃO versionado)
  raw/rodolfo/ — 2 arquivos originais recebidos (Fase 1A.1, local, NÃO versionado)
  audit/manifest-recebimento.csv        (Fase 1A.1, local, NÃO versionado)
```

Nenhum arquivo pré-existente do laboratório (`index.html`, `MODEL.md`,
`database/schema.sql`, `netlify/`, `scripts/`, `tests/`,
`data/hedonic_seed_hybrid.csv`) foi modificado ou apagado em nenhuma
fase até agora.

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Os dois arquivos precisam ser editados juntos até que
   um deles seja eliminado em favor do outro como única fonte de
   verdade — decisão ainda não tomada.
2. **Não verificado em nenhuma auditoria até agora:** se o Netlify DB
   de produção está provisionado e populado, se o deploy Netlify está
   ativo, e se `GET /api/hedonic-data` responde em produção. Não há
   `netlify.toml` no repositório.
3. **Dados reais da Patrimar não devem ser commitados** neste
   repositório enquanto ele permanecer com o remote atual (público) —
   ver [[04-DECISIONS]] D4 e D6. Qualquer planilha real deve ir para
   `data/restricted/raw/rodolfo/`, nunca para a raiz de `data/` nem
   para qualquer caminho versionado.
4. **A tag e a branch já estão no remote** (`origin`) desde a Fase 0.6
   — o ponto de recuperação do legado sobrevive à perda do clone local.
   Qualquer novo commit local em `rebuild/pricing-intelligence` ainda
   precisa de push explícito para chegar ao remote.
5. **`main` e `rebuild/pricing-intelligence` divergirão** a partir de
   agora — `main` continua sendo o histórico do laboratório legado tal
   como estava em `7dd1d24`; toda a evolução da nova plataforma deve
   acontecer em `rebuild/pricing-intelligence` (ou branches derivadas
   dela) até uma decisão explícita de merge/substituição.
6. **`data/restricted/` existe apenas localmente.** Se o ambiente local
   for perdido/trocado, a árvore e qualquer arquivo já recebido nela
   precisam ser recriados/re-recebidos — nada disso está no Git por
   desenho (ver [[04-DECISIONS]] D6).
7. **`raw/rodolfo/` já contém arquivos recebidos** (2, catalogados em
   `data/restricted/audit/manifest-recebimento.csv`), mas seu conteúdo
   interno ainda não foi aberto/lido/validado. O próximo agente deve
   tratar esse conteúdo como não auditado até a Fase 1B ser concluída
   — não presumir estrutura, colunas ou qualidade dos dados.

## Comandos úteis já validados

```bash
npm run test:model            # único teste, roda local, sem rede, sem banco — PASSOU em 2026-09-09 (Fase 0 e Fase 0.5)
npm run generate:seed          # NÃO executado — sobrescreveria data/hedonic_seed_hybrid.csv
npm run generate:seed-migration # NÃO executado — sobrescreveria a migração de seed
git tag --list "legacy-hedonica*"                          # confirma a tag do legado
git log -3 --oneline                                        # confirma os commits acima de 7dd1d24
git ls-remote --heads origin rebuild/pricing-intelligence   # confirma a branch remota
git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909  # confirma a tag remota
git check-ignore -v data/restricted/<arquivo>               # confirma que um arquivo dentro da zona restrita está ignorado
```

## Próximo passo recomendado

O inventário técnico básico (nome, extensão, tamanho, data de
modificação, SHA-256) já está feito em
`data/restricted/audit/manifest-recebimento.csv` (Fase 1A.1). O
próximo passo é a **Fase 1B — auditoria estrutural**: abrir os
arquivos apenas para inspecionar estrutura (abas, cabeçalhos, tipos de
dados aproximados) sem ainda extrair, transformar ou importar dados
de negócio, registrando os achados privadamente em
`data/restricted/audit/` — nunca em documentação pública. Qualquer
conversão de Excel para CSV, importação para PostgreSQL, ou análise de
regras de negócio continua fora de escopo até essa auditoria estrutural
ser concluída e revisada.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/reescrito,
pois reflete sempre o estado *atual*, não o histórico). Nunca escrever
nomes de arquivo, nomes de empreendimento, ou qualquer conteúdo das
planilhas privadas em nenhum documento dentro de `docs/` — apenas
descrições sanitizadas do que foi feito.
