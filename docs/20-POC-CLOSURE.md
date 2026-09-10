# 20 — Encerramento da Prova de Conceito (Fase 3F)

Registra a Fase 3F: encerramento formal do ciclo atual do Patrimar
Pricing Intelligence como uma **prova de conceito funcional** —
polida, documentada e apresentável — não como sistema corporativo de
produção. Nenhum dado privado real, fórmula proprietária ou valor
numérico real da Patrimar aparece neste documento.

## Posicionamento oficial

**Patrimar Pricing Intelligence — Status: Prova de Conceito
Funcional.** A aplicação demonstra transformação de dados de
planilha em estrutura de banco, reprodução independente da
metodologia, rastreabilidade, governança de cálculo, parametrização,
calibração, intervenção humana auditável e capacidade de evolução.
**Não é declarada `PRODUCTION READY`.**

## Feature freeze

A partir desta fase, nenhuma funcionalidade nova foi adicionada:
login, permissões, workflow corporativo, edição produtiva,
integrações ERP/CRM, Motor A operacional, novos modelos de ML e
agentes permanecem **fora de escopo**. O trabalho desta fase foi
polimento, clareza, documentação, segurança e entrega — nunca
expansão de funcionalidade.

## Identificação de POC na interface

O produto (`web/pricing-intelligence/`) agora exibe, de forma
elegante e permanente: um selo "Prova de Conceito" na barra lateral
(com o texto completo "Ambiente demonstrativo. Não representa ainda
um sistema corporativo de produção." disponível via tooltip), e uma
nota de rodapé sensível ao modo de dado ativo — "POC • Dados privados
locais" em modo PRIVATE, "POC • Dados sintéticos" em modo DEMO.

## Linguagem de validação corrigida

Toda referência à precisão da reprodução foi revisada para nunca
implicar igualdade decimal absoluta quando isso não é o que foi
comprovado. Onde antes o texto era vago, passou a explicitar: "884 de
884 unidades dentro de R$ 0,01 do preço já existente na fonte". A
formulação comercial "100% a centavo" permanece, mas sempre
acompanhada do texto detalhado correto — nunca "zero diferença
decimal" sem que isso seja tecnicamente verdadeiro.

## Correção de um defeito real encontrado durante o polimento

A verificação end-to-end do modo PRIVATE contra o banco real revelou
um defeito genuíno na interface, não presente no modo DEMO: unidades
reais sem pavimento identificado (`floor = NULL`, presente em 100%
das 884 unidades reais) faziam um dos gráficos da Visão Geral lançar
uma exceção não tratada, que por sua vez acionava um `alert()` — um
diálogo nativo do navegador que bloqueia toda a aba, inclusive para
ferramentas de automação. Corrigido em duas frentes: (1) a lógica de
agrupamento por pavimento agora ignora unidades sem pavimento
conhecido, com um estado vazio explicativo em vez de um gráfico
quebrado; (2) o tratamento de erro da troca de modo de dado deixou de
usar `alert()`, substituído por uma mensagem inline não bloqueante.
Também foram corrigidos, no mesmo processo, valores como "0,00 m²"
ou "0,0000%" que apareciam quando um campo (área ponderada,
participação relativa, pesos de calibração) simplesmente não estava
disponível para aquela execução — agora exibidos como "—", nunca como
um zero que poderia ser confundido com o valor real.

## Status formal do Motor B

**UNIT PRICE ALLOCATION ENGINE (Motor B):**
- `MATHEMATICAL_REPRODUCTION = VALIDATED`
- `UNITS = 884`
- `CENT_PRECISION_COVERAGE = 884/884`
- `DATABASE_MODEL = VALIDATED`
- `LINEAGE = VALIDATED`
- `PRIVATE_RUNTIME = VALIDATED`
- `DEMO_RUNTIME = VALIDATED`
- `BUSINESS_SEMANTICS = PARTIAL` (2 perguntas de negócio pendentes,
  não bloqueadoras — ver [[99-HANDOFF]])

## Publicação DEMO e execução PRIVATE

Inalterado em relação à Fase 3E (ver [[18-PRICING-INTELLIGENCE-MVP]]
e [[19-DEPLOYMENT-AND-DEMO-MODE]]): o deploy público continua
executando exclusivamente em modo DEMO (100% sintético); o modo
PRIVATE continua disponível apenas localmente, contra o banco privado
real, nunca publicado.

## Pacote de entrega (privado, não versionado)

Um pacote de materiais de apresentação foi produzido em
`data/restricted/deliverables/` (relatório executivo, resumo de uma
página, roteiro de demonstração, FAQ do apresentador, checklist de
apresentação) — **nenhum desses arquivos é ou pode ser versionado**
(cobertos por `.gitignore`, mesma regra de `data/restricted/`, ver
[[04-DECISIONS]] D6). Esta entrega não constitui proposta comercial:
não contém preço, mensalidade, prazo de implantação ou orçamento.

## Próximos passos opcionais (não iniciados)

1. Validar com quem mantém a planilha hoje as 2 perguntas de negócio
   pendentes (origem de valores de calibração; critério de ajuste
   manual) — não bloqueadoras, mas recomendadas antes de qualquer
   decisão de produção.
2. Decisão de negócio sobre iniciar (ou não) o desenho do Motor A
   (Market Pricing Engine).
3. Revisão e aprovação desta entrega por Gustavo Santos antes de
   qualquer novo desenvolvimento.

Nenhum desses itens foi iniciado nesta fase — por definição de
feature freeze.
