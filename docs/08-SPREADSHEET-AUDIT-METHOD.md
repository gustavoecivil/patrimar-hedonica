# 08 — Metodologia de Auditoria Estrutural de Planilhas

Este documento descreve **apenas a metodologia** usada para auditar
estruturalmente workbooks XLSX privados recebidos de fontes externas
(ex.: planilhas de Rodolfo/Patrimar). **Não contém** nomes de arquivo,
nomes de empreendimento, nomes reais de abas/campos, valores, hashes
ou qualquer conteúdo proveniente das planilhas — ver
[[04-DECISIONS]] D4/D6.

## Objetivo

Entender a estrutura de um ou mais workbooks XLSX (abas, campos,
fórmulas, dependências, conteúdo oculto, qualidade dos dados) antes de
qualquer conversão, importação para banco de dados, ou interpretação
de regra de negócio — sem nunca expor o conteúdo privado fora da zona
restrita local (`data/restricted/`).

## Ferramenta

`scripts/audit_xlsx.py` — utilitário de linha de comando, escrito em
Python usando exclusivamente a biblioteca padrão (`zipfile` +
`xml.etree.ElementTree`, já que um `.xlsx` é um pacote OOXML, isto é,
um zip de arquivos XML). Não foi adicionada nenhuma dependência
externa ao projeto: nenhuma biblioteca de leitura de Excel (ex.
`openpyxl`) estava disponível no ambiente, e o volume/complexidade do
que precisava ser lido (metadados estruturais, não os valores de
negócio em si) não justificou a adição de uma dependência nova.

Uso:

```bash
python scripts/audit_xlsx.py \
  --input <arquivo1.xlsx> [--input <arquivo2.xlsx> ...] \
  --output-dir <diretorio-de-saida> \
  [--workbook-id <id1> --workbook-id <id2> ...]
```

O script não contém nenhum caminho absoluto, nome de arquivo real,
hash ou valor específico de nenhum projeto — tudo isso entra via
argumentos de linha de comando em tempo de execução. Todos os
resultados devem ser gravados exclusivamente dentro de
`data/restricted/` (zona ignorada pelo Git).

Um teste de fumaça (`scripts/test_audit_xlsx.py`) valida a ferramenta
usando dois workbooks **sintéticos**, construídos em memória a partir
de XML mínimo (sem nenhuma biblioteca de terceiros e sem nenhum dado
real), cobrindo: aba oculta, fórmula compartilhada copiada
verticalmente, célula de erro, e correspondência de abas com nome
idêntico entre dois workbooks.

## Cadeia de custódia

Antes e depois de qualquer execução da ferramenta sobre arquivos
recebidos:

1. Recalcula-se o SHA-256 de cada arquivo original.
2. Compara-se com o hash já registrado no manifesto de recebimento
   (ver Fase 1A.1 em [[05-WORKLOG]]).
3. Qualquer divergência interrompe o trabalho imediatamente.

A ferramenta abre os arquivos apenas em modo leitura (`zipfile.ZipFile`
em modo `"r"`) e nunca grava sobre o arquivo de entrada.

## O que é levantado (por workbook e por aba)

- Metadados do documento (propriedades, criador, datas).
- Contagem e nomes das abas, com visibilidade (visível / oculta /
  muito oculta).
- Dimensão utilizada, quantidade de linhas/colunas, células
  preenchidas, células com fórmula, células de erro.
- Células mescladas, autofiltro, tabelas estruturadas, congelamento de
  painel (freeze panes), validações de dados, formatação condicional,
  hyperlinks, comentários.
- Linhas e colunas ocultas, nomes definidos ocultos, vínculos
  externos, presença de macros, gráficos e imagens.
- Proteção de workbook/planilha.

## Detecção de tabelas e cabeçalhos

A ferramenta **não assume que a primeira linha é o cabeçalho**. Ela
avalia, entre as primeiras linhas de cada aba, qual delas tem maior
proporção de células de texto, maior unicidade de valores, e é seguida
por linhas predominantemente numéricas/data — combinando esses três
sinais em um escore de 0 a 1, registrado como o nível de confiança da
detecção.

## Perfil de campos

