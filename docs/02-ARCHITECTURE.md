# 02 — Architecture (estado comprovado atual)

> Este documento descreve **apenas** o que existe hoje no repositório,
> com evidência de arquivo/linha. Arquitetura futura fica em
> [[03-ROADMAP]].

## Visão geral

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  index.html (SPA estática)  │        │  Netlify Function             │
│  - CSS + JS inline           │  GET   │  hedonic-data.mts              │
│  - Chart.js via CDN          │───────▶│  /api/hedonic-data             │
│  - gerador sintético local   │  JSON  │  getDatabase() (@netlify/db)   │
│  - engine OLS local          │◀───────│                                 │
└───────────────┬───────────────┘        └────────────────┬───────────────┘
                │ upload CSV manual                        │ SQL
                ▼                                           ▼
        (nenhum armazenamento                    ┌────────────────────┐
         server-side do upload)                    │ PostgreSQL          │
                                                     │ (Netlify DB nativo) │
                                                     │  v_hedonic_model    │
                                                     └────────────────────┘
```

## Componentes

### 1. Frontend — `index.html`
Aplicação de página única, sem framework, sem build step, servida como
arquivo estático (compatível com Netlify static hosting). Contém:
- Design system em CSS custom properties (`:root`), tema claro/escuro.
- Estado da aplicação em um objeto global `S` (linha 985).
- Contrato de API documentado em comentário (linhas 993–1000): a página
  espera um endpoint HTTPS que devolve um array de linhas ou
  `{ data: [...] }`, usando os nomes de campo do CSV.
- Gerador de dados sintéticos determinístico (`mulberry32` +
  `generateSampleData`, linhas 1042–1124).
- Parser de CSV para upload manual (`parseCSV`, `handleCSV`).
- Motor de regressão OLS em JS puro, com HC3, t/F/Jarque-Bera e VIF
  (linhas ~1350–1532).
- Renderização de tabela, estatísticas, gráficos (Chart.js) e
  calculadora/simulador de preço por unidade.

### 2. API — `netlify/functions/hedonic-data.mts`
Única função serverless do projeto (Netlify Functions v3,
`@netlify/functions`). Rota fixa `GET /api/hedonic-data`. Usa
`getDatabase()` de `@netlify/database` para obter uma conexão já
configurada pelo ambiente Netlify — **não lê `DATABASE_URL`
manualmente** (isso é validado por `tests/model-smoke.mjs`, que falha se
a string `'DATABASE_URL'` aparecer no arquivo). Isso implica que a
gestão da string de conexão é responsabilidade do provisionamento
nativo do Netlify DB, não do código da função.

### 3. Banco de dados — PostgreSQL via Netlify DB
Schema relacional normalizado (4 tabelas + 1 view), definido em dois
lugares com conteúdo semanticamente idêntico:
- `database/schema.sql` — cópia de referência/documentação, envolve as
  instruções em `BEGIN;`/`COMMIT;`.
- `netlify/database/migrations/20260829090000_create_hedonic_schema.sql`
  — a migração de fato aplicada pelo Netlify DB, sem `BEGIN`/`COMMIT`
  explícitos (o runner de migração do Netlify provavelmente já
  transaciona) e com pequenas diferenças de espaçamento nos `JOIN`.

  **Observação de manutenção:** os dois arquivos precisam ser mantidos
  manualmente em sincronia; não há mecanismo automático que os mantenha
  iguais. Isso é um risco de drift, não corrigido nesta auditoria (ver
  [[06-LESSONS-LEARNED]]).

Tabelas: `data_sources` (proveniência/metodologia), `developments`
(empreendimento), `units` (unidade física), `unit_price_observations`
(observação de preço no tempo, com `first_sale` e `record_origin`).
View: `v_hedonic_model`, filtrando `first_sale = TRUE` — o contrato
único que a API consome.

### 4. Geração/seed de dados — `scripts/`
Dois scripts Node (ESM, sem dependências externas — só `node:fs` e
`node:vm`):
- `generate-hybrid-seed.mjs`: executa o gerador sintético embutido no
  HTML dentro de um sandbox `vm`, sem precisar de um navegador, e grava
  `data/hedonic_seed_hybrid.csv`.
- `generate-seed-migration.mjs`: lê esse CSV e escreve a migração SQL de
  seed (`INSERT ... ON CONFLICT DO NOTHING`, idempotente).

Este padrão (executar JS de front-end em `vm` a partir de Node) é usado
tanto pelos scripts de geração quanto pelo teste de fumaça — é a forma
como o projeto reusa a mesma lógica de modelo em CI/local sem duplicar
código entre `index.html` e Node.

### 5. Testes — `tests/model-smoke.mjs`
Mesma técnica de sandbox `vm`. Testa dados + modelo + consistência entre
`index.html`, a função Netlify e as duas migrações, num único processo
Node, sem rede e sem banco real.

## Hospedagem/deploy (comprovado por commits e estrutura, não testado nesta auditoria)

Estrutura compatível com Netlify: `netlify/functions/` para a function e
`netlify/database/migrations/` para o Netlify DB nativo (commit
`d4b3785`, "feat: provisionar PostgreSQL nativo no Netlify"). **Não há
`netlify.toml`** no repositório — a configuração de build/publish está,
portanto, ou nos padrões automáticos do Netlify (detecção de `index.html`
na raiz) ou configurada apenas no painel do Netlify (fora do
repositório). Isso não foi verificado nesta auditoria.

## Dependências (`package.json`)

```json
"dependencies": {
  "@netlify/database": "^2.0.0",
  "@netlify/functions": "^3.1.10"
}
```
Nenhuma dependência de build/bundler/framework frontend. `node_modules`
não estava instalado no momento da auditoria.

## O que este documento explicitamente NÃO afirma

Não afirma que o banco de produção está populado, que o deploy Netlify
está ativo/funcional, nem que a função `/api/hedonic-data` responde em
produção — nada disso foi testado nesta auditoria (Fase 0 é local e não
deve tocar produção). Ver [[01-CURRENT-STATE]] para a lista explícita de
hipóteses não verificadas.
