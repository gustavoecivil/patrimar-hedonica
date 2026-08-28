import fs from 'node:fs';
import vm from 'node:vm';

const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
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
console.log(JSON.stringify({rows:data.length,R2:model.R2,RMSE_test:model.rmseTest,MAPE_test:model.mapeTest,max_VIF:model.maxVIF}));
