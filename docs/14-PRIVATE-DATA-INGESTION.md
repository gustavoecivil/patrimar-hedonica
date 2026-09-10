# 14 — Ingestão Controlada de Dados Privados (RAW/STAGING)

Metodologia pública da Fase 3A. Nenhum conteúdo privado (nome de
arquivo, nome de aba, nome de empreendimento, identificador de
unidade, parâmetro, preço, VGV, valor, fórmula, hash privado) é
reproduzido aqui — ver [[04-DECISIONS]] D4/D6. Os números agregados
abaixo descrevem a metodologia e seus resultados de forma sanitizada;
o conteúdo real vive exclusivamente em `data/restricted/` (local,
`.gitignore`) e num banco PostgreSQL privado dedicado.

## Objetivo

Antes desta fase, as duas planilhas reais recebidas de Rodolfo
(Fase 1A/1A.1) só existiam como arquivo no disco, auditadas
estruturalmente (Fase 1B) e com a lógica de precificação reconstruída
por leitura de fórmula (Fase 1C) — nunca haviam sido carregadas para
um banco de dados. A Fase 3A ingere esses dois arquivos, de forma
controlada, auditável e reprocessável, num PostgreSQL **local e
privado**, preservando fidelidade total — sem, em nenhum momento,
calcular preço, promover dado para as camadas de domínio
(`core`/`pricing`/`market`), ou expor conteúdo privado num artefato
público.

## Duas camadas, dois propósitos

`database/v2/008_ingestion.sql` cria dois schemas genéricos — o DDL
em si não contém nenhum nome de arquivo, de aba, de campo ou valor
específico; esses só existem como **linhas** de um banco privado.

### `raw.*` — fidelidade total, nunca transformada

- `raw.ingest_batches` — uma execução do pipeline. Estados:
  `PENDING` → `RUNNING` → `COMPLETED` **ou** `FAILED`. Nunca existe
  um estado "parcialmente concluído" silencioso — se a transação de
  ingestão falha, o batch é explicitamente marcado `FAILED` numa
  instrução separada e autocommitada, porque o próprio registro do
  batch é criado e commitado **antes** do bloco de risco (a
  transação de dados) — assim ele sobrevive a um rollback e pode de
  fato ser marcado como falho.
- `raw.workbooks` — um arquivo-fonte ingerido, identificado
  globalmente por `source_sha256` (`UNIQUE`). A mesma versão exata de
  um arquivo nunca é ingerida duas vezes — reingerir o mesmo hash
  resulta em `ALREADY_INGESTED`, sem duplicar nenhuma linha. Uma nova
  versão (hash diferente) coexiste historicamente com a anterior.
- `raw.sheets` — uma aba de um workbook.
- `raw.cells` — uma célula preenchida (células vazias não são
  gravadas). Preserva **separadamente** `raw_value` (valor literal),
  `cached_value` (resultado cacheado de uma fórmula) e
  `formula_expression` (texto da fórmula) — uma fórmula nunca é
  reduzida ao seu resultado. Essa separação foi essencial na prática:
  uma coluna de identificador de linha, que parecia ser digitada
  manualmente, revelou-se majoritariamente **derivada por fórmula de
  incremento** (só a primeira linha de cada sequência é um valor
  literal) — sem preservar `cached_value` ao lado de `raw_value`,
  esse dado ficaria invisível para qualquer extração posterior.

### `staging.*` — candidatos normalizados, com confiança e rastreabilidade

- `staging.unit_candidates`, `staging.parameter_candidates`,
  `staging.calibration_candidates`, `staging.price_output_candidates`
  — candidatos normalizados, cada um com `mapping_confidence`
  (`HIGH`/`MEDIUM`/`LOW`) e `mapping_status`
  (`CANDIDATE`/`REVIEW_REQUIRED`/`REJECTED`).
- `staging.mapping_review` — catálogo de campos cujo significado
  permanece ambíguo (`MEDIUM`/`LOW`) ou não mapeado
  (`UNMAPPED`/`REVIEW_REQUIRED`). Esses dois resultados são
  considerados **saídas válidas** do processo, não uma falha —
  "não inventar significado" é uma regra explícita desta fase.
