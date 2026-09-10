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
   classificada + prova estrutural; **D14 produto público é sempre
   DEMO, dado real só em PRIVATE local; D15 laboratório legado
   preservado, não apagado**).
6. [[08-SPREADSHEET-AUDIT-METHOD]] … [[17-AMBIGUITY-RESOLUTION-METHOD]]
   — metodologia/modelo das fases 1–3D, sem conteúdo privado.
7. [[18-PRICING-INTELLIGENCE-MVP]] — o produto oficial (Fase 3E): o
   que ele é, as 6 páginas, os dois modos de dado.
8. [[19-DEPLOYMENT-AND-DEMO-MODE]] — como rodar PRIVATE local, como o
   deploy DEMO funciona, o scanner de privacidade.
9. Este documento (99-HANDOFF) — estado exato da última execução.

## Estado atual (2026-09-10, Fase 3E)

- **Produto oficial:** Patrimar Pricing Intelligence
  (`web/pricing-intelligence/`) substituiu o laboratório hedônico
  legado como interface principal do repositório e do deploy
  público. O laboratório continua existindo, preservado, em
  `legacy/lab/` (D15) — não é mais a página inicial.
- **Dois modos de dado, nunca misturados (D14):** PRIVATE (dado real,
  só `localhost`/`127.0.0.1`, via `scripts/pricing_preview_server.py`)
  e DEMO (100% sintético, único modo do GitHub `main`/Netlify, via
  `web/pricing-intelligence/demo-data.json`).
- **PRIVATE testado end-to-end contra o banco real:** 884 unidades,
  VGV real, 100% de precisão de reprodução (884/884 dentro de 1
  centavo) — mesmo resultado já confirmado na Fase 3D, agora também
  visível na interface do produto (não só em script/CSV de auditoria).
- **`netlify.toml` (novo, raiz do repo)** aponta a publicação do site
  Netlify já existente (`imaginative-fudge-64c0aa`) para
  `web/pricing-intelligence` — nenhum site novo foi criado, nenhuma
  configuração do site foi alterada via API, só o diretório de
  publicação via arquivo versionado.
- **`scripts/scan_deploy_privacy.py` (novo)** bloqueia deploy se
  encontrar qualquer indício estrutural de dado privado no diretório
  publicado — rodado com sucesso (`OK`) antes da promoção a `main`.
- **Recovery tag desta fase:** `pre-pricing-intelligence-mvp-20260910`
  → `7dafca5bf8d80bbd7a244c072be22afb5f50283c` (HEAD da Fase 3D),
  criada e enviada a `origin` **antes** de qualquer substituição de
  arquivo. A tag da Fase 0.5 (`legacy-hedonica-pre-rebuild-20260909`)
  continua intacta.
- Toda a suíte de testes conhecida (ver seção "Comandos" abaixo)
  re-executada nesta fase: **todos passando**, incluindo os testes
  contra PostgreSQL real (banco de teste `patrimar_pricing_v2_test`).

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
15. (Fase 3E) commit — `feat: launch Patrimar Pricing Intelligence MVP`
    (novo frontend `web/pricing-intelligence/`, laboratório legado
    movido para `legacy/lab/`, `netlify.toml`, servidor PRIVATE,
    gerador de dataset DEMO, scanner de privacidade, docs 18/19 +
    atualizações — tudo público/genérico, nenhum dado real,
    nenhuma credencial).

Nenhum desses commits contém dado privado ou segredo. `data/restricted/`
nunca foi (e não pode ser) adicionada a nenhum commit. Nenhum
`.env.*` ou `.dump` nunca foi (e não pode ser) adicionado a nenhum
commit.

## Arquivos criados/alterados nesta fase (Fase 3E)

```
web/pricing-intelligence/index.html                    (novo)
web/pricing-intelligence/styles.css                     (novo)
web/pricing-intelligence/app.js                         (novo)
web/pricing-intelligence/data-provider.js                (novo)
web/pricing-intelligence/demo-data.json                  (novo, gerado, 100% sintético)
web/pricing-intelligence/assets/logo-grupo-patrimar-branca.png (novo, extraído do HTML legado)
scripts/generate_pricing_intelligence_demo_data.py       (novo)
scripts/pricing_preview_server.py                        (novo)
scripts/scan_deploy_privacy.py                           (novo)
netlify.toml                                             (novo)
legacy/lab/index.html                                    (movido de index.html, git mv)
legacy/lab/MODEL.md                                      (movido de MODEL.md, git mv)
tests/model-smoke.mjs                                    (caminho atualizado, lógica igual)
docs/18-PRICING-INTELLIGENCE-MVP.md                       (novo)
docs/19-DEPLOYMENT-AND-DEMO-MODE.md                       (novo)
docs/00-PROJECT-CHARTER.md, 03-ROADMAP.md, 04-DECISIONS.md,
  05-WORKLOG.md, 07-DATA-DICTIONARY.md, 99-HANDOFF.md      (atualizados)
```

`netlify/functions/hedonic-data.mts` **não foi alterado** — continua
existindo, backend do laboratório legado, não usado pelo produto novo.
`database/v2/*.sql` **não foi alterado** — nenhuma migração nova foi
necessária nesta fase (só leitura do schema existente, pelo servidor
PRIVATE).

