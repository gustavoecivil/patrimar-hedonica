-- Patrimar Pricing Intelligence — Schema canônico v2
-- Índices justificados por fluxo de consulta previsto. Não indexa toda
-- coluna — apenas caminhos de acesso já antecipados pelo modelo conceitual
-- (Fase 1D) e pelas views (007).

-- core: navegação development -> tower/typology/unit
CREATE INDEX idx_towers_development ON core.towers (development_id);
CREATE INDEX idx_unit_typologies_development ON core.unit_typologies (development_id);
CREATE INDEX idx_units_development ON core.units (development_id);
CREATE INDEX idx_units_tower ON core.units (tower_id);
CREATE INDEX idx_units_typology ON core.units (unit_typology_id);

-- pricing: apenas um cenário ACTIVE por empreendimento por vez —
-- sustenta a semântica de pricing.v_unit_price_current (007_views.sql).
CREATE UNIQUE INDEX uq_scenarios_one_active_per_development
  ON pricing.scenarios (development_id)
  WHERE status = 'ACTIVE';

CREATE INDEX idx_parameter_sets_scenario ON pricing.parameter_sets (scenario_id);
CREATE INDEX idx_parameters_set ON pricing.parameters (parameter_set_id);
CREATE INDEX idx_calibration_sets_scenario ON pricing.calibration_sets (scenario_id);
CREATE INDEX idx_calibration_entries_set ON pricing.calibration_entries (calibration_set_id);

CREATE INDEX idx_runs_scenario ON pricing.runs (scenario_id);
CREATE INDEX idx_runs_status ON pricing.runs (status);
-- suporta "última run concluída por cenário" (usado em pricing.v_unit_price_current)
CREATE INDEX idx_runs_scenario_completed_at ON pricing.runs (scenario_id, completed_at DESC)
  WHERE status = 'COMPLETED';

CREATE INDEX idx_vgv_targets_scenario ON pricing.vgv_targets (scenario_id);
CREATE INDEX idx_vgv_targets_run ON pricing.vgv_targets (run_id);

CREATE INDEX idx_unit_adjustments_run ON pricing.unit_adjustments (run_id);
CREATE INDEX idx_unit_adjustments_unit ON pricing.unit_adjustments (unit_id);

CREATE INDEX idx_unit_price_results_unit ON pricing.unit_price_results (unit_id);
-- (run_id, unit_id) já tem índice implícito via uq_unit_price_results_run_unit.

-- suporta "override mais recente por (run, unit)" (usado na view)
CREATE INDEX idx_unit_overrides_run_unit_decided_at
  ON pricing.unit_overrides (run_id, unit_id, decided_at DESC);

CREATE INDEX idx_validations_run ON pricing.validations (run_id);

-- audit: consulta por entidade referenciada
CREATE INDEX idx_data_lineage_entity ON audit.data_lineage (entity_schema, entity_table, entity_id);

-- market
CREATE INDEX idx_model_versions_model ON market.model_versions (model_id);
CREATE INDEX idx_predictions_model_version ON market.predictions (model_version_id);
CREATE INDEX idx_predictions_development ON market.predictions (development_id);
CREATE INDEX idx_predictions_unit ON market.predictions (unit_id);
