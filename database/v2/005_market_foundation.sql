-- Patrimar Pricing Intelligence — Schema canônico v2
-- market: fundação mínima e extensível do Market Pricing Engine (Motor A — D7).
--
-- Deliberadamente NÃO cria: market.observations, market.comparables,
-- market.transactions, market.listings. Nenhuma fonte real de
-- comparáveis/transações/ofertas existe hoje em nenhuma parte do
-- projeto (confirmado na Fase 1C/1D) — criar essas tabelas agora
-- significaria adivinhar uma estrutura sem evidência. Ver
-- docs/11-DATABASE-V2-DESIGN.md, seção "Camadas futuras", para o
-- desenho documentado (não implementado) dessas entidades.
--
-- O que É criado agora é genérico o suficiente para não presumir nada
-- sobre a fonte de dado de mercado: apenas o conceito de "existe um
-- modelo, com versões, que produz previsões" — infraestrutura que o
-- laboratório hedônico legado já demanda implicitamente (hoje ele
-- recalcula tudo em memória no navegador, sem persistir nada disso).

CREATE TABLE market.models (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code         TEXT NOT NULL UNIQUE,
  name         TEXT NOT NULL,
  description  TEXT,
  model_type   TEXT,          -- rótulo genérico e extensível, ex.: 'HEDONIC_OLS', 'ML_REGRESSION'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE market.models IS
  'Um modelo de estimativa de mercado (ex.: o laboratório hedônico legado, formalizado como uma entrada aqui).';

CREATE TABLE market.model_versions (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_id           UUID NOT NULL REFERENCES market.models(id),
  version_label      TEXT NOT NULL,
  status             TEXT NOT NULL DEFAULT 'DRAFT'
                       CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')),
  trained_at         TIMESTAMPTZ,
  methodology_note   TEXT,
  data_source_id     UUID REFERENCES audit.data_sources(id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_model_versions_model_label UNIQUE (model_id, version_label)
);
COMMENT ON TABLE market.model_versions IS 'Versão treinada/calibrada de um modelo. Granularidade: MODEL_RUN.';

CREATE TABLE market.predictions (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version_id       UUID NOT NULL REFERENCES market.model_versions(id),
  development_id         UUID REFERENCES core.developments(id),
  unit_id                UUID REFERENCES core.units(id),
  predicted_price_per_m2 NUMERIC(12,2),
  predicted_vgv          NUMERIC(18,2),
  confidence_low         NUMERIC(18,2),
  confidence_high        NUMERIC(18,2),
  reference_date         DATE NOT NULL,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_predictions_target CHECK (development_id IS NOT NULL OR unit_id IS NOT NULL)
);
COMMENT ON TABLE market.predictions IS
  'Estimativa de valor de mercado produzida por uma versão de modelo — o ponto de integração conceitual com '
  'o Motor B (pricing.vgv_targets.market_prediction_id).';

ALTER TABLE pricing.vgv_targets
  ADD CONSTRAINT fk_vgv_targets_market_prediction
  FOREIGN KEY (market_prediction_id) REFERENCES market.predictions(id);
