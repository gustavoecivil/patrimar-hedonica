# 18 — Patrimar Pricing Intelligence: MVP do produto oficial

Registra a Fase 3E: a transformação do trabalho das Fases 1–3D em um
**produto oficial** — substituindo o laboratório hedônico legado como
interface principal do repositório (GitHub) e do deploy público
(Netlify). Não contém dado privado, fórmula proprietária ou valor
numérico real (ver [[04-DECISIONS]] D4/D6/D12).

## O que mudou

- **Novo nome/produto:** "PATRIMAR / PRICING INTELLIGENCE" —
  subtítulo "Plataforma de Inteligência e Governança de Precificação".
  O antigo nome "Análise Hedônica" deixa de ser a identidade do
  produto; o modelo hedônico OLS do laboratório passa a ser tratado
  como um componente futuro do Motor A (Market Pricing Engine, ver
  [[04-DECISIONS]] D7), não como o produto inteiro.
- **Novo frontend:** `web/pricing-intelligence/` (HTML/CSS/JS puro,
  sem framework, reaproveitando Chart.js como o laboratório legado
  já fazia) substitui `index.html` como a página inicial do produto.
- **Laboratório legado preservado, não apagado:** movido para
  `legacy/lab/` (`git mv`, histórico preservado) — continua
  navegável e testável (`npm run test:model` aponta para o novo
  caminho), mas deixou de ser a experiência principal.
- **Identidade visual reaproveitada, não recriada:** todos os tokens
  de design (cores, fonte Poppins, logo) vieram literalmente do
  `:root` e do asset embutido em base64 do `legacy/lab/index.html` —
  ver `web/pricing-intelligence/styles.css` (comentário no topo do
  arquivo) e `web/pricing-intelligence/assets/logo-grupo-patrimar-branca.png`
  (extraído byte-a-byte do base64 original, nunca redesenhado).

## Dois modos de dado: PRIVATE e DEMO

A interface nunca sabe, por si só, se está mostrando dado real ou
sintético — essa decisão é isolada numa camada única,
`web/pricing-intelligence/data-provider.js` (`window.dataProvider`).

- **DEMO** — único modo disponível fora de `localhost`/`127.0.0.1`.
  Lê um arquivo estático, `web/pricing-intelligence/demo-data.json`,
  gerado por `scripts/generate_pricing_intelligence_demo_data.py` a
  partir do motor **já público e sintético**
  `scripts/reference_allocation_engine.py` (ver [[04-DECISIONS]] D8 —
  `REFERENCE_ALLOCATION_V1` nunca deve ser confundido com a
  metodologia real). 100% dos números do modo DEMO são fictícios.
- **PRIVATE** — só oferecido quando a página roda em
  `localhost`/`127.0.0.1` (checagem em `isLocalHost()`,
  `data-provider.js`). Consome
  `GET http://127.0.0.1:8765/api/dataset`, servido por
  `scripts/pricing_preview_server.py` (ver [[19-DEPLOYMENT-AND-DEMO-MODE]]
  para detalhes de execução e isolamento).
- **Nunca há fallback automático** entre os dois modos — a troca é
  sempre uma ação explícita da pessoa usuária (botão DEMO/PRIVATE no
  rodapé da barra lateral).

## Páginas do produto

- **Visão Geral** — cards executivos (VGV, unidades, preço médio/m²,
  torres, ajustes humanos, precisão da reprodução) + 6 gráficos
  (preço/m² por pavimento, preço × área, participação por torre,
  distribuição de preços, ajustes humanos, referência × reprodução).
- **Unidades** — tabela completa com busca, filtro por status,
  ordenação por coluna e paginação; clique numa linha abre o painel
  de detalhe da unidade (características + preço sistemático + ajuste
  opcional + preço final + participação relativa).
- **Precificação** — fluxo conceitual de negócio ("Como o preço foi
  formado"): características → parâmetros/calibrações →
  pesos relativos → participação → preço calculado → ajuste comercial
  opcional → preço final. **Nunca expõe a fórmula proprietária** —
  apenas os passos conceituais, consistente com [[04-DECISIONS]] D12.
- **Validação** — indicadores executivos (unidades analisadas,
  correspondências a centavo, precisão, diferença agregada),
  refletindo a reprodução independente já registrada em
  [[16-INDEPENDENT-PRICING-REPRODUCTION]] e [[17-AMBIGUITY-RESOLUTION-METHOD]]
  (modo PRIVATE) ou dados 100% sintéticos equivalentes (modo DEMO).
- **Auditoria** — resumo executivo de rastreabilidade (fonte,
  execução, cenário, parâmetros, calibrações, ajustes, preço
  sistemático, ajuste humano, preço final), em linguagem de negócio,
  sem expor detalhes de engenharia (schema, SHA, PR, DAG).
- **Inteligência de Mercado** — rotulada "PRÓXIMA EVOLUÇÃO". Mostra o
  diagrama conceitual do Motor A (Market Pricing Engine, D7) sem
  simular que ele já está operacional — nenhum dado real ou sintético
  é apresentado como recomendação de mercado nesta fase.

## Responsividade

Desktop: sidebar fixa. Tablet/mobile (`≤900px`): sidebar vira gaveta
deslizante com overlay e botão hambúrguer fixo no topo. `≤640px`:
grade de cards reduz para 2 colunas, painel de detalhe ocupa 100% da
largura. `≤420px`: grade de cards vira 1 coluna. Tabelas usam
`overflow-x: auto` no próprio contêiner — a página nunca gera
scroll horizontal indesejado.

## O que este MVP explicitamente NÃO faz

- Não promove nenhum resultado reproduzido a "preço oficial de
  produção" — mantém a mesma cautela de [[99-HANDOFF]] (risco 5) das
  fases anteriores.
- Não implementa o Motor A (Market Pricing Engine) — apenas mostra a
  arquitetura conceitual futura.
- Não permite edição de ajuste humano/calibração nesta versão —
  ambos são apresentados como somente leitura, com campos futuros
  (valor, motivo, responsável, data, impacto no VGV) documentados mas
  não implementados.
- Não conecta o deploy público (Netlify) a nenhum banco privado — ver
  [[19-DEPLOYMENT-AND-DEMO-MODE]].

Ver [[19-DEPLOYMENT-AND-DEMO-MODE]] para como rodar localmente (modo
PRIVATE), como o deploy público (modo DEMO) funciona, e para o
scanner de privacidade que bloqueia publicação de dado privado.
