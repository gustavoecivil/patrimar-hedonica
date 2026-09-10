-- Patrimar Pricing Intelligence — Schema canônico v2
-- raw / staging: ingestão controlada e fiel de fontes externas (Fase 3A).
--
-- Este arquivo NÃO contém, e nunca deve conter, nomes de arquivo, nomes
-- de aba/empreendimento, valores, parâmetros ou fórmulas privados —
-- essas coisas só existem em REGISTROS (linhas) de um banco privado
-- (`patrimar_pricing_v2_private_dev`), nunca no DDL versionado. Ver
-- docs/14-PRIVATE-DATA-INGESTION.md.
--
-- raw.*   preserva fidelidade total da fonte (workbook -> aba -> célula,
--         valor + fórmula + tipo original, nunca transformado).
-- staging.* guarda candidatos normalizados derivados de raw.*, com
--         rastreabilidade obrigatória até a célula/linha de origem, e
--         nível de confiança do mapeamento (HIGH/MEDIUM/LOW).
--
-- Nenhuma linha é inserida em core.*/pricing.*/market.* a partir daqui
-- — isso é escopo de uma fase futura (promoção staging -> core).

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;

COMMENT ON SCHEMA raw IS
  'Fidelidade total da fonte original (arquivo -> workbook -> aba -> célula). Nunca transforma, nunca corrige. '
  'Pode conter dado privado nas LINHAS (nunca no schema/nomes de coluna) — só deve existir num banco privado.';
COMMENT ON SCHEMA staging IS
  'Candidatos normalizados derivados de raw.*, com rastreabilidade obrigatória e nível de confiança de mapeamento. '
  'Não é core/pricing — nada aqui é usado por cálculo de preço real ainda.';

-- ---------------------------------------------------------------- raw --

CREATE TABLE raw.ingest_batches (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status         TEXT NOT NULL DEFAULT 'PENDING'
                   CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
  source_count   INTEGER NOT NULL DEFAULT 0 CHECK (source_count >= 0),
  tool_version   TEXT,
  started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at   TIMESTAMPTZ,
  notes          TEXT,
  CONSTRAINT ck_ingest_batches_completed_after_started
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);
COMMENT ON TABLE raw.ingest_batches IS
  'Uma execução do pipeline de ingestão. Se algo falha, o batch fica FAILED — nunca "parcialmente concluído" '
  'silencioso. source_hashes fica em raw.workbooks (uma linha por arquivo), não duplicado aqui.';

CREATE TABLE raw.workbooks (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ingest_batch_id    UUID NOT NULL REFERENCES raw.ingest_batches(id),
  source_filename    TEXT NOT NULL,   -- pode ser privado — só existe como DADO, nunca no DDL
  source_sha256      TEXT NOT NULL,
  source_size_bytes  BIGINT NOT NULL CHECK (source_size_bytes > 0),
  sheet_count        INTEGER,
  ingested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_workbooks_source_sha256 UNIQUE (source_sha256)
);
COMMENT ON TABLE raw.workbooks IS
  'Um arquivo-fonte ingerido. source_sha256 é ÚNICO globalmente — a mesma versão exata de um arquivo nunca é '
  'ingerida duas vezes (idempotência, Fase 3A Passo 7). Uma nova versão (hash diferente) coexiste historicamente.';
COMMENT ON COLUMN raw.workbooks.source_filename IS
  'Nome do arquivo como recebido — pode revelar informação privada (nome de empreendimento). Aceitável aqui '
  'porque esta tabela só existe num banco PRIVADO (nunca no schema/DDL versionado, nunca em dump público).';

CREATE TABLE raw.sheets (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workbook_id    UUID NOT NULL REFERENCES raw.workbooks(id),
  sheet_name     TEXT NOT NULL,        -- idem: privado por natureza, aceitável só neste banco privado
  sheet_index    INTEGER NOT NULL,
  visibility     TEXT NOT NULL DEFAULT 'visible'
                   CHECK (visibility IN ('visible','hidden','veryHidden')),
  dimension_ref  TEXT,
  CONSTRAINT uq_sheets_workbook_name UNIQUE (workbook_id, sheet_name)
);
COMMENT ON TABLE raw.sheets IS 'Uma aba de um workbook ingerido.';

