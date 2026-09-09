-- Patrimar Pricing Intelligence — Schema canônico v2
-- core: cadastro físico estável (empreendimento, torre, tipologia, unidade).
--
-- Princípios aplicados (ver database/v2/README.md):
--   * UUID como identidade técnica; business key separada e única.
--   * Colunas tipadas para atributos essenciais/estáveis — sem EAV
--     genérico (avaliado e descartado, ver README seção "core.unit_attributes").
--   * data_source_id fica sem FK física aqui (audit é criado depois, no
--     arquivo 004); a FK é adicionada via ALTER TABLE em 004_audit.sql.

CREATE TABLE core.developments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_key    TEXT NOT NULL,                 -- código externo/legado, ex.: identificador do empreendimento
  name            TEXT,
  city            TEXT NOT NULL DEFAULT 'Belo Horizonte',
  state           CHAR(2) NOT NULL DEFAULT 'MG',
  bairro          TEXT,
  launch_date     DATE,
  completion_date DATE,
  total_floors    INTEGER CHECK (total_floors IS NULL OR total_floors > 0),
  latitude        NUMERIC(9,6),
  longitude       NUMERIC(9,6),
  data_source_id  UUID,                          -- FK -> audit.data_sources adicionada em 004_audit.sql
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_developments_business_key UNIQUE (business_key)
);
COMMENT ON TABLE core.developments IS 'Empreendimento. Granularidade: DEVELOPMENT.';
COMMENT ON COLUMN core.developments.business_key IS
  'Identificador de negócio (não o id técnico) — ex.: código do empreendimento usado externamente.';

CREATE TABLE core.towers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  development_id  UUID NOT NULL REFERENCES core.developments(id),
  business_key    TEXT NOT NULL,                 -- ex.: identificador de torre/bloco na fonte original
  name            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_towers_dev_business_key UNIQUE (development_id, business_key)
);
COMMENT ON TABLE core.towers IS 'Torre/bloco dentro de um empreendimento. Granularidade: TOWER.';

CREATE TABLE core.unit_typologies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  development_id  UUID NOT NULL REFERENCES core.developments(id),
  business_key    TEXT NOT NULL,                 -- rótulo de tipologia na fonte original (ex.: categoria de quartos/suítes)
  name            TEXT,
  bedrooms        INTEGER CHECK (bedrooms IS NULL OR bedrooms >= 0),
  suites          INTEGER CHECK (suites IS NULL OR suites >= 0),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_typologies_dev_business_key UNIQUE (development_id, business_key)
);
COMMENT ON TABLE core.unit_typologies IS
  'Tipologia de unidade (poucas linhas por empreendimento — tabela de referência, não EAV). Granularidade: TYPOLOGY.';

CREATE TABLE core.units (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  development_id         UUID NOT NULL REFERENCES core.developments(id),
  tower_id               UUID REFERENCES core.towers(id),
  unit_typology_id       UUID REFERENCES core.unit_typologies(id),
  unit_code              TEXT NOT NULL,          -- identificador da unidade na fonte original — NÃO globalmente único
  floor                  INTEGER CHECK (floor IS NULL OR floor > 0),
  position_code          TEXT,                   -- atributo genérico de posição/lado (Q-05 pendente — ver README)
  closed_area_m2         NUMERIC(9,2) NOT NULL CHECK (closed_area_m2 >= 0),
  balcony_area_m2        NUMERIC(9,2) NOT NULL DEFAULT 0 CHECK (balcony_area_m2 >= 0),
  ancillary_area_m2      NUMERIC(9,2) NOT NULL DEFAULT 0 CHECK (ancillary_area_m2 >= 0),
  open_terrace_area_m2   NUMERIC(9,2) NOT NULL DEFAULT 0 CHECK (open_terrace_area_m2 >= 0),
  total_area_m2          NUMERIC(9,2) GENERATED ALWAYS AS
                           (closed_area_m2 + balcony_area_m2 + ancillary_area_m2 + open_terrace_area_m2) STORED,
  parking_spaces         INTEGER CHECK (parking_spaces IS NULL OR parking_spaces >= 0),
  view_type              TEXT,
  orientation            CHAR(1) CHECK (orientation IS NULL OR orientation IN ('N','S','L','O')),
  position_type          TEXT CHECK (position_type IS NULL OR position_type IN ('frente','fundos','lateral')),
  is_penthouse           BOOLEAN NOT NULL DEFAULT FALSE,
  data_source_id         UUID,                   -- FK -> audit.data_sources adicionada em 004_audit.sql
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_units_dev_tower_code UNIQUE (development_id, tower_id, unit_code)
);
COMMENT ON TABLE core.units IS 'Unidade física. Granularidade: UNIT. Núcleo de ambos os motores (D7).';
COMMENT ON COLUMN core.units.unit_code IS
  'Identificador da unidade como aparece na fonte (ex.: número do apartamento). Deficiência conhecida (Fase 1): '
  'não é comprovadamente único isoladamente — a unicidade é garantida apenas junto de development_id/tower_id.';
COMMENT ON CONSTRAINT uq_units_dev_tower_code ON core.units IS
  'Quando tower_id é NULL (torre não confirmada), o Postgres não trata NULLs como iguais, então esta constraint '
  'não garante unicidade de unit_code nesse caso — limitação documentada, não um bug (ver README).';
COMMENT ON COLUMN core.units.position_code IS
  'Atributo de posição/lado usado para localizar a unidade numa matriz de calibração. Rotulagem genérica '
  'proposital: o significado exato do atributo lateral usado na metodologia observada ainda não foi confirmado '
  '(pergunta bloqueante de schema, ver database/v2/README.md).';
COMMENT ON COLUMN core.units.parking_spaces IS
  'Simplificação conhecida: a fonte observada categoriza vaga por tipo (livre/presa, combinações), não por '
  'contagem simples. Esta coluna guarda apenas uma contagem — ver database/v2/README.md, "Decisões adiadas".';

-- Invariante estrutural: se a unidade referencia uma torre, essa torre
-- precisa pertencer ao mesmo empreendimento da unidade. Não é expressável
-- como CHECK de linha (depende de outra tabela); implementado como
-- trigger simples (não complexa) em vez de deixado só para a camada de
-- serviço, porque é uma verificação de uma única igualdade.
CREATE OR REPLACE FUNCTION core.fn_check_unit_tower_development()
RETURNS TRIGGER AS $$
DECLARE
  tower_dev UUID;
BEGIN
  IF NEW.tower_id IS NOT NULL THEN
    SELECT development_id INTO tower_dev FROM core.towers WHERE id = NEW.tower_id;
    IF tower_dev IS DISTINCT FROM NEW.development_id THEN
      RAISE EXCEPTION 'core.units: tower_id % pertence a development % diferente de development_id %',
        NEW.tower_id, tower_dev, NEW.development_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_units_tower_development_consistency
  BEFORE INSERT OR UPDATE ON core.units
  FOR EACH ROW EXECUTE FUNCTION core.fn_check_unit_tower_development();
