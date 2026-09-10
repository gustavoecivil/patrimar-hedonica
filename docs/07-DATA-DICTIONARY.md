# 07 — Data Dictionary

> **Nota (Fase 1D):** este dicionário cobre apenas o schema legado
> (laboratório hedônico sintético). Os domínios conceituais do futuro
> Unit Price Allocation Engine e Market Pricing Engine (ver
> [[10-PRICING-DOMAIN-MODEL]] e [[04-DECISIONS]] D7) ainda não têm
> campos físicos definidos — o mapeamento conceitual completo,
> incluindo referências ao conteúdo real das planilhas privadas
> analisadas, está em `data/restricted/audit/pricing-gap-analysis.csv`
> e `pricing-variable-matrix.csv` (privados). Este documento deve ser
> expandido com campos reais somente quando existirem de fato num
> schema físico — ver a regra de "origem deste dicionário" abaixo.
>
> **Nota (Fase 2/2B):** o schema físico do Unit Price Allocation
> Engine já existe (`database/v2/`, ver [[11-DATABASE-V2-DESIGN]]),
> mas seus campos não estão listados abaixo porque este dicionário é
> especificamente do contrato legado (`v_hedonic_model`/CSV/schema
> `database/schema.sql`). Um cenário 100% sintético e público
> (`fixtures/v2/reference_allocation_scenario.json`, ver
> [[12-REFERENCE-ALLOCATION-ENGINE]]) já popula esse schema v2 para
> fins de prova de conceito — **não é dado real da Patrimar nem
> substitui este dicionário**, que continua descrevendo apenas o
> laboratório hedônico legado.
>
> **Nota (Fase 3A):** os schemas físicos genéricos `raw`/`staging`
> (`database/v2/008_ingestion.sql`) já existem e já receberam as duas
> planilhas reais de Rodolfo, mas seus campos também não estão
> listados abaixo — o DDL é deliberadamente genérico (workbook/aba/
> célula, candidato normalizado com nível de confiança), e qualquer
> nome de campo real correspondente só existe como linha de um banco
> privado, nunca como coluna de schema. Ver [[14-PRIVATE-DATA-INGESTION]].
>
> **Nota (Fase 3B):** candidatos `HIGH` de `staging.*` já foram
> promovidos para linhas reais em `core.developments/towers/
> unit_typologies/units` e `pricing.parameters/calibration_entries/
> unit_price_results` — mas, de novo, nenhum conteúdo real está
> listado abaixo, porque as colunas em si (já documentadas na Fase 2)
> não mudaram. O que mudou foi a adição de colunas de metadado/
> distinção (`result_origin`, `run_type`, `classification`,
> `promoted_entity_id`) — ver [[15-STAGING-TO-CANONICAL-PROMOTION]] e
> [[04-DECISIONS]] D11 (nunca confundir `IMPORTED_REFERENCE` com
> `SYSTEM_CALCULATED`).
>
> **Nota (Fase 3C):** uma tentativa de reprodução independente
> (`pricing.runs.run_type='REPRODUCTION_VALIDATION_RUN'`,
> `pricing.reproduction_comparisons`) já existe no schema e já foi
> executada contra o banco privado — resultado `PARTIAL_REPRODUCTION`,
> sem nenhum resultado `SYSTEM_CALCULATED` real produzido ainda (a
> lógica real é configuração privada, nunca parte deste dicionário —
> ver [[04-DECISIONS]] D12 e [[16-INDEPENDENT-PRICING-REPRODUCTION]]).
>
> **Nota (Fase 3E):** o novo produto (`web/pricing-intelligence/`) usa
> um contrato JSON próprio e público — o mesmo formato em modo DEMO
> (`demo-data.json`, 100% sintético) e modo PRIVATE (servido por
> `scripts/pricing_preview_server.py`). Campos:
> `meta.{mode,algorithm,disclaimer,source}`,
> `development.{name,city,state,bairro}`, `towers[]`, `typologies[]`,
> `kpis.{vgv,units_count,towers_count,typologies_count,avg_price_per_m2,
> adjustments_count,reproduction_accuracy_pct,within_1_cent_count}`,
> `units[].{tower,unit_code,typology,floor,position,private_area_m2,
> uncovered_area_m2,weighted_area_m2,floor_factor,position_factor,
> participation_share,system_price,adjustment,final_price,
> price_per_m2,status}`,
> `validation.{units_analyzed,exact_matches,within_1_cent,mae,
> max_absolute_error,aggregate_delta,classification,note,units[]}`.
> Este contrato descreve apenas a FORMA do dado (nomes de campo,
> tipos) — nunca contém, ele mesmo, nenhum valor real; ver
> [[18-PRICING-INTELLIGENCE-MVP]] e [[19-DEPLOYMENT-AND-DEMO-MODE]].

Somente campos comprovadamente existentes no repositório em 2026-09-09.
Três representações coexistem hoje: o CSV de seed, o schema relacional
(PostgreSQL) e a view de contrato `v_hedonic_model` consumida pela API e
pelo frontend. A tabela abaixo mapeia as três.

