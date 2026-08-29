import fs from 'node:fs';

const inputUrl = new URL('../data/hedonic_seed_hybrid.csv', import.meta.url);
const outputUrl = new URL('../netlify/database/migrations/20260829090100_seed_hybrid_model.sql', import.meta.url);

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        value += '"';
        i += 1;
      } else if (char === '"') quoted = false;
      else value += char;
    } else if (char === '"') quoted = true;
    else if (char === ',') {
      row.push(value);
      value = '';
    } else if (char === '\n') {
      row.push(value.replace(/\r$/, ''));
      rows.push(row);
      row = [];
      value = '';
    } else value += char;
  }
  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }
  const [headers, ...data] = rows;
  return data.filter(r => r.length === headers.length).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i]])));
}

const quote = value => `'${String(value).replaceAll("'", "''")}'`;
const number = value => String(Number(value));
const boolean = value => value === '1' ? 'TRUE' : 'FALSE';
const rows = parseCsv(fs.readFileSync(inputUrl, 'utf8'));

const values = rows.map(row => `(${[
  quote(row.empreendimento), quote(row.apartamento), quote(row.bairro), quote(row.torre),
  number(row.andar), number(row.area), number(row.quartos), number(row.vagas), number(row.suite),
  number(row.varanda_m2), boolean(row.cobertura), quote(row.vista), quote(row.orientacao),
  quote(row.posicao), number(row.padrao_score), number(row.lazer_score), number(row.localizacao_score),
  quote(row.fase_obra), number(row.meses_lancamento), number(row.desconto_pct), number(row.preco_m2)
].join(', ')})`).join(',\n');

const sql = `INSERT INTO data_sources (code, name, origin_type, methodology_note, accessed_at)
VALUES (
  'seed-hybrid-v1',
  'Base híbrida calibrada Patrimar',
  'hybrid',
  'Dados sintéticos não lineares calibrados para validação técnica; substituir por dados reais do cliente.',
  TIMESTAMPTZ '2026-08-29 00:00:00+00'
)
ON CONFLICT (code) DO NOTHING;

CREATE TEMP TABLE seed_hedonic (
  empreendimento TEXT, apartamento TEXT, bairro TEXT, torre TEXT, andar INTEGER,
  area NUMERIC, quartos INTEGER, vagas INTEGER, suite INTEGER, varanda_m2 NUMERIC,
  cobertura BOOLEAN, vista TEXT, orientacao CHAR(1), posicao TEXT,
  padrao_score NUMERIC, lazer_score NUMERIC, localizacao_score NUMERIC,
  fase_obra TEXT, meses_lancamento INTEGER, desconto_pct NUMERIC, preco_m2 NUMERIC
) ON COMMIT DROP;

INSERT INTO seed_hedonic VALUES
${values};

INSERT INTO developments (
  id, name, bairro, stage, total_floors, quality_score, amenities_score,
  location_score, source_id
)
SELECT
  s.empreendimento,
  'Empreendimento ' || s.empreendimento,
  MIN(s.bairro),
  MIN(s.fase_obra),
  MAX(s.andar),
  MIN(s.padrao_score),
  MIN(s.lazer_score),
  MIN(s.localizacao_score),
  ds.id
FROM seed_hedonic s
CROSS JOIN data_sources ds
WHERE ds.code = 'seed-hybrid-v1'
GROUP BY s.empreendimento, ds.id
ON CONFLICT (id) DO NOTHING;

INSERT INTO units (
  development_id, apartment, tower, floor, private_area_m2, bedrooms, suites,
  parking_spaces, balcony_area_m2, is_penthouse, view_type, orientation,
  position_type, source_id
)
SELECT
  s.empreendimento, s.apartamento, s.torre, s.andar, s.area, s.quartos, s.suite,
  s.vagas, s.varanda_m2, s.cobertura, s.vista, s.orientacao, s.posicao, ds.id
FROM seed_hedonic s
CROSS JOIN data_sources ds
WHERE ds.code = 'seed-hybrid-v1'
ON CONFLICT (development_id, tower, apartment) DO NOTHING;

INSERT INTO unit_price_observations (
  unit_id, reference_date, months_since_launch, price_m2, discount_pct,
  first_sale, record_origin, source_id
)
SELECT
  u.id,
  DATE '2026-08-29',
  s.meses_lancamento,
  s.preco_m2,
  s.desconto_pct,
  TRUE,
  'hybrid',
  ds.id
FROM seed_hedonic s
JOIN units u ON u.development_id = s.empreendimento
            AND u.tower = s.torre
            AND u.apartment = s.apartamento
CROSS JOIN data_sources ds
WHERE ds.code = 'seed-hybrid-v1'
ON CONFLICT (unit_id, reference_date, source_id) DO NOTHING;
`;

fs.mkdirSync(new URL('../netlify/database/migrations/', import.meta.url), { recursive: true });
fs.writeFileSync(outputUrl, sql);
console.log(`Generated seed migration with ${rows.length} rows.`);
