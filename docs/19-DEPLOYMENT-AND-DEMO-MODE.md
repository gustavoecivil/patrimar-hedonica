# 19 — Deployment e modo DEMO

Como rodar o Patrimar Pricing Intelligence localmente em modo
PRIVATE (dado real, nunca publicado), como o deploy público no
Netlify funciona em modo DEMO (dado 100% sintético), e como a
publicação é verificada antes de ir ao ar. Nenhum valor privado real
aparece neste documento — apenas comandos e estrutura.

## Modo PRIVATE (local, dado real)

1. Pré-requisito: PostgreSQL local com o banco privado
   `patrimar_pricing_v2_private_dev` já populado (Fase 3A/3B/3D — ver
   [[14-PRIVATE-DATA-INGESTION]], [[15-STAGING-TO-CANONICAL-PROMOTION]]).
   Credenciais vivem só em `.env.pricing_v2_private_dev` (local,
   `.gitignore`, nunca commitado).
2. Suba o servidor local, somente leitura:
   ```bash
   python scripts/pricing_preview_server.py --env-file .env.pricing_v2_private_dev
   # se psql não estiver no PATH:
   #   PSQL_BIN=<caminho completo do psql.exe> python scripts/pricing_preview_server.py --env-file ...
   ```
   Bind **exclusivo em `127.0.0.1:8765`** — nunca `0.0.0.0` (ver
   código-fonte do script, `BIND_HOST`). Serve apenas
   `GET /api/dataset`, somente leitura (nenhum `INSERT`/`UPDATE`/
   `DELETE` no banco).
3. Sirva o frontend localmente (qualquer servidor estático simples) e
   abra em `http://127.0.0.1:<porta>/index.html`:
   ```bash
   cd web/pricing-intelligence
   python -m http.server 8899 --bind 127.0.0.1
   ```
4. Na página, clique **PRIVATE** no rodapé da barra lateral (só
   aparece quando a página está em `localhost`/`127.0.0.1` — ver
   `privateModeAvailable()` em `data-provider.js`).

O dataset PRIVATE reflete o resultado real da reprodução independente
(Fase 3D): 884 unidades, comparadas contra
`pricing.reproduction_comparisons` (o run `REPRODUCTION_VALIDATION_RUN`
mais recente por empreendimento — `scripts/pricing_preview_server.py`
usa `audit.reproduction_runs` para escolher sempre a tentativa final,
nunca uma tentativa antiga). Limitação conhecida desta primeira versão:
`floor_factor`/`position_factor` por unidade não são recalculados
aqui (aparecem como vazio na tabela) — o preço final e a comparação
com a referência **são** os valores reais.

## Modo DEMO (público, Netlify)

- **Site Netlify:** `imaginative-fudge-64c0aa`
  (`https://imaginative-fudge-64c0aa.netlify.app`), já associado ao
  repositório `github.com/gustavoecivil/patrimar-hedonica`, branch
  `main`, deploy automático via integração GitHub nativa do Netlify
  (sem `netlify deploy` manual necessário no fluxo normal).
- **`netlify.toml`** (raiz do repositório) redireciona o diretório de
  publicação para `web/pricing-intelligence` — o laboratório legado
  (`legacy/lab/`) não é mais publicado como site.
- **Dataset DEMO:** `web/pricing-intelligence/demo-data.json`, gerado
  por:
  ```bash
  python scripts/generate_pricing_intelligence_demo_data.py
  ```
  100% sintético — reaproveita `scripts/reference_allocation_engine.py`
  (D8) e `fixtures/v2/reference_allocation_scenario.json`, já públicos.
  Deve ser regenerado (e recommitado) sempre que
  `reference_allocation_engine.py`/o cenário sintético mudarem;
  **nunca** deve ser substituído por um export do banco privado.
- **Netlify Function do laboratório legado**
  (`netlify/functions/hedonic-data.mts`) permanece no repositório
  inalterada — Netlify Functions são detectadas independentemente do
  diretório de publicação, então continuar existindo não afeta o novo
  produto nem expõe dado adicional. O novo produto DEMO **não usa**
  nenhuma Netlify Function — lê o JSON estático diretamente.
- Nenhuma variável de ambiente do Netlify aponta para
  `patrimar_pricing_v2_private_dev` — o deploy público nunca tem
  acesso de rede a esse banco.

## Scanner de privacidade (bloqueio de deploy)

`scripts/scan_deploy_privacy.py` varre o diretório de publicação
(`web/pricing-intelligence/` por padrão — o mesmo apontado por
`netlify.toml`) e falha (`exit 1`) se encontrar:

- Arquivos `.env*`, `.xlsx`/`.xls`, `.sql`, `.py`, `.ps1` dentro do
  bundle publicado.
- Padrões de credencial Postgres (`PGPASSWORD=`, `postgres://user:pass@`,
  `DATABASE_URL=`).
- Um hash SHA-256 bruto (64 caracteres hex) em qualquer arquivo — os
  hashes de auditoria de XLSX (Fase 1B) nunca devem aparecer no
  bundle público.
- Qualquer caminho `data/restricted` referenciado em texto.
- O nome do banco privado (`patrimar_pricing_v2_private_dev`).
- `demo-data.json` com `meta.mode` diferente de `"DEMO"` (proteção
  contra publicar acidentalmente um dataset PRIVATE).

Uso:
```bash
python scripts/scan_deploy_privacy.py --dir web/pricing-intelligence
```
Saída `OK` = pode publicar. Qualquer `FALHA` deve bloquear o deploy
até ser corrigida — nunca ignorada com `--force` (o script não tem
essa opção, de propósito).

Opcionalmente, uma pessoa com acesso aos nomes reais dos dois
empreendimentos pode rodar uma conferência extra, **local, nunca
commitada**:
```bash
python scripts/scan_deploy_privacy.py --markers-file data/restricted/privacy_markers.txt
```
(um marcador por linha; o próprio arquivo de marcadores nunca é
versionado — mora em `data/restricted/`, coberto por `.gitignore`).

## Checklist antes de promover para `main`/Netlify

1. `python scripts/scan_deploy_privacy.py --dir web/pricing-intelligence` → `OK`.
2. Suite de testes (ver [[99-HANDOFF]], seção "Comandos úteis") →
   todos passando.
3. Verificação manual em navegador do modo DEMO servido localmente
   (golden path: as 6 páginas, tabela de unidades, painel de detalhe,
   responsivo) — feita nesta fase via automação de navegador.
4. `git status` limpo, recovery tag confirmada (ver [[04-DECISIONS]]
   entrada desta fase) antes de qualquer substituição de `main`.
5. Após deploy: `curl -I` na URL pública confirmando HTTP 200, e
   verificação visual de que nenhuma página exibe dado privado.
