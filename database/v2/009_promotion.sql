-- Patrimar Pricing Intelligence — Schema canônico v2
-- Extensão mínima e genérica para suportar a Fase 3B (promoção
-- controlada de staging.* para core.*/pricing.*).
--
-- Nenhuma linha é inserida por este arquivo — só estrutura. Nenhum
-- nome, valor ou fórmula privado aparece aqui.
--
-- Motivação de cada mudança, em ordem:
--
-- 1) audit.promotion_runs — equivalente, em nível de PROMOÇÃO, de
--    raw.ingest_batches (Fase 3A): registra qual (ingest_batch +
--    mapping_version) já foi promovido, com o mesmo padrão de estado
--    PENDING/RUNNING/COMPLETED/FAILED e o mesmo cuidado de comitar o
--    registro do batch ANTES do bloco de risco, para que um FAILED
--    real seja possível após rollback. Garante reprodutibilidade
--    exata a partir de (source SHA implícito no ingest_batch) +
--    ingest_batch + mapping_version.
--
-- 2) staging.*_candidates.promoted_entity_id/promoted_at — idempotência
--    e lineage ao nível de cada candidato individual: uma segunda
--    execução da promoção nunca duplica uma entidade já promovida.
--
-- 3) staging.mapping_review.review_classification — permite
--    classificar cada item pendente (BLOCKING_CORE/BLOCKING_PRICING/
--    NON_BLOCKING/BUSINESS_CLARIFICATION) sem inventar significado
--    para o campo em si.
--
-- 4) pricing.runs.run_type e pricing.unit_price_results.result_origin —
--    a distinção central desta fase: nenhum resultado que já existia
--    na planilha original pode ser confundido com um resultado
--    calculado pelo novo motor. Aditivo (DEFAULT preenchido), não
--    quebra nenhum dado sintético já existente (Fase 2B/2C).
--
-- 5) pricing.vgv_targets — adiciona 'IMPORTED_REFERENCE' ao vocabulário
--    já existente de `origin`, pelo mesmo motivo. A constraint CHECK
--    original não tinha nome explícito; localizada dinamicamente antes
--    de recriada, para não depender de um nome gerado implicitamente
--    pelo PostgreSQL.
--
-- 6) core.unit_typologies.classification — distingue tipologia oficial
--    (confirmada pela própria fonte) de agrupamento derivado ou
--    desconhecido — nunca promovida como oficial sem evidência.

CREATE TABLE audit.promotion_runs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ingest_batch_id  UUID NOT NULL REFERENCES raw.ingest_batches(id),
  mapping_version  TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at     TIMESTAMPTZ,
  notes            TEXT,
  CONSTRAINT uq_promotion_runs_batch_mapping UNIQUE (ingest_batch_id, mapping_version),
  CONSTRAINT ck_promotion_runs_completed_after_started
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);
COMMENT ON TABLE audit.promotion_runs IS
  'Uma execução do pipeline de promoção staging->core/pricing (Fase 3B), identificada por '
  '(ingest_batch_id, mapping_version). Mesmo padrão de raw.ingest_batches: se a promoção falha, o registro '
  'do batch (já comitado antes do bloco de risco) é marcado FAILED — nunca "parcialmente concluído" silencioso.';
COMMENT ON COLUMN audit.promotion_runs.mapping_version IS
  'Identificador determinístico da versão do arquivo de mapeamento privado usado nesta promoção (ex.: hash do '
  'conteúdo do mapeamento) — nunca o conteúdo do mapeamento em si.';

ALTER TABLE staging.unit_candidates
  ADD COLUMN promoted_entity_id UUID,
  ADD COLUMN promoted_at        TIMESTAMPTZ;
ALTER TABLE staging.parameter_candidates
  ADD COLUMN promoted_entity_id UUID,
  ADD COLUMN promoted_at        TIMESTAMPTZ;
ALTER TABLE staging.calibration_candidates
  ADD COLUMN promoted_entity_id UUID,
  ADD COLUMN promoted_at        TIMESTAMPTZ;
ALTER TABLE staging.price_output_candidates
  ADD COLUMN promoted_entity_id UUID,
  ADD COLUMN promoted_at        TIMESTAMPTZ;
COMMENT ON COLUMN staging.unit_candidates.promoted_entity_id IS
  'id da linha em core.units criada a partir deste candidato, quando promovido. NULL enquanto não promovido — '
  'usado para idempotência (nunca promover o mesmo candidato duas vezes) e lineage (Fase 3B).';