CREATE TABLE raw.cells (
  id                   BIGSERIAL PRIMARY KEY,  -- tabela de fatos de alto volume; sem referência externa a esta PK
  sheet_id             UUID NOT NULL REFERENCES raw.sheets(id),
  cell_ref             TEXT NOT NULL,           -- ex.: 'C5'
  row_number           INTEGER NOT NULL CHECK (row_number > 0),
  column_index          INTEGER NOT NULL CHECK (column_index > 0),
  column_letters       TEXT NOT NULL,
  cell_type            TEXT NOT NULL
                         CHECK (cell_type IN ('string','number','date','boolean','error','empty')),
  raw_value            TEXT,        -- valor literal (não a fórmula) — NULL quando a célula só tem fórmula sem cache
  cached_value         TEXT,        -- valor cacheado (<v> do OOXML) quando a célula tem fórmula
  formula_expression   TEXT,        -- texto da fórmula, quando houver — NUNCA reduzido só ao resultado
  is_shared_formula    BOOLEAN NOT NULL DEFAULT FALSE,
  style_index          INTEGER,
  CONSTRAINT uq_cells_sheet_ref UNIQUE (sheet_id, cell_ref)
);
COMMENT ON TABLE raw.cells IS
  'Uma célula preenchida (não vazias por padrão — ingestão só grava o que tem conteúdo). '
  'formula_expression e cached_value são preservados separadamente — nunca colapsamos uma fórmula no resultado '
  '(Fase 3A Passo 5). BIGSERIAL em vez de UUID: tabela de alto volume, sem necessidade de FK externa vindo de '
  'outro schema (staging referencia sheet_id/workbook_id, não célula a célula) — desvio documentado do padrão '
  'geral de UUID por motivo de volume/performance.';
COMMENT ON COLUMN raw.cells.formula_expression IS
  'Texto da fórmula original. Nunca substituído pelo valor calculado — a auditoria futura precisa provar de '
  'onde cada cálculo vem.';

-- --------------------------------------------------------------- staging --

