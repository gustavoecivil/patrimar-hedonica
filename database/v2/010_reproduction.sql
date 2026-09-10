-- Patrimar Pricing Intelligence — Schema canônico v2
-- Extensão mínima e genérica para suportar a Fase 3C (reprodução
-- independente da lógica de precificação, sem calcular preço de
-- produção nem recomendação de mercado).
--
-- Nenhuma linha é inserida por este arquivo — só estrutura. Nenhum
-- nome, valor, fórmula ou constante privada aparece aqui.
--
-- 1) pricing.runs.run_type ganha 'REPRODUCTION_VALIDATION_RUN' — um
--    terceiro tipo de execução, distinto de SYSTEM_RUN (motor real de
--    produção) e IMPORTED_REFERENCE_RUN (Fase 3B). Nunca deve ser
--    confundido com recomendação de mercado ou precificação de
--    produção (Fase 3C, Passo 13/29).
--
-- 2) audit.reproduction_runs — mesmo padrão de
--    raw.ingest_batches/audit.promotion_runs: identifica uma execução
--    de reprodução por (development_id, ruleset_version), com o mesmo
--    cuidado de comitar o registro do batch ANTES do bloco de risco,
--    para que um FAILED real seja possível após rollback.
--
-- 3) pricing.reproduction_comparisons — separa explicitamente
--    SOURCE_REFERENCE_PRICE (já existente, nunca sobrescrito) de
--    REPRODUCED_PRICE (calculado nesta fase) e o DELTA entre os dois,
--    sem misturar essa semântica de comparação dentro de
--    pricing.unit_price_results (Fase 3C, Passo 14).

DO $$
DECLARE
  con_name TEXT;
BEGIN
  SELECT conname INTO con_name
  FROM pg_constraint
  WHERE conrelid = 'pricing.runs'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) ILIKE '%run_type%SYSTEM_RUN%IMPORTED_REFERENCE_RUN%';
  IF con_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE pricing.runs DROP CONSTRAINT %I', con_name);
  END IF;
END $$;
ALTER TABLE pricing.runs
  ADD CONSTRAINT ck_runs_run_type
  CHECK (run_type IN ('SYSTEM_RUN', 'IMPORTED_REFERENCE_RUN', 'REPRODUCTION_VALIDATION_RUN'));
COMMENT ON COLUMN pricing.runs.run_type IS
  'SYSTEM_RUN = execução real de produção do motor de alocação. IMPORTED_REFERENCE_RUN = importação histórica '
  '(Fase 3B). REPRODUCTION_VALIDATION_RUN = tentativa de reproduzir, de forma independente e auditável, um '
  'resultado IMPORTED_REFERENCE já existente — nunca uma recomendação de mercado nem precificação de produção '
  '(Fase 3C, ver docs/16-INDEPENDENT-PRICING-REPRODUCTION.md).';

CREATE TABLE audit.reproduction_runs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  development_id   UUID NOT NULL REFERENCES core.developments(id),
  ruleset_version   TEXT NOT NULL,
  mapping_version   TEXT NOT NULL,
  pricing_run_id    UUID REFERENCES pricing.runs(id),
  status            TEXT NOT NULL DEFAULT 'PENDING'
                       CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
  started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at      TIMESTAMPTZ,
  notes             TEXT,
  CONSTRAINT uq_reproduction_runs_dev_ruleset UNIQUE (development_id, ruleset_version),
  CONSTRAINT ck_reproduction_runs_completed_after_started
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);
COMMENT ON TABLE audit.reproduction_runs IS
  'Uma execução do pipeline de reprodução independente (Fase 3C), identificada por '
  '(development_id, ruleset_version). Mesmo padrão de raw.ingest_batches/audit.promotion_runs: se a reprodução '
  'falha, o registro fica FAILED — nunca "parcialmente concluído" silencioso.';
COMMENT ON COLUMN audit.reproduction_runs.ruleset_version IS
  'Identificador determinístico da versão do arquivo de regras privado usado nesta reprodução (ex.: hash do '
  'conteúdo do ruleset) — nunca o conteúdo das regras em si.';

CREATE TABLE pricing.reproduction_comparisons (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reproduction_run_id    UUID NOT NULL REFERENCES pricing.runs(id),
  imported_run_id        UUID NOT NULL REFERENCES pricing.runs(id),
  unit_id                UUID NOT NULL REFERENCES core.units(id),
  source_reference_price NUMERIC(18,2),
  reproduced_price       NUMERIC(18,2),
  delta_absolute         NUMERIC(18,2) GENERATED ALWAYS AS (reproduced_price - source_reference_price) STORED,
  delta_percent          NUMERIC(12,6),
  match_classification   TEXT
                            CHECK (match_classification IS NULL OR match_classification IN
                              ('EXACT','WITHIN_1_CENT','WITHIN_1_REAL','WITHIN_0_01_PERCENT','DIVERGENT','BLOCKED')),
  divergence_cause       TEXT
                            CHECK (divergence_cause IS NULL OR divergence_cause IN
                              ('ROUNDING','MISSING_PARAMETER','WRONG_MAPPING','DERIVATION_ERROR',
                               'CALIBRATION_SELECTION','DORMANT_RULE_APPLIED','OVERRIDE','FORMULA_VARIATION',
                               'SOURCE_ANOMALY','IMPLEMENTATION_BUG','BUSINESS_RULE_AMBIGUITY','UNKNOWN')),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_reproduction_comparisons_run_unit UNIQUE (reproduction_run_id, unit_id)
);
COMMENT ON TABLE pricing.reproduction_comparisons IS
  'Compara, por unidade, SOURCE_REFERENCE_PRICE (de um run IMPORTED_REFERENCE_RUN, nunca sobrescrito) contra '
  'REPRODUCED_PRICE (de um run REPRODUCTION_VALIDATION_RUN calculado sem acesso ao preço de referência durante '
  'o cálculo — Fase 3C, Passo 12). match_classification=BLOCKED quando a unidade não pôde ser calculada de forma '
  'independente (ex.: parâmetro/calibração ausente) — nesse caso reproduced_price fica NULL, nunca um valor '
  'inventado.';

CREATE INDEX idx_reproduction_runs_development ON audit.reproduction_runs (development_id);
CREATE INDEX idx_reproduction_comparisons_run ON pricing.reproduction_comparisons (reproduction_run_id);
CREATE INDEX idx_reproduction_comparisons_classification ON pricing.reproduction_comparisons (match_classification);
