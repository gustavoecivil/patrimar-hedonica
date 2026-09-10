# 99 — Handoff

Este documento deve permitir que qualquer agente (ou pessoa) assuma o
projeto **sem ter acesso à conversa em que este trabalho foi feito**.
Leia isto, depois leia os documentos referenciados, na ordem sugerida.

## Ordem de leitura recomendada

1. [[00-PROJECT-CHARTER]] — por que este projeto existe, e o que o
   produto é hoje.
2. [[01-CURRENT-STATE]] — o que de fato existia antes da Fase 3E
   (ainda válido para o laboratório legado, agora em `legacy/lab/`).
3. [[02-ARCHITECTURE]] — como as peças se conectam (laboratório
   legado — ver [[18-PRICING-INTELLIGENCE-MVP]] para a arquitetura do
   produto novo).
4. [[03-ROADMAP]] — o que vem depois (ainda não implementado).
5. [[04-DECISIONS]] — regras que não devem ser quebradas sem registro
   (D7 dois motores; D8 referência sintética não é metodologia
   oficial; D9–D11 isolamento de bancos e distinção importado/
   calculado; D12 lógica real é configuração privada; D13 evidência
   classificada + prova estrutural; D14 produto público é sempre
   DEMO, dado real só em PRIVATE local; D15 laboratório legado
   preservado, não apagado; **D16 ciclo atual encerrado como Prova de
   Conceito — feature freeze até revisão explícita de Gustavo
   Santos**).
6. [[08-SPREADSHEET-AUDIT-METHOD]] … [[17-AMBIGUITY-RESOLUTION-METHOD]]
   — metodologia/modelo das fases 1–3D, sem conteúdo privado.
7. [[18-PRICING-INTELLIGENCE-MVP]] — o produto oficial (Fase 3E): o
   que ele é, as 6 páginas, os dois modos de dado.
8. [[19-DEPLOYMENT-AND-DEMO-MODE]] — como rodar PRIVATE local, como o
   deploy DEMO funciona, o scanner de privacidade.
9. [[20-POC-CLOSURE]] — encerramento formal como prova de conceito
   (Fase 3F): feature freeze, status do Motor B, pacote de entrega.
10. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-10, Fase 3F)

- **Status oficial do produto:** Prova de Conceito Funcional.
  `FEATURE_FREEZE=SIM` — ver [[04-DECISIONS]] D16. Nenhuma
  funcionalidade nova deve ser adicionada sem decisão explícita
  futura de Gustavo Santos que levante o freeze.
- **Interface identifica a POC de forma permanente:** selo "Prova de
  Conceito" na barra lateral (tooltip com o aviso completo), nota de
  rodapé sensível ao modo de dado ("POC • Dados privados locais" /
  "POC • Dados sintéticos").
- **Linguagem de precisão de reprodução corrigida** — nunca mais
  implica igualdade decimal absoluta sem qualificação; "884 de 884
  dentro de R$ 0,01" é o padrão adotado em toda a interface.
- **Defeito real corrigido** (não presente na Fase 3E, só visível ao
  testar o modo PRIVATE contra o banco real): 100% das 884 unidades
  reais têm `floor = NULL` — isso quebrava o gráfico "Preço/m² por
  pavimento" e disparava um `alert()` que travava a aba inteira
  (inclusive para automação de navegador). Corrigido em
  `web/pricing-intelligence/app.js` (agrupamento ignora unidades sem
  pavimento; erro de carregamento não usa mais `alert()`) e em
  `scripts/pricing_preview_server.py` (campos genuinamente ausentes
  — `weighted_area_m2`, `participation_share` — não são mais
  mascarados como `0` via `COALESCE`; chegam como `null` até a
  interface, que agora exibe "—" em vez de um zero enganoso).
- **Motor B formalizado:** `MATHEMATICAL_REPRODUCTION=VALIDATED`,
  `UNITS=884`, `CENT_PRECISION_COVERAGE=884/884`,
  `DATABASE_MODEL=VALIDATED`, `LINEAGE=VALIDATED`,
  `PRIVATE_RUNTIME=VALIDATED`, `DEMO_RUNTIME=VALIDATED`,
  `BUSINESS_SEMANTICS=PARTIAL` (não bloqueador).
- **Pacote de entrega privado** criado em
  `data/restricted/deliverables/` (relatório executivo, resumo de 1
  página, roteiro de demonstração, FAQ do apresentador, checklist de
  apresentação) — confirmado fora do controle de versão
  (`git check-ignore` positivo para todos os arquivos). Sem proposta
  comercial.
- **Recovery tag desta fase:** `poc-delivery-candidate-20260910` →
  `02b54114ee65166b1e2b5f37da132506044d1c3a`, criada e enviada a
  `origin`. Tags anteriores (`legacy-hedonica-pre-rebuild-20260909`,
  `pre-pricing-intelligence-mvp-20260910`) continuam intactas.
- **`main` e `rebuild/pricing-intelligence` sincronizadas** em
  `02b5411` (fast-forward, sem divergência).
