# 17 — Método de Fechamento Forense de Ambiguidades

Metodologia pública da Fase 3D. Nenhum conteúdo privado (fórmula
proprietária, constante, parâmetro real, valor, preço, VGV, nome de
arquivo/aba/campo) é reproduzido aqui — ver [[04-DECISIONS]] D4/D6. Os
números e classificações abaixo descrevem a metodologia e seus
resultados de forma sanitizada; o conteúdo real vive exclusivamente em
`data/restricted/` e num banco PostgreSQL privado dedicado.

## Objetivo

A Fase 3C terminou com resultado `PARTIAL_REPRODUCTION` — parte da
metodologia foi reproduzida, mas o preço final ficou bloqueado por
ambiguidades documentadas. A Fase 3D existe para tentar fechar essas
ambiguidades **usando primeiro toda a evidência já disponível nas
fontes originais**, antes de qualquer recurso a uma pessoa — e para
fazer isso sem jamais ajustar um resultado para "bater" contra o
preço já conhecido.

## Classificação obrigatória de evidência

Toda conclusão desta fase é classificada como:

- **`DIRECT`** — comprovada explicitamente por célula, fórmula,
  cabeçalho ou dependência.
- **`STRUCTURAL`** — comprovada por repetição/padrão estrutural (ex.:
  uma identidade aritmética que fecha em praticamente 100% das
  linhas de um conjunto de dados real).
- **`INFERRED_STRONG`** — inferência necessária, mas apoiada por
  múltiplas evidências independentes.
- **`INFERRED_WEAK`** — hipótese plausível, mas insuficiente.
- **`UNRESOLVED`** — não comprovável com a evidência disponível.

Somente `DIRECT`, `STRUCTURAL` e `INFERRED_STRONG` podem desbloquear
uma regra para reprodução automática. `INFERRED_WEAK` nunca vira
regra executável sem revisão humana explícita — fica registrada como
hipótese, não como fato.

## Controle contra overfitting ao preço de referência

Toda hipótese desta fase foi validada em duas etapas obrigatoriamente
separadas: primeiro, provar `input → regra → fator` **usando somente
a estrutura da própria fonte** (fórmula real, identidade aritmética,
valor cacheado pela própria planilha) — nunca olhando o preço final
durante essa prova. Só depois de uma hipótese estar comprovada dessa
forma é que seu efeito na reprodução é medido. Uma hipótese que só
foi encontrada olhando o preço final para ajustar um valor é
descartada e nunca usada — não existe uma classificação "quase boa o
suficiente" para esse tipo de contaminação.

## Achados desta fase (classe do achado, não o conteúdo)

- Uma ambiguidade que a fase anterior havia atribuído a "dado da
  fonte inconsistente" era, na verdade, um **defeito de software**
  (uma consulta que não isolava corretamente duas partes distintas da
  mesma fonte) — corrigido no código público genérico, sem tocar em
  nenhum dado.
- Uma regra bloqueada por falta de uma tabela nunca antes capturada
  foi resolvida reconstruindo essa tabela inteiramente a partir da
  **fórmula real**, usando um mecanismo genérico e reutilizável de
  extração (não um valor copiado à mão) — nenhuma fórmula real foi
  escrita em código público; o código só sabe *como* interpretar uma
  estrutura desse tipo em geral.
- Um caso de "valor ausente" foi resolvido confirmando, via o próprio
  cálculo já existente na fonte, que o valor correto **é
  zero** — um fato mecânico de como a fonte funciona, não uma
  suposição de negócio.

## Separação matemática vs. semântica de negócio

Mesmo quando a reprodução matemática é bem-sucedida, isso não é
tratado como equivalente a "entendemos o motivo de negócio por trás
de cada decisão". Esta fase distingue explicitamente:

- **`MATHEMATICAL_REPRODUCTION_CONFIRMED`** — o cálculo produz,
  independentemente, o mesmo resultado numérico já existente na
  fonte, dentro de uma tolerância de arredondamento explicada.
- **`BUSINESS_SEMANTICS_CONFIRMED`** — sabemos **por que** a
  metodologia toma cada decisão, não apenas **como** ela calcula.

É possível ter o primeiro sem o segundo — e quando isso acontece, as
perguntas remanescentes são preparadas para consulta humana, nunca
respondidas por suposição.

## Regras para consulta humana

Quando uma ambiguidade permanece `UNRESOLVED` (ou só
`INFERRED_WEAK`) mesmo depois de toda a investigação estrutural
disponível, o processo não continua tentando indefinidamente. Uma
lista curta (no máximo 5, preferencialmente 3 ou menos) de perguntas
é preparada — em linguagem simples, sem jargão técnico — cada uma
explicando o que não se sabe, por que não pôde ser deduzido, e o que
a resposta desbloquearia. Essas perguntas nunca são enviadas
automaticamente a ninguém — apenas preparadas para quando o
responsável do projeto decidir consultar a fonte humana.

## Reprodutibilidade e histórico

Cada nova versão do ruleset privado usado nesta fase declara
explicitamente sua versão-mãe, e cada mudança é registrada com o
problema encontrado, a evidência que o comprova, a mudança feita, e a
métrica antes/depois — nunca um ajuste sem justificativa. Nenhuma
tentativa anterior é apagada; todas continuam auditáveis no banco
privado. O motor de cálculo continua sem nenhum acesso ao preço de
referência durante a fase de cálculo — a mesma separação estrutural
já estabelecida na Fase 3C.

## Engine genérico ampliado (sem nenhuma fórmula real)

`scripts/pricing_reproduction_engine.py` ganhou duas capacidades
genéricas novas nesta fase, ambas testadas com dados 100%
fictícios: busca por **chave composta** (concatenação de dois campos,
equivalente genérico a uma busca horizontal/vertical de planilha com
chave montada por texto) e **valor padrão explicitamente evidenciado
para uma chave específica ausente** (nunca um padrão genérico para
qualquer chave ausente — cada aplicação exige sua própria evidência).
Nenhuma das duas capacidades contém qualquer fórmula, constante ou
nome de campo real.