CREATE TABLE staging.unit_candidates (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_workbook_id   UUID NOT NULL REFERENCES raw.workbooks(id),
  source_sheet_id      UUID NOT NULL REFERENCES raw.sheets(id),
  source_row           INTEGER,
  development_ref      TEXT,
  tower_ref            TEXT,
  unit_ref             TEXT,
  typology_ref         TEXT,
  private_area         NUMERIC(12,4),
  uncovered_area       NUMERIC(12,4),
  floor_ref            TEXT,
  position_ref         TEXT,
  mapping_confidence   TEXT NOT NULL CHECK (mapping_confidence IN ('HIGH','MEDIUM','LOW')),
  mapping_status       TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
                         CHECK (mapping_status IN ('CANDIDATE','REVIEW_REQUIRED','REJECTED')),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE staging.unit_candidates IS
  'Candidato normalizado a unidade física, derivado de raw.* com rastreabilidade obrigatória. Nunca promovido '
  'a core.units automaticamente — isso é decisão de uma fase futura.';

CREATE TABLE staging.parameter_candidates (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_workbook_id   UUID NOT NULL REFERENCES raw.workbooks(id),
  source_sheet_id      UUID NOT NULL REFERENCES raw.sheets(id),
  source_row           INTEGER,
  source_cell_ref      TEXT,
  parameter_key_guess  TEXT,
  value_text           TEXT,
  value_type_guess     TEXT CHECK (value_type_guess IS NULL OR value_type_guess IN ('NUMERIC','TEXT','BOOLEAN','DATE')),
  mapping_confidence   TEXT NOT NULL CHECK (mapping_confidence IN ('HIGH','MEDIUM','LOW')),
  mapping_status       TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
                         CHECK (mapping_status IN ('CANDIDATE','REVIEW_REQUIRED','REJECTED')),
  notes                TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE staging.parameter_candidates IS
  'Candidato normalizado a parâmetro de precificação (equivalente conceitual a pricing.parameters).';

CREATE TABLE staging.calibration_candidates (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_workbook_id   UUID NOT NULL REFERENCES raw.workbooks(id),
  source_sheet_id      UUID NOT NULL REFERENCES raw.sheets(id),
  source_cell_ref      TEXT,   -- rastreabilidade até a célula exata (Passo 17) — sem isso a linhagem parava na aba
  dimension_guess      TEXT,
  category_key_guess   TEXT,
  factor_value         NUMERIC(18,6),
  mapping_confidence   TEXT NOT NULL CHECK (mapping_confidence IN ('HIGH','MEDIUM','LOW')),
  mapping_status       TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
                         CHECK (mapping_status IN ('CANDIDATE','REVIEW_REQUIRED','REJECTED')),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE staging.calibration_candidates IS
  'Candidato normalizado a entrada de calibração (equivalente conceitual a pricing.calibration_entries).';

CREATE TABLE staging.price_output_candidates (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_workbook_id   UUID NOT NULL REFERENCES raw.workbooks(id),
  source_sheet_id      UUID NOT NULL REFERENCES raw.sheets(id),
  source_row           INTEGER,
  unit_ref_guess       TEXT,
  price_value          NUMERIC(18,2),
  price_per_m2_value   NUMERIC(18,2),
  mapping_confidence   TEXT NOT NULL CHECK (mapping_confidence IN ('HIGH','MEDIUM','LOW')),
  mapping_status       TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
                         CHECK (mapping_status IN ('CANDIDATE','REVIEW_REQUIRED','REJECTED')),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE staging.price_output_candidates IS
  'Candidato normalizado a resultado de preço já calculado na fonte (equivalente conceitual a '
  'pricing.unit_price_results) — apenas capturado para análise, NUNCA usado como se fosse um pricing.runs real '
  '(Fase 3A Passo 25: nenhum preço é calculado ou reproduzido nesta fase).';

CREATE TABLE staging.mapping_review (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_workbook_id   UUID NOT NULL REFERENCES raw.workbooks(id),
  source_sheet_id      UUID NOT NULL REFERENCES raw.sheets(id),
  source_row           INTEGER,
  source_cell_ref      TEXT,
  field_label          TEXT,
  suspected_concept    TEXT,
  confidence           TEXT NOT NULL CHECK (confidence IN ('HIGH','MEDIUM','LOW')),
  status               TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
                         CHECK (status IN ('UNMAPPED','REVIEW_REQUIRED')),
  reviewer_notes        TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE staging.mapping_review IS
  'Catálogo de campos cujo significado permanece ambíguo (MEDIUM/LOW confidence) ou não mapeado. '
  '"UNMAPPED"/"REVIEW_REQUIRED" são resultados válidos (Fase 3A Passo 10) — nunca escolhemos um significado só '
  'por convêniencia quando a evidência não sustenta.';

-- ------------------------------------------------------------- índices --

CREATE INDEX idx_raw_workbooks_batch ON raw.workbooks (ingest_batch_id);
CREATE INDEX idx_raw_sheets_workbook ON raw.sheets (workbook_id);
CREATE INDEX idx_raw_cells_sheet ON raw.cells (sheet_id);
CREATE INDEX idx_raw_cells_formula ON raw.cells (sheet_id) WHERE formula_expression IS NOT NULL;

CREATE INDEX idx_staging_unit_candidates_source ON staging.unit_candidates (source_workbook_id, source_sheet_id);
CREATE INDEX idx_staging_unit_candidates_status ON staging.unit_candidates (mapping_status);
CREATE INDEX idx_staging_parameter_candidates_source ON staging.parameter_candidates (source_workbook_id, source_sheet_id);
CREATE INDEX idx_staging_calibration_candidates_source ON staging.calibration_candidates (source_workbook_id, source_sheet_id);
CREATE INDEX idx_staging_price_output_candidates_source ON staging.price_output_candidates (source_workbook_id, source_sheet_id);
CREATE INDEX idx_staging_mapping_review_source ON staging.mapping_review (source_workbook_id, source_sheet_id);
CREATE INDEX idx_staging_mapping_review_status ON staging.mapping_review (status);
