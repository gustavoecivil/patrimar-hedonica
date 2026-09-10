# 03 — Roadmap

## Fase atual

**FASE 3D — Fechamento forense das ambiguidades e regras.**
Executada em 2026-09-10 (ver [[05-WORKLOG]] e
[[17-AMBIGUITY-RESOLUTION-METHOD]]). Investigação forense das
ambiguidades que bloquearam a Fase 3C, usando primeiro toda a
evidência disponível nas fontes originais (fórmula real, identidades
aritméticas, valores já calculados pela própria fonte), nunca
ajustando um resultado para "bater" contra o preço de referência.
**Resultado: `MATHEMATICAL_REPRODUCTION_CONFIRMED` —**
`NEAR_EXACT_WITH_EXPLAINED_ROUNDING`, 884/884 unidades reproduzidas
independentemente, dentro de 1 centavo do preço já existente na
fonte, sem nenhum acesso ao preço de referência durante o cálculo.
Um dos dois bloqueios centrais da Fase 3C era, na verdade, um
**defeito de software** (uma consulta que não isolava corretamente
partes distintas da mesma fonte) — corrigido no código público, sem
alterar nenhum dado. O outro bloqueio (uma tabela de calibração nunca
antes capturada) foi resolvido reconstruindo-a inteiramente a partir
da fórmula real, com um mecanismo genérico reutilizável (nunca uma
fórmula real hardcoded). `BUSINESS_SEMANTICS_CONFIRMED` permanece
parcial — 2 perguntas objetivas, em português simples, preparadas
para consulta futura a quem forneceu a planilha (nunca enviadas
automaticamente). Motor genérico
(`scripts/pricing_reproduction_engine.py`) ganhou 2 capacidades
novas testadas com dados 100% fictícios (busca por chave composta;
valor padrão explicitamente evidenciado para uma chave ausente
específica). Todas as tentativas anteriores preservadas como
histórico, nunca sobrescritas. Banco de teste sintético (Fase 2C)
confirmado intacto ao final.

**FASE 3C — Reprodução independente da lógica de precificação.**
Executada em 2026-09-10 (ver [[05-WORKLOG]] e
[[16-INDEPENDENT-PRICING-REPRODUCTION]]). Tentativa de reproduzir,
fora do Excel, os preços já importados (Fase 3B) a partir das
unidades/parâmetros/calibrações reais já promovidos — sem calcular
nada por hipótese e sem nunca deixar o motor de cálculo acessar o
preço de referência antes de terminar. Resultado:
**`PARTIAL_REPRODUCTION`** — uma regra de calibração (busca por chave
derivada) foi reproduzida de ponta a ponta com evidência de fórmula e
dado real, mas o preço final de todas as unidades permanece bloqueado
por duas lacunas de disponibilidade de dado, não de compreensão da
metodologia: uma tabela de calibração adicional nunca foi capturada
nas fases anteriores, e um componente de área não pôde ser confirmado
com confiança suficiente (tentativa registrada e retratada — nunca um
filtro inventado para "fazer funcionar"). Extensão mínima e aditiva ao
schema v2 (`database/v2/010_reproduction.sql`) para distinguir
formalmente resultado importado de resultado calculado
(`REPRODUCTION_VALIDATION_RUN`, ver [[04-DECISIONS]] D11/D12) — sem
quebrar nenhum dado sintético já existente, reconfirmado. Nenhum
preço foi promovido a produção/recomendação; `REFERENCE_ALLOCATION_V1`
não foi usado sobre dado real. Teste público sintético
(`scripts/test_pricing_reproduction_engine.py`) prova a arquitetura
genérica do motor — grafo, bloqueio transitivo, isolamento do preço de
referência, determinismo — usando somente regras fictícias. Banco de
teste sintético (Fase 2C) confirmado intacto ao final.

