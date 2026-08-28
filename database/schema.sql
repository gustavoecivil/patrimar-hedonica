BEGIN;

CREATE TABLE IF NOT EXISTS data_sources (
  id BIGSERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  source_url TEXT,
  origin_type TEXT NOT NULL CHECK (origin_type IN ('real','imputed','synthetic','hybrid')),
  methodology_note TEXT,
  accessed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS developments (
  id TEXT PRIMARY KEY,
  name TEXT,
  city TEXT NOT NULL DEFAULT 'Belo Horizonte',
  state CHAR(2) NOT NULL DEFAULT 'MG',
  bairro TEXT NOT NULL,
  stage TEXT NOT NULL CHECK (stage IN ('lancamento','construcao','acabamento','pronto')),
  launch_date DATE,
  completion_date DATE,
  total_floors INTEGER CHECK (total_floors > 0),
  quality_score NUMERIC(3,1) CHECK (quality_score BETWEEN 1 AND 5),
  amenities_score NUMERIC(3,1) CHECK (amenities_score BETWEEN 1 AND 5),
  location_score NUMERIC(3,1) CHECK (location_score BETWEEN 1 AND 5),
  latitude NUMERIC(9,6),
  longitude NUMERIC(9,6),
  source_id BIGINT REFERENCES data_sources(id)
);

CREATE TABLE IF NOT EXISTS units (
  id BIGSERIAL PRIMARY KEY,
  development_id TEXT NOT NULL REFERENCES developments(id),
  apartment TEXT NOT NULL,
  tower TEXT NOT NULL DEFAULT 'T1',
  floor INTEGER NOT NULL CHECK (floor > 0),
  private_area_m2 NUMERIC(9,2) NOT NULL CHECK (private_area_m2 > 0),
  bedrooms INTEGER CHECK (bedrooms >= 0),
  suites INTEGER CHECK (suites >= 0),
  parking_spaces INTEGER CHECK (parking_spaces >= 0),
  balcony_area_m2 NUMERIC(8,2) CHECK (balcony_area_m2 >= 0),
  is_penthouse BOOLEAN NOT NULL DEFAULT FALSE,
  view_type TEXT NOT NULL CHECK (view_type IN ('rua','parque','mar')),
  orientation CHAR(1) NOT NULL CHECK (orientation IN ('N','S','L','O')),
  position_type TEXT NOT NULL CHECK (position_type IN ('frente','fundos','lateral')),
  source_id BIGINT REFERENCES data_sources(id),
  UNIQUE (development_id,tower,apartment)
);

CREATE TABLE IF NOT EXISTS unit_price_observations (
  id BIGSERIAL PRIMARY KEY,
  unit_id BIGINT NOT NULL REFERENCES units(id),
  reference_date DATE NOT NULL,
  months_since_launch INTEGER CHECK (months_since_launch >= 0),
  asking_price NUMERIC(15,2),
  transaction_price NUMERIC(15,2),
  price_m2 NUMERIC(12,2) NOT NULL CHECK (price_m2 > 0),
  discount_pct NUMERIC(6,2),
  first_sale BOOLEAN NOT NULL DEFAULT TRUE,
  record_origin TEXT NOT NULL CHECK (record_origin IN ('real','imputed','synthetic','hybrid')),
  source_id BIGINT REFERENCES data_sources(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (unit_id,reference_date,source_id)
);

CREATE INDEX IF NOT EXISTS idx_units_development ON units(development_id);
CREATE INDEX IF NOT EXISTS idx_prices_reference_date ON unit_price_observations(reference_date);
CREATE INDEX IF NOT EXISTS idx_prices_first_sale ON unit_price_observations(first_sale) WHERE first_sale;

CREATE OR REPLACE VIEW v_hedonic_model AS
SELECT
  p.id, d.id AS empreendimento, u.apartment AS apartamento, d.bairro, u.tower AS torre,
  u.floor AS andar, u.private_area_m2 AS area, u.bedrooms AS quartos,
  u.parking_spaces AS vagas, u.suites AS suite, u.balcony_area_m2 AS varanda_m2,
  CASE WHEN u.is_penthouse THEN 1 ELSE 0 END AS cobertura,
  u.view_type AS vista, u.orientation AS orientacao, u.position_type AS posicao,
  d.quality_score AS padrao_score, d.amenities_score AS lazer_score,
  d.location_score AS localizacao_score, d.stage AS fase_obra,
  p.months_since_launch AS meses_lancamento, p.discount_pct, p.price_m2 AS preco_m2,
  p.record_origin AS origem, p.reference_date
FROM unit_price_observations p
JOIN units u ON u.id=p.unit_id
JOIN developments d ON d.id=u.development_id
WHERE p.first_sale = TRUE;

COMMIT;
