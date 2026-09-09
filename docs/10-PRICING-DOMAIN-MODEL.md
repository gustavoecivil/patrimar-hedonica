# 10 — Modelo de Domínio de Precificação

Este documento registra a **decisão arquitetural** de separar a
precificação futura da Patrimar em dois motores conceituais, e os
princípios genéricos de modelagem que resultam disso — sem conteúdo
proprietário (nomes de arquivo, de empreendimento, valores, fórmulas
específicas ou parâmetros). Detalhe privado (com conteúdo real das
planilhas) fica em `data/restricted/audit/`
(`preliminary-canonical-model.md`, `gap-analysis-summary.md`) — ver
[[04-DECISIONS]] D4/D6.

## Decisão arquitetural: dois motores separados e integráveis

A engenharia reversa da lógica de precificação existente (Fase 1C)
revelou que a metodologia hoje em uso resolve **um problema
específico**: distribuir um valor-alvo (VGV) entre as unidades de um
empreendimento já definido, respeitando diferenças internas de área,
posição e pavimento. Ela **não** resolve — e não tenta resolver — a
pergunta de quanto o produto deveria valer frente ao mercado.

A partir desta fase, o projeto formaliza essa distinção como dois
motores conceituais:

### Motor A — Market Pricing Engine

Responde: **quanto o produto/empreendimento/tipologia/unidade deveria
valer frente ao mercado?**

Fontes conceituais futuras: comparáveis de mercado, transações,
ofertas/listings, concorrência, indicadores econômicos, características
físicas e de localização, modelos estatísticos/hedônicos ou de
aprendizado de máquina.

Saídas conceituais: preço-base recomendado, R$/m² recomendado, VGV
recomendado, faixa de confiança, evidências de mercado que sustentam
a estimativa.

### Motor B — Unit Price Allocation Engine

Responde: **dado um VGV/preço-base já definido, como distribuir esse
valor entre as unidades**, respeitando diferenciações internas
(área, área ponderada, pavimento, posição, parâmetros de calibração,
participação proporcional, ajustes manuais).

```
MOTOR A (Market Pricing Engine)
        ↓
VGV / preço-base recomendado
        ↓
MOTOR B (Unit Price Allocation Engine)
        ↓
preço individual das unidades
```

Hoje, apenas o Motor B tem metodologia evidenciada e reconstruída com
confiança alta. O Motor A ainda não existe como mecanismo formal — o
laboratório hedônico atual (modelo OLS sobre dados sintéticos, ver
[[00-PROJECT-CHARTER]] e [[01-CURRENT-STATE]]) é um protótipo
funcional na direção do Motor A, mas ainda não usa dado real de
mercado.

## Por que separar os dois motores

- **Responsabilidades diferentes.** Estimar valor de mercado e
  distribuir um valor já definido são problemas com fontes de dados,
  frequência de atualização e critérios de validação distintos.
- **Evolução independente.** O Motor B já pode ser formalizado hoje
  (a lógica existe, evidenciada por fórmula); o Motor A depende de
  fontes de dados que ainda precisam ser adquiridas.
- **Ponto único de integração explícito.** O VGV/preço-base recomendado
  é o único dado que precisa fluir do Motor A para o Motor B — isso
  evita acoplar prematuramente as duas lógicas.

## Princípios de modelagem adotados

### Classificação de dados: origem separada de processamento

Todo dado no sistema futuro deve ser classificado em duas dimensões
independentes, nunca fundidas:

- **Origem**: real, pública, manual, estimada, simulada, híbrida, ou
  ausente/desconhecida.
- **Status de processamento**: entrada direta, parâmetro, derivado,
  intermediário, ajuste, resultado, override, ou apresentação.

Um dado pode ser, por exemplo, "origem real + processamento derivado"
(um cálculo feito sobre dado real) — as duas dimensões não são
mutuamente exclusivas e não devem ser tratadas como se fossem.

### Granularidade explícita

Toda entidade conceitual do domínio precisa declarar sua granularidade
(ex.: portfólio, empreendimento, torre, tipologia, unidade, data,
observação de mercado, cenário de precificação, execução de
precificação, execução de modelo). Isso evita ambiguidade ao desenhar
o schema físico numa fase futura.

### Histórico como padrão, não excepção

Princípio adotado: **nenhuma decisão histórica relevante deve ser
sobrescrita sem rastreabilidade.** Parâmetros, tabelas de calibração,
metas de VGV, preços de unidade, overrides, regras de negócio,
cenários, e decisões humanas são candidatos padrão a manter histórico
— a exceção (não manter histórico) deve ser justificada, não o
contrário.

### Versionamento por execução (run) de precificação

Cada rodada de cálculo de preço deve ser tratada como uma execução
identificável e imutável, associada ao conjunto de parâmetros que
usou. Isso permite comparar, auditar, e nunca perder o estado de uma
decisão anterior — uma arquitetura de acréscimo (não de sobrescrita)
é o padrão avaliado para decisões de precificação.

### Overrides humanos nunca substituem o histórico

Um override (ajuste manual sobre um resultado calculado) deve
registrar, conceitualmente: o valor produzido pelo sistema antes do
override, o valor humano, o valor final efetivamente usado, o motivo,
o autor, o momento, o cenário/execução ao qual pertence, e o impacto
resultante no agregado (ex.: no VGV total). O valor anterior nunca é
perdido — um novo override é um novo registro, não uma edição do
anterior.

### Regras ativas e dormentes

O modelo de domínio precisa suportar que uma regra de negócio exista,
esteja definida, mas não esteja ativa num dado momento/cenário — com
validade temporal, versão, motivo da ativação/inativação, e autor da
decisão. Uma regra dormente não deve ser tratada como inexistente nem
removida — ela é parte do histórico metodológico do domínio.

### Validação sem assumir igualdade cega

Uma invariante de negócio esperada (ex.: a soma dos preços finais das
unidades se aproximar do VGV-alvo de um cenário) deve ser **verificada
e exposta**, não assumida como verdade absoluta — overrides humanos
podem, de forma legítima, criar desvio entre o valor calculado e o
valor final. O sistema deve conseguir mostrar esse desvio, não apenas
confirmar ou negar uma igualdade exata.

## Onde fica o detalhe

O mapeamento completo de conceitos, a matriz de gap analysis, a
matriz de variáveis de precificação, e o modelo canônico preliminar
com entidades/relações específicas ficam em `data/restricted/audit/`
— documentos privados que citam a estrutura real das planilhas
analisadas. Este documento público registra apenas os princípios que
resultam dessa análise.
