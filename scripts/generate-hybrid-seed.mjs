import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const inlineScripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).join('\n');
const context = {
  window: { HEDONIC_API_CONFIG: null, addEventListener() {}, matchMedia: () => ({ addEventListener() {}, matches: false }) },
  document: {}, console, Math, setTimeout, clearTimeout, AbortController, fetch
};
vm.createContext(context);
vm.runInContext(`${inlineScripts}\nthis.__seed = generateSampleData();`, context);

const columns = [
  'id','empreendimento','apartamento','bairro','torre','andar','area','quartos','vagas','suite',
  'varanda_m2','cobertura','vista','orientacao','posicao','padrao_score','lazer_score',
  'localizacao_score','fase_obra','meses_lancamento','desconto_pct','preco_m2','origem'
];
const escapeCsv = value => `"${String(value ?? '').replaceAll('"','""')}"`;
const csv = [columns.join(','), ...context.__seed.map(row => columns.map(c => escapeCsv(row[c])).join(','))].join('\n');
fs.mkdirSync(new URL('../data/', import.meta.url), { recursive: true });
fs.writeFileSync(new URL('../data/hedonic_seed_hybrid.csv', import.meta.url), `${csv}\n`);
console.log(`Generated ${context.__seed.length} rows.`);