**FASE 3B — Mapeamento controlado de staging para core/pricing.**
Executada em 2026-09-09 (ver [[05-WORKLOG]] e
[[15-STAGING-TO-CANONICAL-PROMOTION]]). Os candidatos de staging com
confiança `HIGH` (Fase 3A) foram promovidos para `core.*`/`pricing.*`
no mesmo banco privado dedicado — 2 desenvolvimentos, 5 torres, 2
tipologias, 884 unidades, 4 parâmetros, 29 entradas de calibração e
884 resultados de preço **importados** (nunca calculados pelo novo
sistema — marcados explicitamente `result_origin='IMPORTED_REFERENCE'`,
`run_type='IMPORTED_REFERENCE_RUN'`, ver [[04-DECISIONS]] D11).
Extensão mínima e aditiva ao schema v2
(`database/v2/009_promotion.sql`) para suportar essa distinção,
lineage por entidade, e idempotência — sem quebrar nenhum dado
sintético já existente (Fases 2B/2C, reconfirmado). Reconciliação
privada entre os resultados importados e o VGV já presente na fonte
fechou com diferença de centavos, explicável por arredondamento.
Alguns candidatos `HIGH` não foram promovidos por terem valor vazio na
extração (achado real, não corrigido por invenção — permanecem
staged) ou por ausência genuína de dado na fonte (2 entradas de
calibração). Nenhum preço foi calculado; `REFERENCE_ALLOCATION_V1` não
foi executado sobre dado real; nenhum item `MEDIUM`/`LOW` foi
promovido. Teste público sintético
(`scripts/test_promote_staging_to_core.py`) prova o pipeline completo
— incluindo detecção de duplicidade e rollback com marcação `FAILED`
— usando somente dados fabricados. Banco de teste sintético
(`patrimar_pricing_v2_test`, Fase 2C) confirmado intacto ao final.

**FASE 3A — Ingestão controlada das planilhas reais em RAW/STAGING
PostgreSQL.**
Executada em 2026-09-09 (ver [[05-WORKLOG]] e
[[14-PRIVATE-DATA-INGESTION]]). As duas planilhas reais recebidas na
Fase 1A/1A.1 foram, pela primeira vez, carregadas para um banco de
dados — um PostgreSQL **local e privado** dedicado
(`patrimar_pricing_v2_private_dev`, totalmente separado do banco de
teste sintético — ver [[04-DECISIONS]] D10), preservando fidelidade
total (valor, fórmula, tipo original, separados) em dois schemas
genéricos (`raw`/`staging`, `database/v2/008_ingestion.sql`), sem
inserir nenhuma linha em `core`/`pricing`/`market`. Reconciliação
estrutural exata contra a auditoria da Fase 1B; amostragem
determinística de fidelidade sem divergência; idempotência por
SHA-256 confirmada (reingestão do mesmo arquivo não duplica nada);
mapeamento de campos classificado por confiança (`HIGH` convertido
automaticamente para candidato de staging, `MEDIUM`/`LOW` só entram
em revisão, nunca convertidos automaticamente); avaliação de chave
candidata com evidência real; comparação estrutural entre os dois
workbooks. Teste público sintético
(`scripts/test_ingest_xlsx_postgres.py`) prova o pipeline completo —
incluindo reversão de transação e marcação `FAILED` — usando somente
um workbook fabricado em memória. Nenhum preço foi calculado ou
reproduzido; nenhuma constraint definitiva foi criada em `core`;
nenhum conteúdo privado apareceu em nenhum artefato público. Banco de
teste sintético (`patrimar_pricing_v2_test`, Fase 2C) confirmado
intacto ao final.

**FASE 2C — Execução real do schema v2 em PostgreSQL isolado.**
Executada em 2026-09-09 (ver [[05-WORKLOG]] e
[[13-POSTGRESQL-V2-RUNTIME-VALIDATION]]). O schema v2 (Fase 2) e o
seed sintético (Fase 2B) foram, por fim, executados de verdade — não
mais só validados por parser — contra um PostgreSQL 18 real, local e
isolado (banco `patrimar_pricing_v2_test`, já pré-existente no
ambiente, nenhuma instalação nova necessária). DDL aplicado sem erro;
inventário real (schemas/tabelas/FKs/constraints/índices) confirmado
via `information_schema`/`pg_catalog`, não só pelo parser Python;
seed aplicado (391 `INSERT`s); VGV validado por SQL puro; view
`pricing.v_unit_price_current` validada; rastreabilidade completa de
uma unidade sintética reconstruída via SQL; 7 tentativas de inserção
inválida corretamente rejeitadas pelo banco; histórico preservado
entre duas runs; determinismo confirmado de ponta a ponta (hash
lógico recalculado a partir do banco idêntico ao hash do motor
Python), inclusive após recriar o ambiente do zero duas vezes. Dois
defeitos reais (só detectáveis em execução real) foram encontrados e
corrigidos no código público/sintético — ver
[[13-POSTGRESQL-V2-RUNTIME-VALIDATION]] para o detalhe. Nenhum dado
privado, `database/schema.sql` (legado), Netlify ou frontend foi
tocado; o banco de teste permanece ativo para a próxima fase.

