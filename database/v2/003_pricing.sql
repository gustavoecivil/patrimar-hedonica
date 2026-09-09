-- Patrimar Pricing Intelligence — Schema canônico v2
-- pricing: Unit Price Allocation Engine (Motor B — D7). Distribui um
-- VGV/preço-base já definido entre as unidades de um empreendimento.
--
-- Metodologia de origem: reconstruída com evidência de fórmula na
-- Fase 1C (ver docs/09-PRICING-LOGIC-REVERSE-ENGINEERING.md). Nenhum
-- nome, fórmula ou valor privado aparece neste arquivo — apenas a
-- estrutura genérica que a metodologia evidenciou.
--
-- data_source_id em pricing.parameters não tem FK física aqui (audit é
-- criado no arquivo seguinte); a FK é adicionada em 004_audit.sql.
-- market_prediction_id em pricing.vgv_targets não tem FK física aqui
-- (market é criado em 005); a FK é adicionada em 005_market_foundation.sql.

CREATE TABLE pricing.scenarios (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  development_id  UUID NOT NULL REFERENCES core.developments(id),
  code            TEXT NOT NULL,
  name            TEXT,
  description     TEXT,
  status          TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')),
  reference_date  DATE,
  created_by      TEXT,           -- placeholder genérico; sem autenticação nesta fase
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_scenarios_dev_code UNIQUE (development_id, code)
);
COMMENT ON TABLE pricing.scenarios IS
  'Uma hipótese de precificação para um empreendimento. Granularidade: PRICING_SCENARIO. '
  'Não observado explicitamente na metodologia atual (cada arquivo é, na prática, um cenário sem identidade '
  'formal) — extensão proposta na Fase 1D/2, não cópia do que já existe.';
COMMENT ON COLUMN pricing.scenarios.status IS
  'TEXT + CHECK em vez de PostgreSQL ENUM — decisão documentada em database/v2/README.md '
  '(vocabulário de status ainda deve evoluir).';

CREATE TABLE pricing.parameter_sets (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id  UUID NOT NULL REFERENCES pricing.scenarios(id),
  code         TEXT NOT NULL,
  version      INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  status       TEXT NOT NULL DEFAULT 'DRAFT'
                 CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')),
  valid_from   TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to     TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_parameter_sets_scenario_code_version UNIQUE (scenario_id, code, version),
  CONSTRAINT ck_parameter_sets_validity CHECK (valid_to IS NULL OR valid_to > valid_from)
);
COMMENT ON TABLE pricing.parameter_sets IS
  'Conjunto versionado de parâmetros de precificação. Nunca sobrescrito — uma mudança gera version+1.';

CREATE TABLE pricing.parameters (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parameter_set_id  UUID NOT NULL REFERENCES pricing.parameter_sets(id),
  key               TEXT NOT NULL,          -- nome genérico do parâmetro, ex.: 'open_terrace_weight', 'target_price_per_m2'
  value_type        TEXT NOT NULL CHECK (value_type IN ('NUMERIC','TEXT','BOOLEAN','DATE')),
  numeric_value     NUMERIC(18,6),
  text_value        TEXT,
  boolean_value     BOOLEAN,
  date_value        DATE,
  unit_of_measure   TEXT,                   -- ex.: 'ratio', 'BRL_per_m2', 'code'
  description       TEXT,
  data_source_id    UUID,                   -- FK -> audit.data_sources adicionada em 004_audit.sql
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_parameters_set_key UNIQUE (parameter_set_id, key),
  CONSTRAINT ck_parameters_typed_value CHECK (
    (value_type = 'NUMERIC' AND numeric_value IS NOT NULL AND text_value IS NULL AND boolean_value IS NULL AND date_value IS NULL) OR
    (value_type = 'TEXT'    AND text_value    IS NOT NULL AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL) OR
    (value_type = 'BOOLEAN' AND boolean_value IS NOT NULL AND numeric_value IS NULL AND text_value IS NULL AND date_value IS NULL) OR
    (value_type = 'DATE'    AND date_value    IS NOT NULL AND numeric_value IS NULL AND text_value IS NULL AND boolean_value IS NULL)
  )
);
COMMENT ON TABLE pricing.parameters IS
  'Parâmetro individual dentro de um parameter_set. Colunas tipadas por value_type em vez de uma única coluna '
  'TEXT genérica — ver database/v2/README.md, "Por que não uma coluna TEXT única".';

