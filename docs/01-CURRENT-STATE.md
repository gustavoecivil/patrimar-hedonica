# 01 — Current State

Auditoria realizada em **2026-09-09**, branch `main`, commit `7dd1d24`
("fix: nomear série do gráfico de ajuste"), working tree limpo antes e
depois desta auditoria. Todo item abaixo é **FATO COMPROVADO NO
REPOSITÓRIO** a menos que explicitamente marcado como **HIPÓTESE**.

## Estrutura de diretórios (arquivos versionados: 12)

```
.
├── data/
│   └── hedonic_seed_hybrid.csv          # 626 linhas de dados + cabeçalho
├── database/
│   └── schema.sql                        # cópia de referência do schema
├── docs/                                 # criado nesta auditoria (Fase 0)
├── netlify/
│   ├── database/migrations/
│   │   ├── 20260829090000_create_hedonic_schema.sql
│   │   └── 20260829090100_seed_hybrid_model.sql
│   └── functions/
│       └── hedonic-data.mts              # única Netlify Function
├── scripts/
│   ├── generate-hybrid-seed.mjs          # gera data/hedonic_seed_hybrid.csv
│   └── generate-seed-migration.mjs       # gera a migração de seed a partir do CSV
├── tests/
│   └── model-smoke.mjs                   # único teste do repositório
├── index.html                            # SPA completa (1911 linhas)
├── MODEL.md                              # especificação do modelo hedônico
├── package.json / package-lock.json
└── .claude/settings.local.json           # config local do Claude Code (não versionada — ver Segurança)
```

Não há `.gitignore` no repositório (ver [[06-LESSONS-LEARNED]] /
segurança abaixo). Não há `netlify.toml`. Não há arquivos `.env` no
repositório nem `node_modules` instalado localmente no momento da
auditoria.

## Objetivo do laboratório atual (comprovado)

Demonstrar, de ponta a ponta, um modelo hedônico de precificação de
apartamentos novos: geração de dados de teste → estimação OLS →
visualização → simulador de preço por unidade → documentação
metodológica — funcionando tanto 100% no navegador (dados sintéticos)
quanto contra um PostgreSQL real (dados reais, quando disponíveis).

## Como o modelo hedônico funciona (comprovado, ver `index.html` e `MODEL.md`)

- Variável dependente: `ln(preço/m²)`.
- Regressores: andar (centrado no 10º pavimento + termo quadrático),
  `ln(área privativa)`, vagas, suítes, vista, orientação, posição,
  interação andar×vista, área de varanda, cobertura (flag de penthouse),
  índice de qualidade do produto (média padrão/lazer), qualidade de
  localização, meses desde o lançamento, fase comercial.
- Estimador: OLS com erros-padrão robustos HC3, implementado em
  JavaScript puro dentro de `index.html` (funções `runOLS`, `buildX`,
  `featureRow`, `lgamma`, `incBeta`, `tPValue`, `fPValue` — linhas
  ~1350–1532 de `index.html`).
- Validação: split determinístico 80/20 treino/teste; reporta RMSE, MAE,
  MAPE fora da amostra, teste de Jarque–Bera e maior VIF.
- Variáveis sem variação na amostra são removidas automaticamente antes
  da estimação.

## Dados utilizados (comprovado)

- **Fonte:** `data/hedonic_seed_hybrid.csv`, gerado por
  `scripts/generate-hybrid-seed.mjs` a partir da função
  `generateSampleData()` embutida em `index.html` (gerador com RNG
  seedado — `mulberry32(2024)` — portanto determinístico/reprodutível).
- **Volume:** 626 unidades em 12 empreendimentos fictícios (`NOVO-01` a
  `NOVO-12`), confirmado por contagem de linhas do CSV e pelo teste de
  fumaça (`{"rows":626,...}`).
- **Natureza:** inteiramente sintética/híbrida — calibrada a partir de
  faixas e distribuições publicadas (IPEAD/UFMG, CMI/Secovi-MG,
  ABRAINC/Fipe, Paixão 2023, Eurostat/OECD — fontes citadas em
  `MODEL.md`), **não** contém nenhuma venda real da Patrimar.
- **Colunas do CSV (23):** `id, empreendimento, apartamento, bairro, torre,
  andar, area, quartos, vagas, suite, varanda_m2, cobertura, vista,
  orientacao, posicao, padrao_score, lazer_score, localizacao_score,
  fase_obra, meses_lancamento, desconto_pct, preco_m2, origem`.

## Como a base é gerada (comprovado)

1. `npm run generate:seed` executa `scripts/generate-hybrid-seed.mjs`, que
   carrega o HTML, extrai os `<script>` inline via regex, executa
   `generateSampleData()` num sandbox Node `vm`, e grava o resultado em
   `data/hedonic_seed_hybrid.csv`.
2. `npm run generate:seed-migration` executa
   `scripts/generate-seed-migration.mjs`, que lê esse CSV e gera
   `netlify/database/migrations/20260829090100_seed_hybrid_model.sql`
   (INSERTs idempotentes com `ON CONFLICT ... DO NOTHING`).

Nenhum destes scripts foi executado durante esta auditoria (apenas
inspecionados), para não alterar arquivos versionados.

## PostgreSQL (comprovado)

- Schema normalizado em `database/schema.sql` (também replicado, com
  formatação levemente diferente, em
  `netlify/database/migrations/20260829090000_create_hedonic_schema.sql`
  — os dois arquivos são semanticamente idênticos, ver [[02-ARCHITECTURE]]).
