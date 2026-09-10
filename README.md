# Patrimar Pricing Intelligence

Plataforma de inteligência e governança de precificação imobiliária,
em construção para a Patrimar Engenharia. Este repositório documenta
o processo publicamente, de forma sanitizada — nenhum dado real de
vendas, preços, clientes ou empreendimentos da Patrimar aparece aqui
(ver `docs/04-DECISIONS.md`, D4/D6).

## O que este repositório é

Um produto em evolução com dois motores conceituais, integráveis mas
independentes:

- **Motor B — Unit Price Allocation Engine (validado).** Distribui um
  VGV/preço-base já definido entre as unidades de um empreendimento,
  respeitando área, pavimento, posição e calibrações. A metodologia
  real de um cliente foi reconstruída e **validada de forma
  independente** — 884 unidades reais reproduzidas matematicamente
  dentro de 1 centavo do preço já existente na fonte, sem nunca
  acessar esse preço durante o cálculo (ver
  `docs/17-AMBIGUITY-RESOLUTION-METHOD.md`). A fórmula e os
  parâmetros reais permanecem privados — o que este repositório expõe
  é a arquitetura genérica que sabe *como* calcular, nunca *o que*
  calcular de verdade (ver `docs/04-DECISIONS.md` D12).
- **Motor A — Market Pricing Engine (próxima evolução).** Estimaria
  quanto um produto deveria valer frente ao mercado, a partir de
  comparáveis, geodados e indicadores. Ainda não implementado — hoje
  existe apenas como arquitetura conceitual no produto (página
  "Inteligência de Mercado").

## Demonstração pública (modo DEMO)

O produto publicado (GitHub `main` / Netlify) roda **exclusivamente
em modo DEMO** — todos os dados exibidos são 100% sintéticos, gerados
por um algoritmo de referência público e explicitamente não-oficial
(`REFERENCE_ALLOCATION_V1`, ver `docs/04-DECISIONS.md` D8). Não há,
nem nunca deve haver, nenhum caminho de código no deploy público que
alcance o banco de dados privado.

Um modo **PRIVATE**, com dado real, existe apenas para execução local
autorizada — nunca publicado (ver `docs/19-DEPLOYMENT-AND-DEMO-MODE.md`).

## Estrutura do repositório

```
web/pricing-intelligence/   produto oficial (frontend, dois modos de dado)
legacy/lab/                 laboratório hedônico original — preservado, não mais a interface principal
scripts/                    pipeline de dados, motores, testes, scanner de privacidade
database/v2/                schema PostgreSQL canônico (core/pricing/audit/raw/staging)
fixtures/v2/                cenários 100% sintéticos e públicos
docs/                        documentação viva do projeto — comece por docs/00-PROJECT-CHARTER.md
netlify/functions/          backend do laboratório legado (Netlify Functions)
```

## Documentação

Toda a documentação de arquitetura, decisões e progresso vive em
`docs/`, começando por `docs/00-PROJECT-CHARTER.md`. Para quem está
assumindo o projeto pela primeira vez, `docs/99-HANDOFF.md` traz a
ordem de leitura recomendada e o estado exato da última execução.

## Privacidade

Nenhuma planilha, credencial, nome real de empreendimento, ou
parâmetro de precificação proprietário é versionado neste
repositório. Um scanner automatizado (`scripts/scan_deploy_privacy.py`)
bloqueia qualquer publicação que contenha indícios estruturais de
dado privado antes do deploy — ver `docs/19-DEPLOYMENT-AND-DEMO-MODE.md`.