CREATE TABLE pricing.calibration_sets (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id  UUID NOT NULL REFERENCES pricing.scenarios(id),
  code         TEXT NOT NULL,          -- ex.: 'floor_premium', 'position_premium'
  dimension    TEXT NOT NULL,          -- rótulo genérico e extensível da dimensão calibrada (não ENUM)
  version      INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  status       TEXT NOT NULL DEFAULT 'DRAFT'
                 CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')),
  valid_from   TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to     TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_calibration_sets_scenario_code_version UNIQUE (scenario_id, code, version),
  CONSTRAINT ck_calibration_sets_validity CHECK (valid_to IS NULL OR valid_to > valid_from)
);
COMMENT ON TABLE pricing.calibration_sets IS
  'Tabela de calibração versionada (ex.: peso por pavimento, peso por posição). Uma variante hoje observada como '
  'dormente numa das fontes é representável aqui com status ARCHIVED/DRAFT, sem perder histórico (Fase 1C/1D).';

CREATE TABLE pricing.calibration_entries (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  calibration_set_id    UUID NOT NULL REFERENCES pricing.calibration_sets(id),
  category_key          TEXT NOT NULL,      -- ex.: código de pavimento ou de posição
  factor                NUMERIC(12,6) NOT NULL,
  notes                 TEXT,
  CONSTRAINT uq_calibration_entries_set_key UNIQUE (calibration_set_id, category_key)
);
COMMENT ON TABLE pricing.calibration_entries IS 'Uma entrada (categoria -> fator) dentro de um calibration_set.';

CREATE TABLE pricing.runs (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id        UUID NOT NULL REFERENCES pricing.scenarios(id),
  parameter_set_id   UUID NOT NULL REFERENCES pricing.parameter_sets(id),
  code               TEXT,
  status             TEXT NOT NULL DEFAULT 'PENDING'
                       CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
  engine_version     TEXT,          -- versão/regra do motor de alocação utilizada
  started_at         TIMESTAMPTZ,
  completed_at       TIMESTAMPTZ,
  notes              TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_runs_started_before_completed
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);
COMMENT ON TABLE pricing.runs IS
  'Uma execução do motor de alocação. Granularidade: PRICING_RUN. Invariante de negócio (não física, ver README): '
  'uma run COMPLETED não deve ser reinterpretada silenciosamente por parâmetros novos — mudar parâmetros exige '
  'uma nova run, nunca um UPDATE nos resultados de uma run concluída.';

CREATE TABLE pricing.run_calibration_sets (
  run_id              UUID NOT NULL REFERENCES pricing.runs(id),
  calibration_set_id  UUID NOT NULL REFERENCES pricing.calibration_sets(id),
  PRIMARY KEY (run_id, calibration_set_id)
);
COMMENT ON TABLE pricing.run_calibration_sets IS
  'Associação N:N — uma run pode usar mais de uma dimensão de calibração ao mesmo tempo (ex.: pavimento + posição).';

CREATE TABLE pricing.vgv_targets (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id           UUID NOT NULL REFERENCES pricing.scenarios(id),
  run_id                UUID REFERENCES pricing.runs(id),
  origin                TEXT NOT NULL CHECK (origin IN ('MANUAL','MARKET_PRICING_ENGINE')),
  target_value          NUMERIC(18,2) NOT NULL CHECK (target_value > 0),
  reference_area_m2     NUMERIC(12,2),
  price_per_m2_basis    NUMERIC(12,2),
  market_prediction_id  UUID,        -- FK -> market.predictions adicionada em 005_market_foundation.sql
  status                TEXT NOT NULL DEFAULT 'DRAFT'
                          CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_vgv_targets_market_needs_prediction
    CHECK (origin <> 'MARKET_PRICING_ENGINE' OR market_prediction_id IS NOT NULL)
);
COMMENT ON TABLE pricing.vgv_targets IS
  'Valor-alvo de VGV para um cenário/run. origin distingue se veio de decisão manual ou do Motor A — nunca '
  'acoplado a uma única origem (Fase 1D, Passo 11).';