- Tabelas: `data_sources`, `developments`, `units`,
  `unit_price_observations`.
- View de contrato da aplicação: `v_hedonic_model` (filtra
  `first_sale = TRUE`, isto é, somente primeira venda de mercado
  primário — revendas ficam de fora por definição da view).
- Uso do pacote `@netlify/database` (Netlify DB nativo, provisionado
  conforme commit `d4b3785` "feat: provisionar PostgreSQL nativo no
  Netlify"). A função Netlify usa `getDatabase()` desse pacote — **não**
  referencia a variável `DATABASE_URL` diretamente no código (o teste de
  fumaça garante isso explicitamente, ver [[05-WORKLOG]]).
- **HIPÓTESE/NÃO VERIFICADO NESTA AUDITORIA:** se o banco Netlify DB está
  de fato provisionado e populado em produção, e se a migração de seed já
  foi aplicada a ele. A auditoria não teve acesso a credenciais de banco
  nem executou queries remotas.

## Netlify Functions (comprovado)

Uma única função: `netlify/functions/hedonic-data.mts`.
- Rota: `GET /api/hedonic-data`.
- Aceita `?limit=` (padrão 5000, mínimo 50, máximo 20000).
- Consulta `SELECT * FROM v_hedonic_model ORDER BY empreendimento, torre,
  andar, apartamento LIMIT $limit`.
- Retorna `{ data, count, source: 'netlify-postgresql' }` com cache
  `public, max-age=60, stale-while-revalidate=300`.
- Em erro, retorna HTTP 500 com mensagem genérica em português (não
  vaza detalhes internos do erro na resposta; loga no `console.error`).

## Frontend (comprovado)

- `index.html`: SPA estática, sem framework (JS vanilla), sem build
  step, 1911 linhas incluindo CSS e JS inline.
- Dependências externas via CDN: Google Fonts (Poppins) e Chart.js 4.4.0
  (`cdnjs.cloudflare.com`).
- Abas de navegação: **Base de Dados**, **Modelo OLS**, **Prêmios &
  Gráficos**, **Calculadora**, **Metodologia**.
- Suporta tema claro/escuro (`prefers-color-scheme` + toggle manual).
- Pode carregar dados de três formas: (a) gerador sintético embutido
  (`generateSampleData`), (b) upload de CSV pelo usuário (`handleCSV`/
  `parseCSV`), (c) API real via `loadPostgresData()` →
  `fetch(API_CONFIG.endpoint)`, endpoint configurável via
  `window.HEDONIC_API_CONFIG` antes do script carregar. Nenhuma
  credencial de banco aparece no HTML (confirmado por busca por
  `DATABASE_URL`/`postgres://` no arquivo — nenhuma ocorrência).

## Simulador (comprovado)

Existe: aba "Calculadora" (`panel-calculadora`), funções `calcPredict()`,
`predictUnit()`, `modelCoefficient()`, `renderCalcMeta()` — permite
inserir atributos de uma unidade hipotética e obter preço previsto pelo
modelo OLS treinado na sessão atual do navegador.

## Métricas (comprovado, exemplo real de execução do teste em 2026-09-09)

R² = 0.9018, RMSE (teste) = 4186.31, MAPE (teste) = 13.68%, maior VIF =
11.84, N = 626. Ver [[05-WORKLOG]] para o comando exato.

## Testes disponíveis (comprovado)

Um único teste: `tests/model-smoke.mjs` (`npm run test:model`). Roda o
gerador de dados e o OLS num sandbox Node `vm`, e valida invariantes
(tamanho mínimo de amostra, nº mínimo de empreendimentos, coeficientes
finitos, MAPE dentro de uma faixa plausível, R² não artificialmente
perfeito, a função Netlify não depender de `DATABASE_URL` bruto, a
migração de schema conter a view, a migração de seed conter todas as
626 unidades). Resultado desta execução: **PASSOU**, ver [[05-WORKLOG]].

## Fluxo de dados atual (comprovado)

```
generateSampleData() (index.html, JS)
        │
        ├─ usado ao vivo no navegador quando não há API configurada
        │
        └─ scripts/generate-hybrid-seed.mjs → data/hedonic_seed_hybrid.csv
                    │
                    └─ scripts/generate-seed-migration.mjs
                              → netlify/database/migrations/20260829090100_seed_hybrid_model.sql
                                        │
                                        └─ (aplicada manualmente/via Netlify) → PostgreSQL (Netlify DB)
                                                  │
                                                  └─ v_hedonic_model
                                                            │
                                                            └─ netlify/functions/hedonic-data.mts (GET /api/hedonic-data)
                                                                      │
                                                                      └─ index.html → loadPostgresData() → runOLS()
```

## O que NÃO existe hoje (para evitar hipóteses implícitas)

- Não há backend próprio além da única Netlify Function.
- Não há autenticação/autorização de nenhum tipo na função ou no site.
- Não há dados reais da Patrimar no repositório.
- Não há PostGIS, RAW/STAGING/CORE, importação de planilhas, dicionário
  de dados formal além deste, comparáveis de mercado, motor de preços
  separado do modelo, painel além das abas do `index.html`, nem agentes
  de IA operacionais sobre os dados. Esses itens são **plano futuro**,
  ver [[03-ROADMAP]].
- Não há CI/CD configurado no repositório (nenhum workflow do GitHub
  Actions encontrado).