**FASE 2B — Seed sintético e prova end-to-end do Unit Price
Allocation Engine.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Provado que o schema v2
(Fase 2) representa um ciclo completo de distribuição de VGV entre
unidades usando um algoritmo de referência público e 100% sintético
(`REFERENCE_ALLOCATION_V1`, ver [[12-REFERENCE-ALLOCATION-ENGINE]]) —
**não** a metodologia proprietária da Patrimar. Cenário fictício (1
empreendimento, 2 torres, 4 tipologias, 40 unidades), 2 runs
(`SYSTEM_ONLY` e `WITH_OVERRIDE`), fechamento exato do VGV-alvo,
override com impacto explícito no VGV, e determinismo confirmado por
hash SHA-256 idêntico entre execuções. `scripts/validate_db_v2.py`
estendido para validar o seed SQL gerado contra o DDL. Nenhum
PostgreSQL real foi usado (não disponível no ambiente); nenhum dado
privado foi incorporado; `database/schema.sql` (legado), Netlify,
frontend e modelo OLS não foram tocados.

**FASE 2 — Desenho do schema canônico PostgreSQL v2.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Traduzido em schema
físico o modelo conceitual da Fase 1D, priorizando o Unit Price
Allocation Engine (Motor B — 12 tabelas em `pricing`, schema completo,
evidenciado por fórmula na Fase 1C) e criando apenas a fundação mínima
extensível do Market Pricing Engine (Motor A — 3 tabelas em `market`,
sem comparáveis/transações/ofertas, por falta de fonte real). Ver
[[11-DATABASE-V2-DESIGN]] para a documentação pública (decisões de
modelagem, estratégia de migração do legado, sem conteúdo privado).
Todo o DDL vive em `database/v2/`, em schemas próprios (`core`,
`pricing`, `audit`, `market`) — `database/schema.sql` (legado)
**não foi alterado** e continua em uso. Nenhuma migração de dado real
ou sintético foi executada; nenhum banco de produção, Netlify,
frontend ou modelo OLS foi tocado. Validação do DDL feita
estruturalmente (`scripts/validate_db_v2.py`, sem PostgreSQL/Docker
disponíveis no ambiente), com teste de fumaça sintético.

**FASE 1D — Gap analysis e modelo canônico preliminar.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). A partir da lógica de
precificação reconstruída na Fase 1C, formalizada a decisão
arquitetural de separar **Market Pricing Engine** (Motor A — estima
valor de mercado) e **Unit Price Allocation Engine** (Motor B —
distribui um VGV/preço-base entre unidades) — ver [[04-DECISIONS]] D7
e [[10-PRICING-DOMAIN-MODEL]]. Produzida taxonomia de domínios, gap
analysis, matriz de variáveis de precificação, backlog de aquisição
de dados, e um modelo canônico preliminar (entidades/relações/
histórico/versionamento/overrides, sem SQL) — todos privados em
`data/restricted/audit/`, sem conteúdo proprietário na documentação
pública. Nenhum schema físico foi criado, nenhuma migration escrita,
nenhum banco alterado, nenhum frontend/Netlify/modelo OLS tocado.

**FASE 1C — Engenharia reversa da lógica de precificação.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Reconstruído, com
evidência de fórmula (nunca por suposição), o fluxo de cálculo de
preço presente nas duas planilhas recebidas: entradas, parâmetros,
buscas/lookups, ajustes, agregações, e o(s) ponto(s) de override
humano sobre o preço final. Criada a ferramenta genérica
`scripts/analyze_pricing_logic.py` (reaproveitando
`scripts/audit_xlsx.py`, ainda sem dependência externa) com teste de
fumaça sintético. Toda a interpretação com conteúdo real (fórmulas,
parâmetros, valores, nomes de aba/campo) ficou exclusivamente em
`data/restricted/audit/` — ver [[09-PRICING-LOGIC-REVERSE-ENGINEERING]]
para a metodologia pública, sem conteúdo privado. Não foi desenhado
banco definitivo, migrado dado nenhum, nem alterado frontend/modelo/
API/Netlify.

**FASE 1B — Auditoria estrutural das planilhas do Rodolfo.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Criada a ferramenta
genérica `scripts/audit_xlsx.py` (biblioteca padrão do Python, sem
dependência externa nova) e seu teste de fumaça com dados sintéticos
(`scripts/test_audit_xlsx.py`). Os dois workbooks recebidos na Fase
1A.1 foram auditados estruturalmente (abas, campos, fórmulas,
dependências entre abas, conteúdo oculto, qualidade de dados,
comparação entre os dois workbooks). Todos os resultados (incluindo
qualquer nome real de aba/campo) ficam exclusivamente em
`data/restricted/audit/` — ver [[08-SPREADSHEET-AUDIT-METHOD]] para a
metodologia pública, sem conteúdo privado. Nenhuma interpretação de
regra de negócio, conversão de formato, ou importação para banco foi
feita nesta fase.