CREATE TABLE pricing.unit_adjustments (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id                UUID NOT NULL REFERENCES pricing.runs(id),
  unit_id               UUID NOT NULL REFERENCES core.units(id),
  adjustment_type       TEXT NOT NULL,     -- rótulo genérico e extensível, ex.: 'AREA_WEIGHTING', 'FLOOR_PREMIUM'
  input_value           NUMERIC(18,6),
  factor_value          NUMERIC(12,6),
  calibration_entry_id  UUID REFERENCES pricing.calibration_entries(id),
  parameter_id          UUID REFERENCES pricing.parameters(id),
  result_value          NUMERIC(18,6) NOT NULL,
  sequence_order        INTEGER NOT NULL DEFAULT 1 CHECK (sequence_order > 0),
  explanation           TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE pricing.unit_adjustments IS
  'Um passo intermediário do cálculo por unidade (não apenas o preço final — precisamos explicar como se chegou '
  'nele, Fase 1D Passo 12). calibration_entry_id/parameter_id dão rastreabilidade até a origem do fator aplicado.';

CREATE TABLE pricing.unit_price_results (
  id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id                         UUID NOT NULL REFERENCES pricing.runs(id),
  unit_id                        UUID NOT NULL REFERENCES core.units(id),
  weighted_area_m2               NUMERIC(12,4),
  participation_share            NUMERIC(9,6) CHECK (participation_share IS NULL OR (participation_share BETWEEN 0 AND 1)),
  combined_weight_factor         NUMERIC(12,6),
  system_calculated_price        NUMERIC(18,2) NOT NULL CHECK (system_calculated_price >= 0),
  system_calculated_price_per_m2 NUMERIC(12,2),
  created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_unit_price_results_run_unit UNIQUE (run_id, unit_id)
);
COMMENT ON TABLE pricing.unit_price_results IS
  'Resultado calculado pelo sistema (SYSTEM_RESULT), por unidade, por run. Não inclui override — ver '
  'pricing.unit_overrides (Passo 13/14: override é entidade separada, nunca sobrescrita).';

CREATE TABLE pricing.unit_overrides (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id          UUID NOT NULL,
  unit_id         UUID NOT NULL,
  previous_price  NUMERIC(18,2) NOT NULL CHECK (previous_price >= 0),
  proposed_price  NUMERIC(18,2) NOT NULL CHECK (proposed_price >= 0),
  final_price     NUMERIC(18,2) NOT NULL CHECK (final_price >= 0),
  vgv_impact      NUMERIC(18,2) GENERATED ALWAYS AS (final_price - previous_price) STORED,
  reason          TEXT,
  author_ref      TEXT,            -- placeholder genérico; sem autenticação nesta fase
  decided_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT fk_unit_overrides_price_result
    FOREIGN KEY (run_id, unit_id) REFERENCES pricing.unit_price_results(run_id, unit_id)
);
COMMENT ON TABLE pricing.unit_overrides IS
  'Evento de override — sempre INSERT, nunca UPDATE destrutivo do valor histórico (Passo 14). A FK composta '
  '(run_id, unit_id) garante que todo override se refere a um resultado calculado existente. Múltiplas linhas '
  'para o mesmo (run_id, unit_id) são esperadas e representam a sequência histórica de decisões.';

CREATE TABLE pricing.validations (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id         UUID NOT NULL REFERENCES pricing.runs(id),
  check_type     TEXT NOT NULL,     -- ex.: 'VGV_RECONCILIATION', 'UNITS_WITHOUT_PRICE', 'MISSING_PARAMETER'
  severity       TEXT NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR')),
  expected_value NUMERIC(18,2),
  actual_value   NUMERIC(18,2),
  difference     NUMERIC(18,2) GENERATED ALWAYS AS (actual_value - expected_value) STORED,
  message        TEXT,
  checked_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE pricing.validations IS
  'Resultado de uma verificação de negócio sobre uma run (ex.: SUM(preço final) vs. VGV alvo). Deliberadamente '
  'não é um CHECK de linha — é validação de negócio, registrada como dado, não travada estruturalmente (Passo 19). '
  'A anomalia de fórmula real encontrada na Fase 1C justifica este domínio; a fórmula privada em si não é '
  'reproduzida aqui.';
