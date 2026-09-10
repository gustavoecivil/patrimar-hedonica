/* Patrimar Pricing Intelligence — App
 * Vanilla JS, sem framework. Usa Chart.js (já usado no laboratório
 * legado) só para os gráficos. Toda leitura de dado passa por
 * window.dataProvider (data-provider.js) — esta camada nunca sabe se
 * o dado é PRIVATE ou DEMO. */

(function () {
  'use strict';

  const state = { dataset: null, unitsFiltered: [], sortKey: 'unit_code', sortDir: 1, page: 1, pageSize: 25, search: '', filterStatus: 'TODOS', charts: {} };

  const fmtMoney = (v) => {
    const n = Number(v || 0);
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 });
  };
  const fmtNum = (v, d = 2) => Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
  const fmtInt = (v) => Number(v || 0).toLocaleString('pt-BR');
  const fmtOrDash = (v, d = 2) => (v == null ? '—' : fmtNum(v, d));
  const orDash = (v) => (v == null || v === '' ? '—' : v);

  /* ── THEME ─────────────────────────────────────────── */
  window.toggleTheme = function () {
    const cur = document.documentElement.getAttribute('data-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (cur === 'dark' || (!cur && prefersDark)) {
      document.documentElement.setAttribute('data-theme', 'light');
      localStorage.setItem('pi-theme', 'light');
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('pi-theme', 'dark');
    }
    renderCharts();
  };
  (function initTheme() {
    const saved = localStorage.getItem('pi-theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
  })();

  /* ── MOBILE NAV ───────────────────────────────────── */
  window.toggleSidebar = function (force) {
    const sb = document.querySelector('.sidebar');
    const ov = document.querySelector('.sidebar-overlay');
    const open = force !== undefined ? force : !sb.classList.contains('open');
    sb.classList.toggle('open', open);
    ov.classList.toggle('open', open);
  };

  /* ── NAVIGATION ───────────────────────────────────── */
  const VIEWS = ['visao-geral', 'unidades', 'precificacao', 'validacao', 'auditoria', 'mercado'];
  window.switchView = function (view, el) {
    VIEWS.forEach((v) => document.getElementById('view-' + v).style.display = v === view ? '' : 'none');
    document.querySelectorAll('.nav-item[data-view]').forEach((n) => n.classList.toggle('active', n === el));
    window.toggleSidebar(false);
    if (view === 'visao-geral') renderCharts();
  };

  /* ── DATA MODE ────────────────────────────────────── */
  window.setDataMode = async function (mode) {
    try {
      await window.dataProvider.setMode(mode);
      document.querySelectorAll('.mode-btn').forEach((b) => b.classList.toggle('active', b.dataset.mode === mode));
      await loadAndRender();
    } catch (err) {
      console.error('[setDataMode]', err);
      document.getElementById('kpi-cards').innerHTML = `<div class="empty-state"><p>Não foi possível carregar os dados.</p><div class="hint">${err.message}</div></div>`;
    }
  };

  /* ── LOAD + RENDER ────────────────────────────────── */
  async function loadAndRender() {
    const dataset = await window.dataProvider.getDataset();
    state.dataset = dataset;
    document.getElementById('demo-banner').style.display = dataset.meta.mode === 'DEMO' ? 'flex' : 'none';
    document.getElementById('private-mode-item').style.display = window.dataProvider.privateModeAvailable() ? '' : 'none';
    document.getElementById('poc-mode-note').textContent = dataset.meta.mode === 'PRIVATE'
      ? 'POC • Dados privados locais' : 'POC • Dados sintéticos';
    renderKpis();
    renderCharts();
    applyUnitFilters();
    renderValidation();
    renderAuditoria();
    document.getElementById('prec-towers').textContent = dataset.towers.join(', ') || '—';
    document.getElementById('prec-typologies').textContent = dataset.typologies.join(', ') || '—';
  }

  /* ── KPIs ─────────────────────────────────────────── */
  function renderKpis() {
    const k = state.dataset.kpis;
    const box = document.getElementById('kpi-cards');
    box.innerHTML = `
      <div class="stat-box highlight"><div class="label">VGV</div><div class="value">${fmtMoney(k.vgv)}</div><div class="hint">Valor Geral de Vendas</div></div>
      <div class="stat-box"><div class="label">Unidades</div><div class="value">${fmtInt(k.units_count)}</div><div class="hint">${state.dataset.towers.length} torre(s) · ${state.dataset.typologies.length} tipologia(s)</div></div>
      <div class="stat-box"><div class="label">Preço médio / m²</div><div class="value">${fmtMoney(k.avg_price_per_m2)}</div></div>
      <div class="stat-box"><div class="label">Torres</div><div class="value">${fmtInt(k.towers_count)}</div></div>
      <div class="stat-box"><div class="label">Ajustes humanos</div><div class="value">${fmtInt(k.adjustments_count)}</div><div class="hint">${((k.adjustments_count / k.units_count) * 100).toFixed(1)}% das unidades</div></div>
      <div class="stat-box"><div class="label">Precisão da reprodução</div><div class="value text-good">${k.reproduction_accuracy_pct}%</div><div class="hint">${fmtInt(k.within_1_cent_count)} de ${fmtInt(k.units_count)} unidades dentro de R$ 0,01</div></div>
    `;
  }

  /* ── CHARTS ───────────────────────────────────────── */
  function chartColors() {
    const css = getComputedStyle(document.documentElement);
    return {
      navy: css.getPropertyValue('--navy').trim() || '#003258',
      gold: css.getPropertyValue('--gold').trim() || '#C49A22',
      good: css.getPropertyValue('--good').trim() || '#165E3A',
      muted: css.getPropertyValue('--muted').trim() || '#5A6070',
      grid: css.getPropertyValue('--border').trim() || '#D8D8D5',
      text: css.getPropertyValue('--text').trim() || '#0B1020',
    };
  }

  function destroyChart(id) { if (state.charts[id]) { state.charts[id].destroy(); delete state.charts[id]; } }

  function renderCharts() {
    if (!state.dataset) return;
    const units = state.dataset.units;
    const colors = chartColors();
    const baseOpts = {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { font: { family: "'Poppins', sans-serif", size: 11 }, color: colors.text } } },
      scales: {
        x: { grid: { color: colors.grid }, ticks: { color: colors.muted, font: { size: 10, family: "'Poppins', sans-serif" } } },
        y: { grid: { color: colors.grid }, ticks: { color: colors.muted, font: { size: 10, family: "'Poppins', sans-serif" } } },
      },
    };

    // Preço/m² por pavimento (unidades sem pavimento conhecido são ignoradas neste gráfico)
    const byFloor = {};
    units.forEach((u) => { if (u.floor == null) return; (byFloor[u.floor] = byFloor[u.floor] || []).push(Number(u.price_per_m2)); });
    const floors = Object.keys(byFloor).map(Number).sort((a, b) => a - b);
    destroyChart('floor');
    document.getElementById('chart-floor').style.display = floors.length ? '' : 'none';
    document.getElementById('chart-floor-empty').style.display = floors.length ? 'none' : '';
    if (floors.length) {
      state.charts.floor = new Chart(document.getElementById('chart-floor'), {
        type: 'line',
        data: { labels: floors, datasets: [{ label: 'Preço médio/m² por pavimento', data: floors.map((f) => byFloor[f].reduce((a, b) => a + b, 0) / byFloor[f].length), borderColor: colors.navy, backgroundColor: colors.navy, tension: .25 }] },
        options: baseOpts,
      });
    }

    // Preço x área
    destroyChart('scatter');
    state.charts.scatter = new Chart(document.getElementById('chart-scatter'), {
      type: 'scatter',
      data: { datasets: [{ label: 'Unidades', data: units.map((u) => ({ x: Number(u.private_area_m2), y: Number(u.final_price) })), backgroundColor: colors.gold }] },
      options: baseOpts,
    });

    // Participação por torre
    const byTower = {};
    units.forEach((u) => { byTower[u.tower] = (byTower[u.tower] || 0) + Number(u.final_price); });
    destroyChart('tower');
    state.charts.tower = new Chart(document.getElementById('chart-tower'), {
      type: 'doughnut',
      data: { labels: Object.keys(byTower), datasets: [{ data: Object.values(byTower), backgroundColor: [colors.navy, colors.gold, colors.good, '#7B2F5E', '#B8850A'] }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: colors.text, font: { family: "'Poppins', sans-serif", size: 10 } } } } },
    });

    // Distribuição de preços (histograma simplificado)
    const prices = units.map((u) => Number(u.final_price)).sort((a, b) => a - b);
    const bins = 8;
    const min = prices[0], max = prices[prices.length - 1];
    const step = (max - min) / bins || 1;
    const hist = new Array(bins).fill(0);
    prices.forEach((p) => { const i = Math.min(bins - 1, Math.floor((p - min) / step)); hist[i]++; });
    destroyChart('dist');
    state.charts.dist = new Chart(document.getElementById('chart-dist'), {
      type: 'bar',
      data: { labels: hist.map((_, i) => fmtMoney(min + i * step).replace('R$', '').trim().slice(0, 6) + 'k+'), datasets: [{ label: 'Unidades', data: hist, backgroundColor: colors.navy }] },
      options: baseOpts,
    });

    // Ajustes humanos (waterfall simplificado: sistemático vs ajuste)
    const adjusted = units.filter((u) => Number(u.adjustment) !== 0);
    destroyChart('adjust');
    document.getElementById('chart-adjust').style.display = adjusted.length ? '' : 'none';
    document.getElementById('chart-adjust-empty').style.display = adjusted.length ? 'none' : '';
    if (adjusted.length) {
      state.charts.adjust = new Chart(document.getElementById('chart-adjust'), {
        type: 'bar',
        data: {
          labels: adjusted.map((u) => `${u.tower}/${u.unit_code}`),
          datasets: [
            { label: 'Preço sistemático', data: adjusted.map((u) => Number(u.system_price)), backgroundColor: colors.navy },
            { label: 'Ajuste', data: adjusted.map((u) => Number(u.adjustment)), backgroundColor: colors.gold },
          ],
        },
        options: { ...baseOpts, scales: { ...baseOpts.scales, x: { ...baseOpts.scales.x, stacked: true }, y: { ...baseOpts.scales.y, stacked: true } } },
      });
    }

    // Referência x Reprodução
    const val = state.dataset.validation.units.slice(0, 20);
    destroyChart('refrepro');
    state.charts.refrepro = new Chart(document.getElementById('chart-refrepro'), {
      type: 'line',
      data: {
        labels: val.map((v) => v.unit_code),
        datasets: [
          { label: 'Referência', data: val.map((v) => Number(v.reference_price)), borderColor: colors.navy, backgroundColor: colors.navy, pointRadius: 2 },
          { label: 'Reproduzido', data: val.map((v) => Number(v.reproduced_price)), borderColor: colors.gold, backgroundColor: colors.gold, pointRadius: 2, borderDash: [4, 3] },
        ],
      },
      options: baseOpts,
    });
  }

  /* ── UNIDADES TABLE ───────────────────────────────── */
  function applyUnitFilters() {
    if (!state.dataset) return;
    let rows = state.dataset.units.slice();
    if (state.search) {
      const s = state.search.toLowerCase();
      rows = rows.filter((u) => `${u.tower} ${u.unit_code} ${u.typology}`.toLowerCase().includes(s));
    }
    if (state.filterStatus !== 'TODOS') rows = rows.filter((u) => u.status === state.filterStatus);
    rows.sort((a, b) => {
      const av = a[state.sortKey], bv = b[state.sortKey];
      const an = Number(av), bn = Number(bv);
      const cmp = !isNaN(an) && !isNaN(bn) ? an - bn : String(av).localeCompare(String(bv));
      return cmp * state.sortDir;
    });
    state.unitsFiltered = rows;
    state.page = 1;
    renderUnitsTable();
  }

  function statusBadge(status) {
    const map = { VALIDADO: 'badge-good', AJUSTE: 'badge-warm', REVISAO: 'badge-muted' };
    return `<span class="badge ${map[status] || 'badge-muted'}">${status}</span>`;
  }

  function renderUnitsTable() {
    const tbody = document.getElementById('units-tbody');
    const totalPages = Math.max(1, Math.ceil(state.unitsFiltered.length / state.pageSize));
    state.page = Math.min(state.page, totalPages);
    const start = (state.page - 1) * state.pageSize;
    const pageRows = state.unitsFiltered.slice(start, start + state.pageSize);
    tbody.innerHTML = pageRows.map((u, i) => `
      <tr data-idx="${start + i}">
        <td>${u.tower}</td><td>${u.unit_code}</td><td>${orDash(u.typology)}</td>
        <td>${fmtNum(u.private_area_m2)} m²</td><td>${fmtNum(u.uncovered_area_m2)} m²</td>
        <td>${orDash(u.floor)}</td><td>${orDash(u.position)}</td>
        <td>${fmtMoney(u.price_per_m2)}</td><td>${fmtMoney(u.final_price)}</td>
        <td class="${Number(u.adjustment) !== 0 ? 'text-gold' : 'text-muted'}">${Number(u.adjustment) !== 0 ? fmtMoney(u.adjustment) : '—'}</td>
        <td>${statusBadge(u.status)}</td>
      </tr>`).join('') || '<tr><td colspan="11"><div class="empty-state"><div class="icon">🔍</div><p>Nenhuma unidade encontrada</p></div></td></tr>';

    tbody.querySelectorAll('tr[data-idx]').forEach((tr) => {
      tr.addEventListener('click', () => openUnitDrawer(state.unitsFiltered[Number(tr.dataset.idx)]));
    });

    const pager = document.getElementById('units-pager');
    pager.querySelector('.pager-info').textContent = `${state.unitsFiltered.length} unidade(s) · página ${state.page} de ${totalPages}`;
    const pagesEl = pager.querySelector('.pages');
    pagesEl.innerHTML = '';
    for (let p = 1; p <= totalPages; p++) {
      if (totalPages > 7 && p !== 1 && p !== totalPages && Math.abs(p - state.page) > 1) {
        if (p === 2 || p === totalPages - 1) pagesEl.insertAdjacentHTML('beforeend', '<span class="pg-btn" style="border:none">…</span>');
        continue;
      }
      const btn = document.createElement('button');
      btn.className = 'pg-btn' + (p === state.page ? ' active' : '');
      btn.textContent = p;
      btn.onclick = () => { state.page = p; renderUnitsTable(); };
      pagesEl.appendChild(btn);
    }
  }

  window.sortUnitsBy = function (key) {
    if (state.sortKey === key) state.sortDir *= -1; else { state.sortKey = key; state.sortDir = 1; }
    applyUnitFilters();
  };

  function bindTableControls() {
    document.getElementById('units-search').addEventListener('input', (e) => { state.search = e.target.value; applyUnitFilters(); });
    document.getElementById('units-status-filter').addEventListener('change', (e) => { state.filterStatus = e.target.value; applyUnitFilters(); });
  }

  /* ── DRAWER (detalhe da unidade) ──────────────────── */
  function openUnitDrawer(u) {
    const overlay = document.getElementById('unit-drawer-overlay');
    document.getElementById('drawer-title').textContent = `Unidade ${u.unit_code}`;
    document.getElementById('drawer-sub').textContent = `${u.tower} · ${orDash(u.typology)} · pavimento ${orDash(u.floor)}`;
    document.getElementById('drawer-kv').innerHTML = `
      <div class="kv-item"><div class="k">Área privativa</div><div class="v">${fmtNum(u.private_area_m2)} m²</div></div>
      <div class="kv-item"><div class="k">Área descoberta</div><div class="v">${fmtNum(u.uncovered_area_m2)} m²</div></div>
      <div class="kv-item"><div class="k">Área ponderada</div><div class="v">${fmtOrDash(u.weighted_area_m2)} m²</div></div>
      <div class="kv-item"><div class="k">Posição</div><div class="v">${orDash(u.position)}</div></div>
      <div class="kv-item"><div class="k">Peso de pavimento</div><div class="v">${fmtOrDash(u.floor_factor, 3)}</div></div>
      <div class="kv-item"><div class="k">Peso de posição</div><div class="v">${fmtOrDash(u.position_factor, 3)}</div></div>
    `;
    const hasAdj = Number(u.adjustment) !== 0;
    document.getElementById('drawer-price').innerHTML = `
      <div class="row"><span>Preço sistemático</span><span>${fmtMoney(u.system_price)}</span></div>
      ${hasAdj ? `<div class="row"><span class="op">+</span><span>Ajuste humano/comercial</span><span class="text-gold">${fmtMoney(u.adjustment)}</span></div>` : ''}
      <div class="row total"><span>Preço final</span><span>${fmtMoney(u.final_price)}</span></div>
      <div class="row"><span>Preço/m²</span><span>${fmtMoney(u.price_per_m2)}</span></div>
      <div class="row"><span>Participação relativa</span><span>${u.participation_share == null ? '—' : (Number(u.participation_share) * 100).toFixed(4) + '%'}</span></div>
    `;
    document.getElementById('drawer-status').innerHTML = statusBadge(u.status);
    overlay.classList.add('open');
  }
  window.closeUnitDrawer = function () { document.getElementById('unit-drawer-overlay').classList.remove('open'); };

  /* ── VALIDAÇÃO ────────────────────────────────────── */
  function renderValidation() {
    const v = state.dataset.validation;
    document.getElementById('validation-cards').innerHTML = `
      <div class="stat-box"><div class="label">Unidades avaliadas</div><div class="value">${fmtInt(v.units_analyzed)}</div></div>
      <div class="stat-box"><div class="label">Dentro de R$ 0,01</div><div class="value text-good">${fmtInt(v.within_1_cent)}</div><div class="hint">de ${fmtInt(v.units_analyzed)} unidades</div></div>
      <div class="stat-box"><div class="label">Precisão</div><div class="value text-good">${((v.within_1_cent / v.units_analyzed) * 100).toFixed(1)}%</div></div>
      <div class="stat-box"><div class="label">Diferença agregada</div><div class="value">${fmtMoney(v.aggregate_delta)}</div></div>
    `;
    document.getElementById('validation-note').textContent = v.note || '';
  }

  /* ── AUDITORIA ────────────────────────────────────── */
  function renderAuditoria() {
    const d = state.dataset;
    document.getElementById('audit-summary').innerHTML = `
      <div class="kv-grid">
        <div class="kv-item"><div class="k">Fonte</div><div class="v">${d.meta.mode === 'DEMO' ? 'Cenário sintético de demonstração' : 'Base privada local'}</div></div>
        <div class="kv-item"><div class="k">Empreendimento</div><div class="v">${d.development.name}</div></div>
        <div class="kv-item"><div class="k">Cenário</div><div class="v">Referência importada</div></div>
        <div class="kv-item"><div class="k">Parâmetros</div><div class="v">${d.towers.length + d.typologies.length} calibrações ativas</div></div>
        <div class="kv-item"><div class="k">Preço sistemático</div><div class="v">Calculado por unidade</div></div>
        <div class="kv-item"><div class="k">Ajuste humano</div><div class="v">${fmtInt(d.kpis.adjustments_count)} unidade(s)</div></div>
        <div class="kv-item"><div class="k">Preço final</div><div class="v">${fmtMoney(d.kpis.vgv)} (VGV)</div></div>
        <div class="kv-item"><div class="k">Rastreabilidade</div><div class="v">100% das unidades vinculadas à origem</div></div>
      </div>
    `;
  }

  /* ── INIT ─────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', async () => {
    bindTableControls();
    document.querySelectorAll('.sort-th').forEach((th) => th.addEventListener('click', () => window.sortUnitsBy(th.dataset.key)));
    document.getElementById('private-mode-item').style.display = window.dataProvider.privateModeAvailable() ? '' : 'none';
    try {
      await loadAndRender();
    } catch (err) {
      console.error(err);
      document.getElementById('kpi-cards').innerHTML = `<div class="empty-state"><p>Não foi possível carregar os dados.</p><div class="hint">${err.message}</div></div>`;
    }
  });
})();