**FASE 0.5 — Congelamento do legado e fundação segura.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Criou tag local do legado
(`legacy-hedonica-pre-rebuild-20260909` → `7dd1d24`), a branch
`rebuild/pricing-intelligence` (ponto de partida da nova plataforma),
`.gitignore` (incluindo a zona restrita `data/restricted/` — ver
[[04-DECISIONS]] D6) e versionou a documentação da Fase 0. Nenhum
modelo, banco, frontend, função Netlify ou dado foi alterado.

**FASE 0 — Auditoria, inventário e documentação do legado.**
Iniciada e concluída em 2026-09-09 (ver [[05-WORKLOG]]). Nenhuma
implementação nova foi feita nesta fase; apenas leitura, execução segura
de teste local, e criação da documentação canônica em `docs/`.

## Fases futuras (registradas como plano, NÃO implementadas)

As fases abaixo são **hipótese/plano**, não compromisso de cronograma, e
não foram iniciadas. Ordem sugerida, sujeita a revisão:

1. **Auditoria das planilhas do Rodolfo** — levantar quais planilhas
   existem, o que contêm, qualidade e cobertura dos dados, e o que pode
   ser migrado para o repositório/banco. Qualquer planilha original
   trazida para o ambiente de trabalho deve ser salva em
   `data/restricted/` (zona restrita, ignorada pelo Git — ver
   [[04-DECISIONS]] D6), nunca na raiz de `data/` nem em nenhum outro
   caminho versionado. **Status:** recepção (Fase 1A/1A.1), auditoria
   estrutural (Fase 1B), engenharia reversa da lógica de precificação
   (Fase 1C), gap analysis/modelo canônico preliminar (Fase 1D),
   desenho do schema PostgreSQL v2 (Fase 2), prova end-to-end com
   dados sintéticos (Fase 2B), execução real em PostgreSQL isolado
   (Fase 2C), ingestão controlada das duas planilhas reais para
   RAW/STAGING (Fase 3A), promoção controlada de staging para
   core/pricing (Fase 3B), reprodução independente da lógica de
   precificação (Fase 3C) e fechamento forense das ambiguidades
   (Fase 3D, resultado `NEAR_EXACT_WITH_EXPLAINED_ROUNDING`,
   `MATHEMATICAL_REPRODUCTION_CONFIRMED`) concluídos. Da lista
   original de perguntas para quem forneceu a planilha, duas
   bloqueavam decisão de schema e foram resolvidas modelando para a
   incerteza (ver [[11-DATABASE-V2-DESIGN]]); a Fase 3D reduziu o
   restante a uma shortlist de 2 perguntas objetivas de negócio
   (`BUSINESS_SEMANTICS_CONFIRMED` parcial — ver
   [[17-AMBIGUITY-RESOLUTION-METHOD]]), ainda pendentes de validação
   humana, ver `data/restricted/audit/questions-for-rodolfo.md`.
2. **Dicionário de dados** — formalizar e expandir
   [[07-DATA-DICTIONARY]] cobrindo também os dados a importar das
   planilhas.
3. **RAW / STAGING / CORE** — camadas de dados para ingestão bruta,
   tratamento e modelo de domínio limpo, substituindo o CSV sintético
   único atual. **Status:** `core` já existe como schema físico desde
   a Fase 2 (`database/v2/002_core.sql`); `raw`/`staging` também já
   existem como schema físico desde a Fase 3A
   (`database/v2/008_ingestion.sql`) e já receberam as duas planilhas
   reais num banco privado dedicado — ver [[14-PRIVATE-DATA-INGESTION]].
   A promoção de `staging` para `core`/`pricing` (Fase 3B) já foi
   feita para os candidatos `HIGH` — ver
   [[15-STAGING-TO-CANONICAL-PROMOTION]]. A Fase 3C tentou reproduzir
   a lógica real de forma independente (`PARTIAL_REPRODUCTION`) e a
   Fase 3D fechou as ambiguidades que bloqueavam isso — resultado
   `NEAR_EXACT_WITH_EXPLAINED_ROUNDING`, com
   `MATHEMATICAL_REPRODUCTION_CONFIRMED` (ver
   [[17-AMBIGUITY-RESOLUTION-METHOD]]). Os resultados reproduzidos
   ainda vivem só no banco privado, num run de validação — nenhum foi
   promovido a produção/recomendação.