COMMENT ON COLUMN staging.parameter_candidates.promoted_entity_id IS
  'id da linha em pricing.parameters criada a partir deste candidato, quando promovido (Fase 3B).';
COMMENT ON COLUMN staging.calibration_candidates.promoted_entity_id IS
  'id da linha em pricing.calibration_entries criada a partir deste candidato, quando promovido (Fase 3B).';
COMMENT ON COLUMN staging.price_output_candidates.promoted_entity_id IS
  'id da linha em pricing.unit_price_results (result_origin=IMPORTED_REFERENCE) criada a partir deste '
  'candidato, quando promovido (Fase 3B).';

ALTER TABLE staging.mapping_review
  ADD COLUMN review_classification TEXT
    CHECK (review_classification IS NULL OR review_classification IN
      ('BLOCKING_CORE','BLOCKING_PRICING','NON_BLOCKING','BUSINESS_CLARIFICATION'));
COMMENT ON COLUMN staging.mapping_review.review_classification IS
  'Classificação de impacto de um item ainda não promovido (Fase 3B) — nunca atribuída para inventar '
  'significado do campo em si, apenas para priorizar revisão futura. NULL é um valor válido (ainda não '
  'classificado).';

ALTER TABLE pricing.runs
  ADD COLUMN run_type TEXT NOT NULL DEFAULT 'SYSTEM_RUN'
    CHECK (run_type IN ('SYSTEM_RUN','IMPORTED_REFERENCE_RUN'));
COMMENT ON COLUMN pricing.runs.run_type IS
  'SYSTEM_RUN = execução real do motor de alocação (REFERENCE_ALLOCATION_V1 ou futuro motor real). '
  'IMPORTED_REFERENCE_RUN = representa uma importação histórica de resultados já existentes numa fonte '
  'externa (ex.: planilha) — nunca um cálculo novo. Distinção obrigatória (Fase 3B): nenhum resultado '
  'importado pode ser confundido com um resultado calculado pelo Patrimar Pricing Intelligence.';

ALTER TABLE pricing.unit_price_results
  ADD COLUMN result_origin TEXT NOT NULL DEFAULT 'SYSTEM_CALCULATED'
    CHECK (result_origin IN ('SYSTEM_CALCULATED','IMPORTED_REFERENCE'));
COMMENT ON COLUMN pricing.unit_price_results.result_origin IS
  'SYSTEM_CALCULATED = valor produzido por uma run real do motor de alocação. IMPORTED_REFERENCE = valor que '
  'já existia numa fonte externa (ex.: planilha) e foi apenas armazenado aqui para referência/análise — as '
  'colunas system_calculated_price/system_calculated_price_per_m2 guardam o valor IMPORTADO nesse caso, NUNCA '
  'um valor recalculado por este sistema. Ver docs/15-STAGING-TO-CANONICAL-PROMOTION.md.';

DO $$
DECLARE
  con_name TEXT;
BEGIN
  SELECT conname INTO con_name
  FROM pg_constraint
  WHERE conrelid = 'pricing.vgv_targets'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) ILIKE '%origin%MANUAL%MARKET_PRICING_ENGINE%';
  IF con_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE pricing.vgv_targets DROP CONSTRAINT %I', con_name);
  END IF;
END $$;
ALTER TABLE pricing.vgv_targets
  ADD CONSTRAINT ck_vgv_targets_origin
  CHECK (origin IN ('MANUAL','MARKET_PRICING_ENGINE','IMPORTED_REFERENCE'));
COMMENT ON COLUMN pricing.vgv_targets.origin IS
  'MANUAL = decisão humana direta. MARKET_PRICING_ENGINE = produzido pelo Motor A. IMPORTED_REFERENCE = valor '
  'de VGV que já existia numa fonte externa (ex.: planilha), importado para referência — nunca uma '
  'recomendação do Motor A nem uma decisão manual tomada no novo sistema (Fase 3B).';

ALTER TABLE core.unit_typologies
  ADD COLUMN classification TEXT NOT NULL DEFAULT 'UNKNOWN'
    CHECK (classification IN ('OFFICIAL_TYPOLOGY','DERIVED_GROUPING','UNKNOWN'));
COMMENT ON COLUMN core.unit_typologies.classification IS
  'OFFICIAL_TYPOLOGY = rótulo de tipologia como existe explicitamente na fonte (ex.: coluna de tipologia com '
  'cabeçalho confirmado). DERIVED_GROUPING = agrupamento inferido por nós (ex.: por combinação de área/quartos), '
  'nunca apresentado como se fosse oficial da fonte. UNKNOWN = ainda não classificado (Fase 3B).';