## Riscos conhecidos que o próximo agente deve considerar antes de agir

1. **Drift entre `database/schema.sql` e a migração Netlify
   equivalente.** Ainda não resolvido (herdado das fases anteriores).
2. **Dados reais da Patrimar não devem ser commitados** — ver
   [[04-DECISIONS]] D4/D6. Qualquer dado real deve ir para
   `data/restricted/` ou para o banco privado `_private_dev`, nunca
   para caminho versionado. `scripts/scan_deploy_privacy.py` é uma
   camada de defesa adicional, não a única — sempre revisar
   manualmente também.
3. **`REFERENCE_ALLOCATION_V1` nunca deve ser confundido com a
   metodologia real** — ver [[04-DECISIONS]] D8. É a base do dataset
   DEMO — mantê-lo assim, nunca aproximar seus números dos reais.
4. **Os 884 resultados reproduzidos ainda não são "preço oficial de
   produção"** — o modo PRIVATE do produto novo os EXIBE (é read-only,
   é local, é rastreável), mas isso não é o mesmo que promovê-los a
   recomendação de preço. Nenhum código deve tratar esse run como
   decisão de precificação sem uma decisão explícita futura.
5. **`BUSINESS_SEMANTICS_CONFIRMED` permanece parcial** (herdado da
   Fase 3D) — 2 perguntas de negócio pendentes em
   `data/restricted/audit/questions-for-rodolfo-final.md` (local, não
   versionado, não enviado a ninguém ainda).
6. **`floor_factor`/`position_factor` por unidade não são recalculados
   pelo servidor PRIVATE nesta primeira versão** (aparecem vazios na
   tabela/painel de detalhe) — o preço final e a comparação com a
   referência são reais; só esses dois fatores intermediários ficam
   pendentes de uma consulta adicional a `pricing.unit_adjustments`
   numa fase futura, se necessário.
7. **Dois bancos PostgreSQL locais no mesmo servidor pré-existente**
   (`patrimar_pricing_v2_test` e `patrimar_pricing_v2_private_dev`) —
   nunca misturar dado real no banco `_test`, nem dado sintético de
   demonstração no banco `_private_dev` (ver D10).
8. **`psql`/`PSQL_BIN`:** o PostgreSQL local está instalado fora do
   local padrão (`winget`/`Program Files`) neste ambiente — não
   assumir que `psql` está no `PATH`; usar `PSQL_BIN=<caminho
   completo>` quando necessário (ver [[19-DEPLOYMENT-AND-DEMO-MODE]]).
9. **O Motor A (Market Pricing Engine) ainda não tem nenhuma fonte de
   dado real** — a página "Inteligência de Mercado" do produto é só
   arquitetura conceitual, rotulada "PRÓXIMA EVOLUÇÃO".
10. **Responsividade do produto novo foi verificada por leitura do
    CSS, não por captura visual em viewport estreito** — a ferramenta
    de redimensionar janela do navegador automatizado não surtiu
    efeito neste ambiente (viewport permaneceu no tamanho original
    apesar de reportar sucesso). Uma verificação visual real em
    dispositivo/emulador móvel ainda é recomendada antes de qualquer
    apresentação comercial que dependa de mobile.
11. **Se uma fase futura promover os resultados reproduzidos a
    produção**, revisar antes: (a) as 2 perguntas pendentes de
    `questions-for-rodolfo-final.md`; (b) o resíduo de meio centavo
    por unidade (precisão de dízima periódica), hoje apenas
    documentado, nunca corrigido.

## Comandos úteis já validados

```bash
# suíte completa (todos passando na Fase 3E):
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

# produto novo — modo DEMO local:
python scripts/generate_pricing_intelligence_demo_data.py
cd web/pricing-intelligence && python -m http.server 8899 --bind 127.0.0.1

# produto novo — modo PRIVATE local (dado real, banco privado):
python scripts/pricing_preview_server.py --env-file .env.pricing_v2_private_dev
# (defina PSQL_BIN=<caminho completo do psql.exe> se psql não estiver no PATH)

# scanner de privacidade — rodar antes de qualquer push para main/deploy:
python scripts/scan_deploy_privacy.py --dir web/pricing-intelligence

# reprodução real (NUNCA rodar contra o banco "_test" — só contra o banco privado dedicado):
python scripts/run_pricing_reproduction.py --mode summary
```

## Próximo passo recomendado

1. **Validação com Rodolfo** — levar as 2 perguntas de
   `data/restricted/audit/questions-for-rodolfo-final.md` para fechar
   `BUSINESS_SEMANTICS_CONFIRMED`. Recomendado antes de qualquer
   promoção dos resultados reproduzidos a preço oficial.
2. **Revisão visual + preparação de apresentação comercial** — o
   produto está publicado em modo DEMO; revisar em dispositivo móvel
   real (risco 10 acima) e preparar o roteiro de apresentação.
3. **Fase 4 — Market Pricing Engine** — com o Motor B (alocação) já
   reproduzido e agora visível no produto, o próximo domínio em
   aberto é o Motor A (estimativa de valor de mercado), que ainda não
   tem nenhuma fonte de dado real (ver [[10-PRICING-DOMAIN-MODEL]] e
   [[04-DECISIONS]] D7).

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