- Toda linha de `staging.*` referencia `source_workbook_id` e
  `source_sheet_id` (e, quando aplicável, `source_row`/
  `source_cell_ref`), resolvendo de volta a uma linha real de
  `raw.*`. Nenhuma linha de staging órfã é aceita.
- Nenhuma linha é inserida em `core.*`/`pricing.*`/`market.*` nesta
  fase — a promoção de staging para essas camadas é escopo de uma
  fase futura (Fase 3B).

## Confiança do mapeamento (HIGH / MEDIUM / LOW)

O "de-para" entre o layout real de cada planilha e os conceitos
canônicos é um arquivo JSON **exclusivamente privado**
(`data/restricted/staging/source-to-canonical-mapping.json`, nunca
versionado), lido em tempo de execução por uma ferramenta genérica —
o script nunca tem nomes reais escritos no código. Cada entrada
recebe um nível de confiança:

- **HIGH** — mapeamento confirmado por evidência de fórmula/cabeçalho
  cruzado com a Fase 1B/1C. Convertido automaticamente para uma
  tabela de candidatos.
- **MEDIUM** — mapeamento plausível, mas sem confirmação direta (ex.:
  inferido por analogia com outro workbook, sem cabeçalho de texto
  confirmável naquele workbook específico). Só entra em
  `staging.mapping_review` como `REVIEW_REQUIRED` — nunca é
  convertido automaticamente para um candidato.
- **LOW** — papel do campo desconhecido, sem evidência de uso em
  nenhuma fórmula de resultado. Registrado em
  `staging.mapping_review` como `UNMAPPED`. Nunca convertido
  automaticamente.

## Idempotência e reprocessamento

A chave de idempotência é o SHA-256 do arquivo, não o nome do arquivo
nem metadados de sistema de arquivos. Reingerir exatamente o mesmo
arquivo é detectado e ignorado (`ALREADY_INGESTED`), confirmado nesta
fase contra um PostgreSQL real, duas vezes: uma vez como parte da
prova de conceito, e uma segunda vez como verificação final dedicada
— em ambos os casos, zero linhas novas em `raw.*`. Uma nova versão do
mesmo arquivo (conteúdo diferente ⇒ hash diferente) não é bloqueada —
coexiste historicamente com a versão anterior, permitindo comparação
entre versões no futuro.

## Validação de fidelidade

Depois de ingerir, dois tipos de verificação foram feitos contra o
PostgreSQL privado (nunca contra um ambiente público):

1. **Reconciliação estrutural** — contagem de workbooks/abas/
   células/fórmulas persistidos comparada, campo a campo, contra o
   inventário estrutural já produzido na Fase 1B. Reconciliação
   esperada: exata, salvo diferença explicável e documentada.
2. **Amostragem determinística de fidelidade** — um subconjunto fixo
   de células, escolhido por uma regra determinística (não aleatória,
   para ser reprodutível), comparado célula a célula entre o arquivo
   original e o banco: tipo, valor (ou fórmula, quando aplicável).
   Qualquer divergência seria motivo de bloqueio da fase; os valores
   em si nunca são reproduzidos em nenhum documento público — apenas
   a contagem de células verificadas e de divergências encontradas.

## Qualidade de dados (privada, nunca corrigida silenciosamente)

A ingestão registra, mas nunca corrige automaticamente, sinais de
qualidade como: identificador de negócio ausente, valores duplicados,
área ausente, tipo inconsistente numa coluna, possível duplicidade de
unidade, parâmetro sem definição clara, resultado de preço sem unidade
relacionada, mapeamento ambíguo, e registro sem linhagem completa.
Esses sinais — e sua evidência — ficam exclusivamente no banco
privado e em artefatos privados dedicados
(`data/restricted/audit/staging-profile.csv`,
`data/restricted/audit/ingestion-validation.md`), nunca resumidos com
conteúdo real em nenhum documento público.

## Avaliação de chave candidata

