import type { Config } from '@netlify/functions';
import pg from 'pg';

const { Pool } = pg;
let pool: pg.Pool | undefined;

function getPool() {
  const connectionString = Netlify.env.get('DATABASE_URL');
  if (!connectionString) throw new Error('DATABASE_URL não configurada');
  pool ??= new Pool({
    connectionString,
    ssl: Netlify.env.get('PGSSL') === 'disable' ? false : true,
    max: 4,
    idleTimeoutMillis: 10000
  });
  return pool;
}

export default async (request: Request) => {
  if (request.method !== 'GET') return new Response('Method Not Allowed', { status: 405 });
  try {
    const url = new URL(request.url);
    const limit = Math.min(Math.max(Number(url.searchParams.get('limit')) || 5000, 50), 20000);
    const result = await getPool().query(
      'SELECT * FROM v_hedonic_model ORDER BY empreendimento, torre, andar, apartamento LIMIT $1',
      [limit]
    );
    return Response.json({ data: result.rows, count: result.rowCount, source: 'postgresql' }, {
      headers: { 'Cache-Control': 'public, max-age=60, stale-while-revalidate=300' }
    });
  } catch (error) {
    console.error('hedonic-data:', error instanceof Error ? error.message : 'erro desconhecido');
    return Response.json({ error: 'Não foi possível consultar a base hedônica.' }, { status: 500 });
  }
};

export const config: Config = { path: '/api/hedonic-data', method: 'GET' };