Para cada campo (coluna) sob o cabeçalho detectado, calcula-se: tipo
predominante e tipos encontrados, contagem/percentual de preenchimento,
contagem de valores únicos, indício de duplicidade, presença de
fórmulas, valor constante, min/max/média (numéricos), datas
mínima/máxima, comprimento de texto, mistura de tipos, células de erro,
candidato a chave única (preenchimento total + unicidade total), e
sinais de campo categórico ou campo calculado.

**Nenhum valor de planilha é reproduzido em relatórios públicos.**
Campos cujo nome sugere dado pessoal (nome, CPF, telefone, e-mail
etc.) ou cujos valores casam com padrões de CPF/telefone/e-mail são
marcados apenas como `POTENCIAL_PII=SIM`, sem reproduzir o valor.

## Auditoria de fórmulas

Cada fórmula é normalizada substituindo a parte numérica das
referências de célula por um marcador (`A2` → `A#`), preservando
marcadores de referência absoluta (`$`). Fórmulas que normalizam para
o mesmo padrão dentro de uma aba são agrupadas — isso cobre tanto
fórmulas compartilhadas (`shared formulas` do OOXML) quanto fórmulas
soltas estruturalmente equivalentes. Para cada grupo, registra-se
quantidade de ocorrências, direção de cópia (vertical/horizontal/
mista), se há referência a outra aba, se há referência absoluta e/ou
relativa, e quantas ocorrências do grupo contêm erro (`#REF!` etc.).

## Dependências

A partir das referências a outras abas encontradas nas fórmulas,
constrói-se um grafo de dependência aba → aba (com contagem de
referências), permitindo distinguir abas centrais, abas de parâmetro,
e abas de resultado.

## Conteúdo oculto

Abas ocultas/muito ocultas, linhas e colunas ocultas, e nomes
definidos ocultos são apenas **listados**, nunca tratados como erro
por padrão — cabe a uma análise humana decidir se são intencionais.

## Qualidade dos dados

Heurísticas aplicadas por aba/campo: linhas totalmente vazias no meio
de um intervalo de dados, campos com baixa cobertura de preenchimento,
mistura de tipos numa mesma coluna, células de erro, indício de
duplicidade acima de um limiar, colunas quase constantes, e ausência
de qualquer campo candidato a chave única na aba. Nenhuma correção é
aplicada nesta fase — apenas identificação.

## Comparação entre workbooks

Quando mais de um workbook é auditado na mesma execução, nomes de aba
e nomes de campo são comparados par a par usando similaridade textual
(após normalização: minúsculas, sem acentos/pontuação). A
correspondência é classificada em três níveis de confiança:

- **ALTA** — similaridade ≥ 0.85 (ou nomes idênticos após normalização).
- **MEDIA** — similaridade entre 0.6 e 0.85 (campos) ou 0.6–0.85 (abas).
- **BAIXA** — similaridade menor, ainda registrada para revisão manual.

Nenhuma correspondência é assumida como definitiva nesta fase — a
classificação de confiança existe justamente para deixar isso
explícito.

## Artefatos gerados (privados, nunca commitados)

Todos os artefatos são gravados em `data/restricted/audit/` (zona
ignorada pelo Git — ver [[04-DECISIONS]] D6):

- `workbook_inventory.csv`
- `sheet_inventory.csv`
- `field_profile.csv`
- `formula_inventory.csv`
- `dependency_inventory.csv`
- `hidden_content_inventory.csv`
- `quality_issues.csv`
- `cross_workbook_mapping.csv`
- `structural-audit.md` (resumo narrativo privado)

## Limitações conhecidas desta primeira passada

- A detecção de cabeçalho e de chave candidata é heurística e pode
  errar em planilhas com múltiplos blocos/tabelas numa mesma aba, ou
  com áreas de parâmetro fora do padrão "tabela única por aba" — isso
  é esperado nesta fase estrutural e deve ser refinado manualmente na
  Fase 1C (engenharia reversa da lógica de precificação).
- Fórmulas compartilhadas sem texto próprio (`<f t="shared" si="N"/>`)
  são associadas ao padrão normalizado da fórmula-mestre do grupo; a
  ferramenta não recalcula o deslocamento exato de cada referência
  relativa célula a célula.
- Detecção de PII é heurística (nome de campo + regex sobre uma
  amostra de valores) e deve ser tratada como sinal de atenção, não
  como classificação definitiva de conformidade/LGPD.
