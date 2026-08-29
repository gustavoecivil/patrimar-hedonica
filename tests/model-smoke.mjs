import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
const netlifyFunction=fs.readFileSync(new URL('../netlify/functions/hedonic-data.mts',import.meta.url),'utf8');
const schemaMigration=fs.readFileSync(new URL('../netlify/database/migrations/20260829090000_create_hedonic_schema.sql',import.meta.url),'utf8');
const seedMigration=fs.readFileSync(new URL('../netlify/database/migrations/20260829090100_seed_hybrid_model.sql',import.meta.url),'utf8');
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const context={window:{HEDONIC_API_CONFIG:null,addEventListener(){},matchMedia:()=>({addEventListener(){},matches:false})},document:{},console,Math,setTimeout,clearTimeout,AbortController,fetch};
vm.createContext(context);
vm.runInContext(`${scripts}\nthis.__data=generateSampleData();this.__model=runOLS(this.__data);`,context);

const {__data:data,__model:model}=context;
if(data.length<500) throw new Error('Base híbrida pequena demais');
if(new Set(data.map(row=>row.empreendimento)).size<10) throw new Error('Poucos empreendimentos');
if(!model.beta.every(Number.isFinite)) throw new Error('Coeficientes inválidos');
if(model.testN<100) throw new Error('Amostra de teste insuficiente');
if(model.mapeTest<=5 || model.mapeTest>=25) throw new Error(`MAPE fora da faixa realista: ${model.mapeTest}`);
if(model.R2>=.98) throw new Error('Ajuste artificialmente perfeito');
if(!netlifyFunction.includes("from '@netlify/database'")) throw new Error('Função não usa Netlify Database');
if(netlifyFunction.includes('DATABASE_URL')) throw new Error('Função ainda depende de DATABASE_URL manual');
if(!schemaMigration.includes('CREATE OR REPLACE VIEW v_hedonic_model')) throw new Error('Migração do esquema incompleta');
if((seedMigration.match(/\('NOVO-/g) || []).length !== data.length) throw new Error('Migração seed não contém todas as unidades');
console.log(JSON.stringify({rows:data.length,R2:model.R2,RMSE_test:model.rmseTest,MAPE_test:model.mapeTest,max_VIF:model.maxVIF}));
