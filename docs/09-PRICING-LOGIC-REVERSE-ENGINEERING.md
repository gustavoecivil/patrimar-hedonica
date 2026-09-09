# 09 — Metodologia de Engenharia Reversa da Lógica de Precificação

Este documento descreve **apenas a metodologia** usada para
reconstruir, com evidência, o raciocínio de precificação existente em
planilhas privadas recebidas de fontes externas (ex.: planilhas de
Rodolfo/Patrimar). **Não contém** nomes de arquivo, nomes de
empreendimento, valores, fórmulas específicas, parâmetros, nomes reais
de aba/campo, ou qualquer conteúdo comercial da Patrimar — ver
[[04-DECISIONS]] D4/D6. Toda essa metodologia parte da estrutura já
levantada em [[08-SPREADSHEET-AUDIT-METHOD]] (Fase 1B).

## Objetivo

Diferente da auditoria estrutural (Fase 1B, que respondia "o que
existe" numa planilha), esta fase responde "o que a planilha calcula e
por quê" — sem ainda desenhar um banco de dados definitivo, migrar
dados, ou alterar qualquer sistema em produção. É uma etapa de
**leitura e interpretação com evidência**, não de implementação.

## Princípio central: nunca concluir sem evidência de fórmula

Toda afirmação sobre o que uma célula/coluna representa precisa estar
ancorada em pelo menos uma destas evidências:

- o texto literal da fórmula da célula (lido diretamente do arquivo,
  nunca deduzido do nome do campo isoladamente);
- o grafo de dependências entre células/abas (o que referencia o quê);
- o rótulo textual explícito associado à célula (quando existe, ex.:
  um rótulo ao lado de uma célula de parâmetro);
- o comportamento numérico observado (ex.: uma coluna sem fórmula e
  com baixa cobertura de preenchimento é evidência de entrada manual
  esporádica, não de cálculo).

Nomes de campo por si só são tratados como **hipótese fraca**, nunca
como prova. Quando a única evidência disponível é o nome de um campo
ambíguo, a conclusão correspondente é marcada com confiança BAIXA e
frequentemente gera uma pergunta para revisão humana em vez de uma
afirmação.

## Taxonomia de classificação de blocos/células

Cada célula ou bloco relevante é classificado em uma destas
categorias, sem forçar uma classificação quando a evidência não
sustenta nenhuma delas (categoria `UNKNOWN`):

`SOURCE_INPUT`, `MANUAL_INPUT`, `PARAMETER`, `LOOKUP`, `FILTER_RULE`,
`DERIVED`, `INTERMEDIATE`, `ADJUSTMENT`, `SCORE`, `OUTPUT`,
`OVERRIDE`, `PRESENTATION`, `UNKNOWN`.

Cada classificação recebe um nível de confiança (`HIGH`/`MEDIUM`/
`LOW`), nunca uma certeza binária.

## Identificação de outputs

Um candidato a resultado final (preço, preço por m², faixa, prêmio,
etc.) não é aceito apenas pelo nome do campo. A confirmação exige
rastreamento reverso pelo grafo de dependências: a partir da célula
candidata, seguem-se os precedentes (o que ela usa) até chegar a
entradas e parâmetros já classificados, e verifica-se se algo mais na
planilha depende dela (se nada depende, é candidata a output; se algo
depende, pode ser intermediário).

## Regras de seleção, ajuste e homogeneização

Mecanismos de seleção/exclusão de comparáveis (quando existem) são
classificados como `AUTOMATIC`, `MANUAL` ou `MIXED`, com base em se a
regra é uma fórmula (automática), uma célula editável sem fórmula
(manual), ou uma combinação das duas. O mesmo vale para ajustes/
homogeneizações: cada ajuste identificado é catalogado com sua entrada,
fórmula, parâmetro usado, e origem do parâmetro (fórmula fixa,
célula manual, tabela de referência, ou valor derivado de outro
cálculo).

## Constantes numéricas ("parâmetros mágicos")

Números literais embutidos diretamente em fórmulas (ex.: um percentual
fixo, um limite usado em uma condição) são extraídos
programaticamente e listados privadamente, cada um com um papel
possível sugerido de forma conservadora (ex.: "possível percentual ou
peso", "possível índice de busca") e uma marcação de se aquele número
provavelmente requer explicação humana antes de ser tratado como
parâmetro de negócio real — nunca se assume automaticamente o
significado de uma constante.

## Overrides e julgamento humano

Pontos onde um valor pode ser alterado manualmente (uma fórmula
substituída por um número digitado, um parâmetro editável, uma
exclusão manual) são classificados como `HUMAN_JUDGMENT_REQUIRED`,
`HUMAN_OVERRIDE_OPTIONAL`, `FULLY_AUTOMATIC` ou `UNKNOWN`. Essa
classificação é o insumo mais importante para decidir, em fases
futuras, o que deve continuar sendo uma decisão humana explícita num
sistema novo (nunca automatizada) versus o que pode ser calculado
automaticamente.

## Inconsistências de fórmula

Regiões onde o padrão de fórmula de uma coluna muda de forma
inesperada (uma fórmula diferente no meio de uma sequência, uma
constante diferente, uma referência deslocada, um valor manual dentro
de uma região calculada) são sinalizadas, nunca corrigidas nesta fase.
Cada ocorrência é classificada como `EXPECTED_VARIATION`,
`POSSIBLE_MANUAL_OVERRIDE`, `POSSIBLE_ERROR` ou `UNKNOWN` — a decisão
entre essas quatro opções é sempre revisada manualmente antes de
qualquer conclusão, porque a mesma divergência estrutural pode ter
causas muito diferentes.

### Cuidado com fórmulas compartilhadas do formato XLSX

O formato OOXML permite que uma fórmula seja "compartilhada" entre
várias células, guardando o texto completo apenas na célula-mestre e
apenas uma referência nas demais. Uma ferramenta que reconstrua o
texto da fórmula para fins de leitura precisa, ao encontrar uma
referência sem texto próprio, ou (a) recalcular corretamente o
deslocamento de linha/coluna a partir da fórmula-mestre, ou (b)
deixar explícito que o texto mostrado para aquela célula é apenas uma
aproximação. Qualquer divergência de fórmula encontrada dessa forma
deve ser confirmada contra o XML bruto do arquivo antes de ser tratada
como uma inconsistência real da planilha original — do contrário, um
artefato da própria ferramenta de leitura pode ser confundido com um
achado de negócio.

## Comparação entre múltiplos workbooks

Quando mais de um workbook privado é analisado, a comparação segue
três eixos: estrutura (mesma sequência de etapas de cálculo?),
parâmetros (mesmos parâmetros usados, ainda que com valores
diferentes?), e resultado (mesma forma de calcular o resultado final?).
Cada correspondência recebe confiança `HIGH`, `MEDIUM` ou `LOW`. A
data de criação/modificação do arquivo **nunca** é usada como
evidência de que uma versão é "mais nova" ou "mais correta" que outra
— apenas o conteúdo estrutural é comparado.

## Catálogo de regras de negócio

Cada regra identificada (de qualquer natureza: filtro, busca,
transformação, ajuste, agregação, seleção, pontuação, validação,
override, ou resultado) é registrada com: descrição, entrada,
expressão, parâmetro, saída, grau de automaticidade, grau de
intervenção humana, evidência que sustenta a classificação, confiança,
e (quando aplicável) uma pergunta pendente para quem forneceu a
planilha original. Isso forma a base para decidir, em fases futuras,
o que pode ir para um banco de dados/pipeline automatizado, o que
precisa de uma regra de negócio configurável, e o que deve continuar
exigindo uma decisão humana explícita.

## Perguntas para quem forneceu a planilha

Perguntas geradas nesta fase evitam qualquer coisa respondível apenas
lendo a própria planilha. O foco é: origem de parâmetros, motivo de
pesos/critérios específicos, quando uma exceção é aplicada, significado
de campos ambíguos, frequência de atualização de tabelas de referência,
e critérios subjetivos que não aparecem em nenhuma fórmula. Cada
pergunta é priorizada como `CRITICAL`, `IMPORTANT` ou `OPTIONAL`.

## Mapa de automação

Para cada regra do catálogo, avalia-se o potencial de automação em
quatro níveis: `AUTOMATABLE_NOW` (cálculo determinístico, sem
julgamento humano necessário), `AUTOMATABLE_WITH_MORE_DATA` (mecanismo
automatizável, mas depende de uma tabela/calibração ainda não
totalmente esclarecida), `REQUIRES_BUSINESS_RULE` (o mecanismo pode
ser automatizado, mas o valor do parâmetro é uma decisão de negócio que
não deve ser inferida), e `REQUIRES_HUMAN_JUDGMENT` (deve permanecer
uma decisão humana explícita em qualquer sistema futuro). Esse mapa é
o principal insumo para decisões futuras sobre o que vai para banco de
dados, pipeline, motor de preços, simulador, ou apenas interface
humana.

## Onde ficam os resultados

Toda a interpretação com conteúdo real (nomes de aba/campo, fórmulas
específicas, valores, parâmetros) fica exclusivamente em
`data/restricted/audit/` (zona local, ignorada pelo Git — ver
[[04-DECISIONS]] D6). Este documento público registra apenas o
método, nunca o resultado da interpretação em si.