- **Deploy Netlify confirmado** servindo o commit `02b5411`
  (`https://imaginative-fudge-64c0aa.netlify.app`) — HTTP 200,
  título/selo/textos novos visíveis, console sem erros de aplicação.
- Suíte de testes completa (ver seção "Comandos" abaixo) e o scanner
  de privacidade re-executados após todas as correções: **todos
  passando / `OK`**. Verificação adicional (grep manual em todo o
  repositório versionado) não encontrou nenhuma credencial, connection
  string ou hash de XLSX real — apenas nomes de variável de ambiente
  genéricos e o hash determinístico do cenário sintético público
  (D8).

## Commits desta branch acima de `7dd1d24`

1. `5ab265b` — `chore: establish Patrimar Pricing Intelligence baseline`.
2. `e689be9` — `docs: record remote baseline backup`.
3. `f6fc53e` — `docs: prepare restricted Patrimar data intake` (Fase 1A).
4. `f21df3d` — `docs: record restricted data receipt` (Fase 1A.1).
5. `8472085` — `feat: add workbook structural audit tooling` (Fase 1B).
6. `99a225a` — `feat: add pricing logic reverse engineering` (Fase 1C).
7. `f5a2cb2` — `docs: define Patrimar pricing domain model` (Fase 1D).
8. `e59157e` — `feat: design canonical PostgreSQL v2 schema` (Fase 2).
9. `866e876` — `feat: prove unit allocation engine with synthetic scenario` (Fase 2B).
10. `c72fe0c` — `test: validate pricing v2 on real PostgreSQL` (Fase 2C).
11. `55139eb` — `feat: add controlled private data ingestion pipeline` (Fase 3A).
12. `72d798c` — `feat: promote private staging into canonical pricing model` (Fase 3B).
13. `9c06f38` — `feat: add independent pricing reproduction engine` (Fase 3C).
14. (Fase 3D) commit — `feat: add forensic ambiguity resolution workflow`.
15. `6915820` — `feat: launch Patrimar Pricing Intelligence MVP` (Fase 3E).
16. `02b5411` — `chore: finalize Patrimar Pricing Intelligence proof of concept`
    (Fase 3F — selo de POC na interface, linguagem de precisão
    corrigida, correção do defeito real de `floor = NULL`/`alert()`,
    status formal do Motor B, `docs/20-POC-CLOSURE.md` — tudo
    público/genérico, nenhum dado real, nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. Nenhum
`.env.*` ou `.dump` nunca foi (e não pode ser) adicionado a nenhum
commit.

## Arquivos criados/alterados nesta fase (Fase 3F)

```
docs/20-POC-CLOSURE.md                                    (novo)
docs/03-ROADMAP.md, 04-DECISIONS.md, 05-WORKLOG.md,
  99-HANDOFF.md                                            (atualizados)
web/pricing-intelligence/index.html                        (selo POC, nota de modo, intro Visão Geral, textos revisados)
web/pricing-intelligence/styles.css                         (estilos do selo POC, intro Visão Geral)
web/pricing-intelligence/app.js                             (correção floor=NULL, remoção de alert(), campos "-" em vez de zero enganoso)
web/pricing-intelligence/demo-data.json                     (regenerado — nota de validação sem referência a docs internos)
scripts/generate_pricing_intelligence_demo_data.py          (nota de validação simplificada)
scripts/pricing_preview_server.py                           (weighted_area_m2/participation_share não mais mascarados com COALESCE)

data/restricted/deliverables/                                (NOVO, LOCAL, NUNCA versionado)
  RELATORIO-EXECUTIVO-PATRIMAR-PRICING-INTELLIGENCE-POC.md
  RESUMO-EXECUTIVO-1-PAGINA.md
  ROTEIRO-DEMONSTRACAO.md
  FAQ-APRESENTADOR.md
  CHECKLIST-APRESENTACAO.md
```

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **`FEATURE_FREEZE=SIM` está em vigor (D16).** Não adicionar login,
   permissões, workflow corporativo, edição produtiva, integrações
   ERP/CRM, Motor A operacional, novos modelos de ML ou agentes sem
   confirmação explícita de Gustavo Santos de que o freeze foi
   levantado.
2. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Ainda não resolvido (herdado das fases anteriores).
3. **Dados reais da Patrimar não devem ser commitados** — ver
   [[04-DECISIONS]] D4/D6. `scripts/scan_deploy_privacy.py` é uma
   camada de defesa adicional, não a única — sempre revisar
   manualmente também.
4. **`REFERENCE_ALLOCATION_V1` nunca deve ser confundido com a
   metodologia real** — ver [[04-DECISIONS]] D8.
5. **Os 884 resultados reproduzidos ainda não são "preço oficial de
   produção"** — o modo PRIVATE os exibe (read-only, local,
   rastreável), mas isso não é promoção a recomendação de preço.
6. **`BUSINESS_SEMANTICS_CONFIRMED` permanece parcial** — 2 perguntas
   de negócio pendentes em
   `data/restricted/audit/questions-for-rodolfo-final.md` (local, não
   versionado, não enviado a ninguém ainda). Não bloqueador para o
   status atual da POC.
