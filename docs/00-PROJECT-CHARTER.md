# 00 — Project Charter

## Propósito

O `patrimar-hedonica` é o repositório de origem do que está evoluindo de um
**laboratório de modelo hedônico** (prova de conceito de precificação de
apartamentos novos) para o **Patrimar Pricing Intelligence**: uma plataforma
de inteligência de precificação imobiliária para a Patrimar Engenharia,
combinando banco de dados próprio, modelos estatísticos, simulador de preço
e painel de análise.

## Evolução do laboratório hedônico

**Estado de origem (comprovado no repositório):** uma aplicação estática de
página única (`index.html`) que gera uma base sintética/híbrida de 626
unidades em 12 empreendimentos fictícios, estima um modelo hedônico OLS
inteiramente no navegador (JavaScript, sem backend), e opcionalmente carrega
dados reais de um banco PostgreSQL (Netlify DB) via uma Netlify Function
(`GET /api/hedonic-data`). Esse laboratório foi preservado — nunca apagado
— em `legacy/lab/` a partir da Fase 3E (ver [[04-DECISIONS]] D15).

**Estado atual do produto (Fase 3E, 2026-09-10):** o laboratório deixou
de ser a interface principal. O produto oficial é o **Patrimar Pricing
Intelligence** (`web/pricing-intelligence/`), com dois modos de dado —
**PRIVATE** (dado real, execução local apenas) e **DEMO** (100%
sintético, único modo do deploy público no GitHub `main`/Netlify) — ver
[[04-DECISIONS]] D14 e [[18-PRICING-INTELLIGENCE-MVP]]. O Unit Price
Allocation Engine (Motor B, D7) já foi reproduzido matematicamente com
884/884 unidades reais dentro de 1 centavo (Fase 3D,
`NEAR_EXACT_WITH_EXPLAINED_ROUNDING`) e essa validação é a base do que
o produto mostra na página Validação (em modo PRIVATE, com o dado
real; em modo DEMO, com equivalente sintético).

**Direção declarada:** o Market Pricing Engine (Motor A, D7) ainda não
tem nenhuma fonte de dado real — a página "Inteligência de Mercado" do
produto mostra apenas a arquitetura conceitual futura, rotulada
"PRÓXIMA EVOLUÇÃO". O objetivo segue evoluindo para uma arquitetura
com dados reais da Patrimar, modelos concorrentes avaliados entre si,
um simulador comercial completo e um painel de acompanhamento. Essa
evolução é tratada como **hipótese/plano futuro** e está detalhada,
sem implementação, em [[03-ROADMAP]].

**Decisão arquitetural (Fase 1D, ver [[04-DECISIONS]] D7):** "motor de
preços" acima se desdobra em dois motores conceituais separados e
integráveis — o **Market Pricing Engine** (estima valor de mercado) e
o **Unit Price Allocation Engine** (distribui um VGV/preço-base entre
as unidades de um empreendimento). Ver
[[10-PRICING-DOMAIN-MODEL]] para os princípios resultantes.

## Princípio de independência das planilhas

O projeto deve ser capaz de operar e evoluir **sem depender de planilhas
manuais** (ex.: as planilhas hoje mantidas por Rodolfo) como fonte de
verdade operacional. Planilhas podem ser uma fonte de dados a ser auditada
e importada, mas não podem permanecer como o repositório de conhecimento
do negócio. O repositório de código e banco de dados é que deve carregar
esse papel — ver [[04-DECISIONS]].

## Objetivo futuro (não implementado ainda)

Banco de dados relacional (PostgreSQL/PostGIS) + modelos hedônicos e
concorrentes + motor de preços + simulador + painel de acompanhamento +
agentes de IA operando sobre essa base. Nenhum desses componentes além do
que já existe no laboratório atual foi implementado até a data desta
auditoria (2026-09-09). Ver [[01-CURRENT-STATE]] para o que de fato existe
hoje e [[03-ROADMAP]] para as fases futuras.

## Como este documento deve ser usado

Qualquer agente (Claude, Codex, Gemini, modelo local, ou humano) que assuma
este projeto deve ler este documento primeiro para entender o *porquê* do
projeto antes de olhar o código. Decisões que alterem este propósito devem
ser registradas em [[04-DECISIONS]].