4. **PostgreSQL/PostGIS** — evoluir o schema atual (`database/schema.sql`)
   para suportar dados geoespaciais reais (hoje `developments` já tem
   `latitude`/`longitude` como `NUMERIC`, mas não há extensão PostGIS
   nem índices espaciais). O schema v2 (`database/v2/`, Fase 2)
   também tem `core.developments.latitude`/`longitude` como `NUMERIC`
   simples — PostGIS continua não implementado em nenhum dos dois.
5. **Parâmetros** — parametrização de premissas de negócio (ex.: tabelas
   de referência, faixas de mercado) fora do código.
6. **Dados públicos** — incorporar fontes públicas adicionais (IPEAD,
   Secovi, ABRAINC/Fipe, etc., já citadas em `MODEL.md` como calibração,
   não como dados diretos).
7. **Comparáveis** — módulo de seleção/análise de comparáveis de
   mercado. Domínio do Market Pricing Engine (Motor A, ver
   [[04-DECISIONS]] D7); confirmado na Fase 1C que nenhum mecanismo
   desse tipo existe na metodologia atual de alocação interna.
8. **Modelo hedônico (evolução)** — avaliar efeitos fixos de
   empreendimento, tempo, seleção de estoque e política de desconto,
   conforme já apontado como limitação em `MODEL.md`.
9. **Modelos concorrentes** — comparar o modelo hedônico OLS com
   abordagens alternativas (ex. árvores, regularização).
10. **Motor de preços** — desde a Fase 1D, formalmente dois motores
    (ver [[04-DECISIONS]] D7 e [[10-PRICING-DOMAIN-MODEL]]): Market
    Pricing Engine (estimativa de valor de mercado, apenas fundação
    física mínima desde a Fase 2 — `database/v2/005_market_foundation.sql`)
    e Unit Price Allocation Engine (distribuição do VGV entre
    unidades — reconstruído com evidência na Fase 1C, schema físico
    completo desde a Fase 2 — `database/v2/003_pricing.sql`, provado
    de ponta a ponta com algoritmo de referência 100% sintético na
    Fase 2B, e executado com sucesso contra um PostgreSQL real e
    isolado na Fase 2C — ver [[12-REFERENCE-ALLOCATION-ENGINE]] e
    [[13-POSTGRESQL-V2-RUNTIME-VALIDATION]]). Resultados de preço
    reais já existem no schema (Fase 3B), mas todos marcados
    `result_origin='IMPORTED_REFERENCE'` — importados da fonte, nunca
    calculados pelo sistema (ver [[04-DECISIONS]] D11 e
    [[15-STAGING-TO-CANONICAL-PROMOTION]]). A Fase 3C tentou produzir
    o primeiro resultado `SYSTEM_CALCULATED` real de forma
    independente (`PARTIAL_REPRODUCTION`) e a Fase 3D fechou as
    ambiguidades que bloqueavam o preço final — 884/884 unidades
    reproduzidas independentemente dentro de 1 centavo do preço já
    existente na fonte (`NEAR_EXACT_WITH_EXPLAINED_ROUNDING`, ver
    [[17-AMBIGUITY-RESOLUTION-METHOD]] e [[04-DECISIONS]] D12/D13).
    `BUSINESS_SEMANTICS_CONFIRMED` permanece parcial — 2 perguntas de
    negócio ainda pendentes em
    `data/restricted/audit/questions-for-rodolfo-final.md`. Nenhum
    resultado foi promovido a produção/recomendação nesta fase.
11. **Simulador** — evoluir a "Calculadora" atual (client-side, sessão
    única) para um simulador robusto e auditável.
12. **Painel** — evoluir as abas atuais de `index.html` para um painel
    de acompanhamento completo.
13. **Agentes** — agentes de IA operando sobre a base de dados e modelos
    (ex.: automatizar reprecificação, alertas, relatórios).
14. **Lessons learned** — consolidar aprendizados continuamente em
    [[06-LESSONS-LEARNED]] à medida que as fases avançam.

## Regras para avançar de fase

Nenhuma fase futura deve ser iniciada sem que [[04-DECISIONS]] e este
roadmap sejam atualizados primeiro, e sem que o estado local esteja
limpo (`git status`) antes de começar. Qualquer agente que comece uma
nova fase deve atualizar [[05-WORKLOG]] e [[99-HANDOFF]] ao final da
sessão de trabalho.
