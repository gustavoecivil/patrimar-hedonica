-- Patrimar Pricing Intelligence — Schema canônico v2
-- Views analíticas. Criada apenas uma, com semântica explícita — ver
-- Passo 23 da Fase 2: "se não puder definir corretamente, não criar".

-- pricing.v_unit_price_current
--
-- Semântica exata de "current" (para não ficar ambígua):
--   1. Para cada empreendimento, considera o único cenário com status
--      ACTIVE (garantido no máximo um pela constraint
--      uq_scenarios_one_active_per_development, ver 006_indexes.sql).
--   2. Dentro desse cenário, considera a run mais recente com
--      status COMPLETED (por completed_at).
--   3. Para cada unidade, o preço "atual" é o valor do override mais
--      recente (por decided_at) daquela run/unidade, se existir; caso
--      contrário, o preço calculado pelo sistema.
--
-- Isto é uma FOTOGRAFIA do estado mais recente confirmado — não
-- substitui o histórico. Toda linha de pricing.unit_price_results e
-- pricing.unit_overrides permanece intacta e consultável diretamente
-- para qualquer análise histórica.
CREATE OR REPLACE VIEW pricing.v_unit_price_current AS
WITH active_scenario AS (
  SELECT id AS scenario_id, development_id
  FROM pricing.scenarios
  WHERE status = 'ACTIVE'
),
latest_run_per_scenario AS (
  -- DISTINCT ON exige o ORDER BY correspondente na MESMA consulta (uma
  -- CTE separada só com ORDER BY não garante a ordem quando lida de
  -- outra consulta) — por isso está tudo num único SELECT aqui.
  SELECT DISTINCT ON (r.scenario_id) r.id AS run_id, r.scenario_id
  FROM pricing.runs r
  JOIN active_scenario s ON s.scenario_id = r.scenario_id
  WHERE r.status = 'COMPLETED'
  ORDER BY r.scenario_id, r.completed_at DESC
),
latest_override AS (
  SELECT DISTINCT ON (run_id, unit_id) run_id, unit_id, final_price, decided_at
  FROM pricing.unit_overrides
  ORDER BY run_id, unit_id, decided_at DESC
)
SELECT
  s.development_id,
  lr.run_id,
  upr.unit_id,
  upr.system_calculated_price,
  lo.final_price                                                AS override_final_price,
  COALESCE(lo.final_price, upr.system_calculated_price)         AS current_final_price,
  upr.system_calculated_price_per_m2,
  upr.participation_share,
  upr.weighted_area_m2
FROM active_scenario s
JOIN latest_run_per_scenario lr ON lr.scenario_id = s.scenario_id
JOIN pricing.unit_price_results upr ON upr.run_id = lr.run_id
LEFT JOIN latest_override lo ON lo.run_id = upr.run_id AND lo.unit_id = upr.unit_id;

COMMENT ON VIEW pricing.v_unit_price_current IS
  'Preço "atual" por unidade = resultado da run COMPLETED mais recente do cenário ACTIVE do empreendimento, '
  'com o override mais recente aplicado quando existir. Não é um substituto do histórico — ver comentário no '
  'arquivo-fonte (007_views.sql) para a semântica completa antes de usar esta view em qualquer relatório.';