Antes de qualquer decisão de chave física em `core.*`, esta fase
avaliou, com evidência real (cobertura, unicidade, colisões, nulos),
se um identificador de negócio isolado é suficiente como chave dentro
de um development, ou se uma chave composta (ex.: development + torre
+ identificador) é necessária. Nenhuma constraint `UNIQUE` nova foi
criada em `core.*` nesta fase — essa avaliação só produz evidência
para uma decisão futura de schema, já antecipada estruturalmente
desde a Fase 2 (`UNIQUE(development_id, tower_id, unit_code)`, nunca
`unit_code` isolado).

## Reconciliação entre workbooks

Quando mais de um workbook real é ingerido, esta fase compara os dois
por **estrutura e conteúdo** (faixas de valor, contagem de
subdivisões internas, metodologia de cálculo evidenciada) — nunca
apenas por nome de arquivo ou data de modificação, que não provam
nada sobre a relação real entre dois arquivos. A conclusão dessa
comparação (mesma metodologia/planilha-modelo aplicada a
empreendimentos diferentes, versões diferentes do mesmo
empreendimento, ou nenhuma relação identificável) fica registrada
privadamente, com o nível de confiança da conclusão.

## Privacidade — o que nunca aparece em saída pública

Nenhuma saída pública desta fase (este documento, o DDL, os scripts,
o teste sintético) contém: nomes de arquivo; nomes reais de aba;
nomes de empreendimento; identificadores de unidade; parâmetros;
preços; VGV; valores; fórmulas; hashes privados. O único lugar onde
esse conteúdo pode existir é como **linha** de um banco de dados
PostgreSQL local e privado (`patrimar_pricing_v2_private_dev`, ver
[[04-DECISIONS]]), nunca em schema/DDL/código versionado, nunca em
dump ou export salvo em caminho público.

## Teste público sintético

`scripts/test_ingest_xlsx_postgres.py` prova o pipeline completo
usando exclusivamente um workbook `.xlsx` **fabricado em memória**
(nunca um arquivo real): ingestão bruta com fidelidade total
(incluindo uma célula-fórmula com `cached_value` separado do
`raw_value`, a mesma classe de estrutura encontrada nos dados reais),
idempotência/detecção de fonte duplicada, `stage` populando
candidatos `HIGH` em todas as categorias e `staging.mapping_review`
para `MEDIUM`/`LOW`, ausência de linhas de staging órfãs, e — mais
importante — que uma transação de ingestão que viola uma constraint
do banco é revertida pelo próprio PostgreSQL e o batch correspondente
termina `FAILED`, nunca "parcialmente concluído". Executado contra um
PostgreSQL real neste ambiente.

## Ferramenta

`scripts/ingest_xlsx_postgres.py` — dois subcomandos:

- `ingest-raw` — lê um ou mais `.xlsx` e grava fidelidade total em
  `raw.*`. Reaproveita o parser de `scripts/audit_xlsx.py` (biblioteca
  padrão apenas, sem dependência nova). Suporta `--dry-run` (nenhuma
  escrita, só contagem). Conecta a PostgreSQL exclusivamente via
  `psql` (sem `psycopg2`, indisponível no ambiente) e variáveis de
  ambiente padrão do libpq — nunca recebe nem contém credencial no
  código.
- `stage` — lê `raw.*` já ingerido e um arquivo de mapeamento (privado,
  passado por argumento — nunca hardcoded), populando `staging.*`
  segundo a regra de confiança acima.

Ambos: fail-fast, ingestão em transação única quando aplicável, sem
caminho absoluto hardcoded, logs que nunca imprimem valor de célula
por padrão.

## O que esta fase explicitamente NÃO fez

- Não calculou nenhum preço, nem reproduziu nenhum resultado das
  planilhas originais como se fosse um cálculo do sistema.
- Não inseriu nenhuma linha em `core.*`/`pricing.*`/`market.*`.
- Não usou `REFERENCE_ALLOCATION_V1` (D8) sobre dado real.
- Não criou nenhuma constraint `UNIQUE` definitiva em `core.*`.
- Não promoveu nenhum candidato `MEDIUM`/`LOW` automaticamente.

Essas decisões ficam para a Fase 3B (mapeamento staging → core/
pricing), que depende também das perguntas ainda pendentes em
`data/restricted/audit/questions-for-rodolfo.md`.