## `v_hedonic_model` (contrato da API / frontend) ↔ CSV ↔ schema relacional

| Campo em `v_hedonic_model` / CSV | Tipo (origem SQL) | Coluna/origem relacional | Descrição |
|---|---|---|---|
| `id` | BIGINT | `unit_price_observations.id` | id da observação de preço |
| `empreendimento` | TEXT | `developments.id` | identificador do empreendimento (ex. `NOVO-01`) |
| `apartamento` | TEXT | `units.apartment` | identificador da unidade dentro da torre |
| `bairro` | TEXT | `developments.bairro` | bairro do empreendimento (Belo Horizonte/MG) |
| `torre` | TEXT | `units.tower` | torre (padrão `T1`) |
| `andar` | INTEGER | `units.floor` | pavimento, > 0 |
| `area` | NUMERIC(9,2) | `units.private_area_m2` | área privativa em m² |
| `quartos` | INTEGER | `units.bedrooms` | nº de quartos |
| `vagas` | INTEGER | `units.parking_spaces` | nº de vagas de garagem |
| `suite` | INTEGER | `units.suites` | nº de suítes |
| `varanda_m2` | NUMERIC(8,2) | `units.balcony_area_m2` | área de varanda em m² |
| `cobertura` | 0/1 (CASE) | `units.is_penthouse` (BOOLEAN) | 1 se é cobertura/penthouse |
| `vista` | TEXT | `units.view_type` | `rua` \| `parque` \| `mar` (CHECK) |
| `orientacao` | CHAR(1) | `units.orientation` | `N` \| `S` \| `L` \| `O` (CHECK) |
| `posicao` | TEXT | `units.position_type` | `frente` \| `fundos` \| `lateral` (CHECK) |
| `padrao_score` | NUMERIC(3,1) | `developments.quality_score` | 1–5, índice de padrão construtivo |
| `lazer_score` | NUMERIC(3,1) | `developments.amenities_score` | 1–5, índice de lazer/amenidades |
| `localizacao_score` | NUMERIC(3,1) | `developments.location_score` | 1–5, índice de qualidade de localização |
| `fase_obra` | TEXT | `developments.stage` | `lancamento` \| `construcao` \| `acabamento` \| `pronto` (CHECK) |
| `meses_lancamento` | INTEGER | `unit_price_observations.months_since_launch` | meses desde o lançamento, ≥ 0 |
| `desconto_pct` | NUMERIC(6,2) | `unit_price_observations.discount_pct` | desconto percentual aplicado |
| `preco_m2` | NUMERIC(12,2) | `unit_price_observations.price_m2` | preço por m², > 0 — variável dependente do modelo (em log) |
| `origem` / `p.record_origin` | TEXT | `unit_price_observations.record_origin` | `real` \| `imputed` \| `synthetic` \| `hybrid` (CHECK) |
| `reference_date` | DATE | `unit_price_observations.reference_date` | data de referência da observação |

**Filtro implícito da view:** `v_hedonic_model` só retorna linhas com
`first_sale = TRUE` — ou seja, apenas primeira venda de mercado
primário. Revendas/usados nunca aparecem nessa view por construção.

## Tabelas relacionais adicionais (não expostas diretamente na view)

### `data_sources`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `code` | TEXT UNIQUE | ex. `seed-hybrid-v1` |
| `name` | TEXT | |
| `source_url` | TEXT | opcional |
| `origin_type` | TEXT CHECK | `real` \| `imputed` \| `synthetic` \| `hybrid` |
| `methodology_note` | TEXT | opcional |
| `accessed_at` | TIMESTAMPTZ | opcional |

### `developments` (campos não expostos na view)
`name`, `city` (default `Belo Horizonte`), `state` (default `MG`),
`launch_date`, `completion_date`, `total_floors`, `latitude`,
`longitude`, `source_id` → FK `data_sources.id`.

### `units` (campos não expostos na view)
`source_id` → FK `data_sources.id`. Restrição `UNIQUE
(development_id, tower, apartment)`.

### `unit_price_observations` (campos não expostos na view)
`asking_price`, `transaction_price`, `source_id` → FK `data_sources.id`,
`created_at`. Restrição `UNIQUE (unit_id, reference_date, source_id)`.

## Variáveis derivadas usadas pelo modelo (calculadas em JS, não no banco)

Definidas em `index.html` (`featureRow`, `buildX`), a partir dos campos
acima — não persistidas em nenhuma tabela:
- `ln(preco_m2)` — variável dependente.
- `ln(area)` — log da área privativa.
- Andar centrado no 10º pavimento + termo quadrático desse andar
  centrado.
- Interação andar × vista.
- Índice de qualidade do produto = média de `padrao_score` e
  `lazer_score`.

## Origem deste dicionário

Extraído diretamente de `database/schema.sql` (idêntico à migração
`20260829090000_create_hedonic_schema.sql`), do cabeçalho de
`data/hedonic_seed_hybrid.csv` e da view `v_hedonic_model`. Nenhum campo
listado aqui é hipotético. Campos de fases futuras (ex. dados de
planilhas, comparáveis) devem ser adicionados somente quando existirem
de fato no schema ou nos dados.
