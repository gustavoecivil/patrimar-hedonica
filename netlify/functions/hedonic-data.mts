import type { Config } from '@netlify/functions';
import { getDatabase } from '@netlify/database';

export default async (request: Request) => {
  if (request.method !== 'GET') return new Response('Method Not Allowed', { status: 405 });
  try {
    const url = new URL(request.url);
    const limit = Math.min(Math.max(Number(url.searchParams.get('limit')) || 5000, 50), 20000);
    const db = getDatabase();
    const rows = await db.sql`
      SELECT *
      FROM v_hedonic_model
      ORDER BY empreendimento, torre, andar, apartamento
      LIMIT ${limit}
    `;
    return Response.json({ data: rows, count: rows.length, source: 'netlify-postgresql' }, {
      headers: { 'Cache-Control': 'public, max-age=60, stale-while-revalidate=300' }
    });
  } catch (error) {
    console.error('hedonic-data:', error instanceof Error ? error.message : 'erro desconhecido');
    return Response.json({ error: 'Não foi possível consultar a base hedônica.' }, { status: 500 });
  }
};

export const config: Config = { path: '/api/hedonic-data', method: 'GET' };
