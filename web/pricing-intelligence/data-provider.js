/* Patrimar Pricing Intelligence — Data Provider
 *
 * Camada única de acesso a dados. O resto da interface nunca sabe se
 * os dados vieram do modo PRIVATE (servidor local, dados reais) ou
 * DEMO (arquivo estático sintético, publicado no Netlify).
 *
 * Regras obrigatórias:
 *  - O modo PRIVATE só é sequer OFERECIDO quando a página está rodando
 *    em localhost/127.0.0.1 — nunca em produção (Netlify).
 *  - Nunca há fallback automático de DEMO para PRIVATE nem de PRIVATE
 *    para DEMO — a troca de modo é sempre uma ação explícita da
 *    pessoa usuária.
 *  - O servidor PRIVATE só é acessado em 127.0.0.1 — este arquivo
 *    nunca contém nenhuma credencial, connection string ou dado real.
 */

const PRIVATE_API_BASE = 'http://127.0.0.1:8765';
const DEMO_DATA_URL = 'demo-data.json';

function isLocalHost() {
  const h = window.location.hostname;
  return h === 'localhost' || h === '127.0.0.1' || h === '';
}

class DataProvider {
  constructor() {
    this.mode = 'DEMO';
    this._cache = null;
  }

  privateModeAvailable() {
    return isLocalHost();
  }

  async setMode(mode) {
    if (mode === 'PRIVATE' && !this.privateModeAvailable()) {
      throw new Error('Modo PRIVATE só está disponível rodando localmente.');
    }
    this.mode = mode;
    this._cache = null;
  }

  async _loadDemo() {
    const res = await fetch(DEMO_DATA_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('Não foi possível carregar o dataset de demonstração.');
    return res.json();
  }

  async _loadPrivate() {
    const res = await fetch(`${PRIVATE_API_BASE}/api/dataset`, { cache: 'no-store' });
    if (!res.ok) throw new Error('Servidor PRIVATE local não respondeu. Rode scripts/pricing_preview_server.py.');
    return res.json();
  }

  async getDataset() {
    if (this._cache) return this._cache;
    this._cache = this.mode === 'PRIVATE' ? await this._loadPrivate() : await this._loadDemo();
    return this._cache;
  }
}

window.dataProvider = new DataProvider();
