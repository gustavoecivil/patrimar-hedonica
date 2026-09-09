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
(`GET /api/hedonic-data`).

**Direção declarada:** este laboratório é o ponto de partida técnico —
não o produto final. O objetivo é evoluir para uma arquitetura com dados
reais da Patrimar, staging/core de dados, modelos concorrentes avaliados
entre si, um motor de preços, um simulador comercial e um painel de
acompanhamento. Essa evolução é tratada como **hipótese/plano futuro** e
está detalhada, sem implementação, em [[03-ROADMAP]].

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
