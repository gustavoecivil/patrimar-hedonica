-- Patrimar Pricing Intelligence — Schema canônico v2
-- audit: proveniência (data_sources) e linhagem (data_lineage) de dados.
-- Nenhuma tabela deste arquivo contém dado de negócio ou valor privado.
--
-- Também adiciona, via ALTER TABLE, as foreign keys de core/pricing para
-- audit.data_sources que não puderam ser declaradas inline nos arquivos
-- 002/003 (audit ainda não existia naquele ponto da execução ordenada).

CREATE TABLE audit.data_sources (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code              TEXT NOT NULL UNIQUE,
  name              TEXT NOT NULL,
  source_url        TEXT,
  origin_type       TEXT NOT NULL CHECK (origin_type IN ('real','imputed','synthetic','hybrid')),
  methodology_note  TEXT,
  accessed_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE audit.data_sources IS
  'Equivalente v2 de data_sources do schema legado (database/schema.sql) — mesmo conceito, novo namespace.';

CREATE TABLE audit.data_lineage (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_schema   TEXT NOT NULL,     -- ex.: 'core', 'pricing'
  entity_table    TEXT NOT NULL,     -- ex.: 'units'
  entity_id       UUID NOT NULL,     -- referência polimórfica — sem FK física, ver nota abaixo
  data_source_id  UUID NOT NULL REFERENCES audit.data_sources(id),
  field_name      TEXT,              -- opcional, quando a linhagem é a nível de campo
  derived_from    TEXT,              -- descrição genérica da derivação (nunca fórmula/valor privado)
  recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE audit.data_lineage IS
  'Responde "de onde veio este valor?" para qualquer entidade do schema. entity_id é uma referência '
  'polimórfica (aponta para linhas de tabelas diferentes conforme entity_schema/entity_table) — '
  'intencionalmente sem foreign key física, é um trade-off padrão desse tipo de tabela genérica de auditoria.';

-- audit.decisions (aprovação/revisão humana formal) é deixado para fase
-- futura — ver docs/11-DATABASE-V2-DESIGN.md. pricing.unit_overrides já
-- cobre a decisão de override em si; um fluxo de aprovação formal
-- (quem revisou, quando, se aprovou) ainda não tem requisito confirmado.

ALTER TABLE core.developments
  ADD CONSTRAINT fk_developments_data_source
  FOREIGN KEY (data_source_id) REFERENCES audit.data_sources(id);

ALTER TABLE core.units
  ADD CONSTRAINT fk_units_data_source
  FOREIGN KEY (data_source_id) REFERENCES audit.data_sources(id);

ALTER TABLE pricing.parameters
  ADD CONSTRAINT fk_parameters_data_source
  FOREIGN KEY (data_source_id) REFERENCES audit.data_sources(id);