7. **100% das 884 unidades reais têm `floor` não identificado** — a
   interface já trata isso corretamente (estado vazio explicativo,
   nunca "null" cru), mas qualquer nova funcionalidade que dependa de
   pavimento real precisará resolver essa lacuna de dado primeiro.
8. **Dois bancos PostgreSQL locais no mesmo servidor pré-existente**
   (`patrimar_pricing_v2_test` e `patrimar_pricing_v2_private_dev`) —
   nunca misturar dado real no banco `_test`, nem dado sintético de
   demonstração no banco `_private_dev` (ver D10).
9. **`psql`/`PSQL_BIN`:** o PostgreSQL local está instalado fora do
   local padrão (`winget`/`Program Files`) neste ambiente
   (`D:\GSA\PostgreSQL\18\bin\psql.exe`) — usar `PSQL_BIN=<caminho
   completo>` quando `psql` não estiver no `PATH`.
10. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte
    de dado real** — a página "Inteligência de Mercado" do produto é
    só arquitetura conceitual.
11. **Responsividade verificada por leitura do CSS, não por captura
    visual em viewport estreito** — a ferramenta de redimensionar
    janela do navegador automatizado não surtiu efeito neste
    ambiente em nenhuma das duas fases em que foi tentada (3E e 3F).
    Uma verificação visual real em dispositivo/emulador móvel ainda é
    recomendada antes de qualquer apresentação comercial.
12. **O pacote de entrega em `data/restricted/deliverables/` é
    material potencial de entrega** — não deve ser enviado a ninguém
    sem revisão e aprovação prévia de Gustavo Santos (ver
    [[20-POC-CLOSURE]]). Nenhum desses arquivos deve ser commitado.

## Comandos úteis já validados

```bash
# suíte completa (todos passando na Fase 3F):
npm run test:model
python scripts/test_reference_allocation_engine.py
python scripts/test_validate_db_v2.py
python scripts/test_pricing_reproduction_engine.py
python scripts/test_analyze_pricing_logic.py
python scripts/test_audit_xlsx.py
python scripts/validate_db_v2.py --sql-dir database/v2 \
  --file 001_schemas.sql --file 002_core.sql --file 003_pricing.sql \
  --file 004_audit.sql --file 005_market_foundation.sql \
  --file 006_indexes.sql --file 007_views.sql --file 008_ingestion.sql \
  --file 009_promotion.sql --file 010_reproduction.sql \
  --seed-file database/v2/seeds/001_demo_allocation.sql

# contra o banco de teste SINTÉTICO (requer .env.pricing_v2_test local e PSQL_BIN se psql não estiver no PATH):
powershell -File scripts/db_v2_verify.ps1
python scripts/test_ingest_xlsx_postgres.py --env-file .env.pricing_v2_test
python scripts/test_promote_staging_to_core.py --env-file .env.pricing_v2_test

# produto — modo DEMO local:
python scripts/generate_pricing_intelligence_demo_data.py
cd web/pricing-intelligence && python -m http.server 8899 --bind 127.0.0.1

# produto — modo PRIVATE local (dado real, banco privado, somente leitura):
python scripts/pricing_preview_server.py --env-file .env.pricing_v2_private_dev
# (defina PSQL_BIN=<caminho completo do psql.exe> se psql não estiver no PATH)

# scanner de privacidade — rodar antes de qualquer push para main/deploy:
python scripts/scan_deploy_privacy.py --dir web/pricing-intelligence
```

## Próximo passo recomendado

`PROXIMO_PASSO=ESTUDO_DO_MANUAL_E_REVIEW_COM_GUSTAVO` — nenhum
desenvolvimento novo deve começar antes dessa revisão. Depois dela,
possíveis linhas de trabalho (nenhuma iniciada, nenhuma orçada):

1. Validar as 2 perguntas de negócio pendentes com quem mantém a
   planilha hoje.
2. Decisão de negócio sobre iniciar o desenho do Motor A.
3. Decisão de negócio sobre levantar o feature freeze (D16) para uma
   eventual evolução a sistema corporativo.

## Regra para quem continuar este trabalho

Ao final de qualquer sessão de trabalho relevante neste projeto,
atualizar [[05-WORKLOG]] (nova entrada, não substituir entradas
anteriores) e este arquivo `99-HANDOFF.md` (pode ser substituído/
reescrito, pois reflete sempre o estado *atual*, não o histórico).
Nunca escrever nomes de arquivo, nomes de empreendimento, nomes reais
de aba/campo, fórmulas específicas, valores, senhas, connection
strings, ou qualquer conteúdo das planilhas privadas em nenhum
documento dentro de `docs/`, `fixtures/` ou qualquer arquivo `.sql`/
`.ps1`/`.py` — apenas descrições sanitizadas e números agregados.
**A partir da Fase 3F, respeitar o feature freeze (D16) até
confirmação explícita de Gustavo Santos.**
