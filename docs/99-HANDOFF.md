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
9. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-09, Fase 1D)

- **Branch de trabalho:** `rebuild/pricing-intelligence`, rastreando
  `origin/rebuild/pricing-intelligence`. `main` intocada em `7dd1d24`.
- **Tag do legado:** `legacy-hedonica-pre-rebuild-20260909` →
  `7dd1d24bb9fbea21e915fc9d9365a1dbec547bf0`, no remote desde a Fase 0.6.
- **Decisão arquitetural nova:** Market Pricing Engine (Motor A) e
  Unit Price Allocation Engine (Motor B) são domínios separados e
  integráveis pelo VGV/preço-base recomendado — ver [[04-DECISIONS]]
  D7 e [[10-PRICING-DOMAIN-MODEL]]. O Motor B tem metodologia
  reconstruída com evidência (Fase 1C); o Motor A ainda não existe
  como mecanismo formal (o laboratório hedônico sintético é um
  protótipo na direção do Motor A, sem dado real).
- **Zona restrita local `data/restricted/`** (só localmente, nunca no
  Git — [[04-DECISIONS]] D6):
  - `raw/rodolfo/` — 2 arquivos originais, intactos, hash não
    revalidado nesta fase (não foram lidos/tocados — Fase 1D é
    modelagem sobre o conhecimento já extraído, não nova extração).
  - `audit/` — além de tudo produzido nas Fases 1A.1/1B/1C, contém
    agora `pricing-gap-analysis.csv`, `pricing-variable-matrix.csv`,
    `data-acquisition-backlog.csv`, `preliminary-canonical-model.md`
    (com diagramas Mermaid), `gap-analysis-summary.md`.
    `questions-for-rodolfo.md` foi atualizado (seção de classificação
    de bloqueio), sem perguntas novas.
  - `staging/`, `derived/`, `quarantine/` — vazias.
- **Nenhum schema físico, migration, ou alteração de banco/frontend/
  Netlify/modelo OLS foi feita** em nenhuma fase até agora.
- `npm run test:model` re-executado nesta fase: **PASSOU**, mesmo
  resultado numérico das fases anteriores.
- `python -m py_compile` em `scripts/audit_xlsx.py` e
  `scripts/analyze_pricing_logic.py`: **OK**. Nenhum script novo
  criado nesta fase (trabalho de modelagem, não de extração).

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence baseline`.
2. `e689be9` — `docs: record remote baseline backup`.
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase 1A).
4. `f21df3d` — `docs: record restricted data receipt` (Fase 1A.1).
5. `8472085` — `feat: add workbook structural audit tooling` (Fase 1B).
6. `99a225a` — `feat: add pricing logic reverse engineering` (Fase 1C).
7. (Fase 1D) commit — `docs: define Patrimar pricing domain model`
   (`docs/10-PRICING-DOMAIN-MODEL.md`, `docs/00-PROJECT-CHARTER.md`,
   `docs/03-ROADMAP.md`, `docs/04-DECISIONS.md`, `docs/05-WORKLOG.md`,
   `docs/07-DATA-DICTIONARY.md`, `docs/99-HANDOFF.md` — todos sem dado
   privado).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit.

## Arquivos criados até agora neste histórico (Fase 0 a 1D)

```
docs/00 .. docs/07 (Fase 0, atualizados em fases posteriores)
docs/08-SPREADSHEET-AUDIT-METHOD.md                    (Fase 1B)
docs/09-PRICING-LOGIC-REVERSE-ENGINEERING.md           (Fase 1C)
docs/10-PRICING-DOMAIN-MODEL.md                        (Fase 1D)
docs/99-HANDOFF.md (este arquivo)
CLAUDE.md, AGENTS.md, .gitignore
scripts/audit_xlsx.py + test_audit_xlsx.py             (Fase 1B)
scripts/analyze_pricing_logic.py + test_analyze_pricing_logic.py  (Fase 1C)
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
  staging/, derived/, quarantine/  (vazias)
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
   evolução da nova plataforma acontece nesta branch até decisão
   explícita de merge/substituição.
6. **`data/restricted/` existe apenas localmente.** Perda do ambiente
   local exige recriar/reprocessar tudo — nada disso está no Git por
   desenho.
7. **Fórmulas compartilhadas do XLSX têm limitação de leitura
   conhecida** — ver [[09-PRICING-LOGIC-REVERSE-ENGINEERING]]. Toda
   regra do catálogo da Fase 1C foi confirmada contra o XML bruto,
   mas expansões futuras da análise devem reconfirmar célula a célula.
8. **A Fase 1D é modelagem conceitual, não schema físico.** Nenhuma
   tabela, migration, ORM ou API foi criada. O próximo agente não deve
   presumir que existe um schema pronto para uso — existe um modelo
   conceitual (entidades, relações, granularidade, princípios de
   histórico/versionamento) que ainda precisa ser traduzido em SQL na
   Fase 2.
9. **Perguntas bloqueantes pendentes para quem forneceu a planilha.**
   Ver `data/restricted/audit/questions-for-rodolfo.md`, seção
   "Classificação de bloqueio (Fase 1D)": 2 perguntas bloqueiam
   decisão de schema, 5 bloqueiam definição de regra de negócio, 1
   bloqueia decisão sobre o Motor A. O próximo agente não deve tomar
   essas decisões por conta própria sem ao menos registrar que essas
   perguntas ainda estão abertas.
10. **O Motor A (Market Pricing Engine) não tem nenhuma fonte de dado
    hoje** — nem nas planilhas, nem no schema legado (que é
    inteiramente sintético). Qualquer trabalho na Fase 2 que tente
    implementar o Motor A antes de resolver isso vai ficar sem dado
    real para operar sobre.
11. **A anomalia de fórmula da Fase 1C não foi corrigida** (nem
    deveria ser, nesta fase) — ela continua preservada como evidência
    privada. O modelo conceitual da Fase 1D já prevê que o sistema
    futuro precisa de validação/versionamento/testes/rastreabilidade
    para lidar com esse tipo de caso, mas isso ainda não foi
    implementado.

## Comandos úteis já validados

```bash
npm run test:model            # único teste JS — PASSOU em todas as fases até agora
git tag --list "legacy-hedonica*"
git log --oneline -8
git ls-remote --heads origin rebuild/pricing-intelligence
git ls-remote --tags origin legacy-hedonica-pre-rebuild-20260909
git check-ignore -v data/restricted/<arquivo>
python scripts/audit_xlsx.py --help
python scripts/analyze_pricing_logic.py --help
python scripts/test_audit_xlsx.py
python scripts/test_analyze_pricing_logic.py
```

## Próximo passo recomendado

**Fase 2 — Desenho do schema PostgreSQL canônico.** Traduzir o
modelo conceitual da Fase 1D (`data/restricted/audit/
preliminary-canonical-model.md`) em schema físico — priorizando o
Motor B (Unit Price Allocation Engine), que já tem evidência completa,
e deixando o Motor A (Market Pricing Engine) como extensão planejada
mas não bloqueante, já que não há fonte de dado real disponível para
ele ainda. Antes de desenhar `PricingScenario`/`PricingRun`, considerar
levar as perguntas bloqueantes de schema (Q-05, Q-12) e de regra de
negócio (Q-02, Q-03, Q-04, Q-08, Q-11) ao responsável do projeto — ver
`questions-for-rodolfo.md`.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, fórmulas específicas, valores, ou qualquer conteúdo das
planilhas privadas em nenhum documento dentro de `docs/` — apenas
descrições sanitizadas e números agregados.
