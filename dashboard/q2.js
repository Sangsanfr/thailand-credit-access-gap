// Q2: is low credit access spatially clustered?
(() => {
  const C = window.CG, F = C.fmt;
  const page = document.getElementById('q2');
  const VAR = {
    loan: { lisa: 'log_loan_pc', col: 'loan_pc_dec', name: 'สินเชื่อต่อหัว', breaks: [25000, 35000, 50000, 80000], unit: 'บาทต่อคน' },
    dep: { lisa: 'log_dep_pc', col: 'dep_pc_dec', name: 'เงินฝากต่อหัว', breaks: [40000, 60000, 80000, 120000], unit: 'บาทต่อคน' },
    ldr: { lisa: 'ldr_dec', col: 'ldr_dec', name: 'LDR', breaks: [50, 75, 100, 125], unit: 'สินเชื่อ ÷ เงินฝาก (%)' },
  };
  const st = { scope: 'all', weights: 'queen', metric: 'loan', view: 'lisa', year: 2568, dvar: 'loan', zoom: 'all' };
  C.seg(page.querySelector('#q2-scope'), (v) => { st.scope = v; draw(); });
  C.seg(page.querySelector('#q2-weights'), (v) => { st.weights = v; draw(); });
  C.seg(page.querySelector('#q2-metric'), (v) => { st.metric = v; draw(); });
  C.seg(page.querySelector('#q2-view'), (v) => { st.view = v; draw(); });
  C.seg(page.querySelector('#q2-dvar'), (v) => { st.dvar = v; draw(); });
  C.seg(page.querySelector('#q2-zoom'), (v) => { st.zoom = v; draw(); });
  const yearIn = page.querySelector('#q2-year'), yearOut = page.querySelector('#q2-year-out');
  yearIn.addEventListener('input', () => { st.year = Number(yearIn.value); draw(); });

  const fmtVal = (k, v) => (v == null ? '—' : k === 'ldr' ? F.d1(v) + '%' : F.baht(v) + ' บาท');

  function ramp(k) {
    const panel = C.probe('var(--color-panel)'), blue = C.probe(dash.colors[0]), red = C.LISA.LL.color;
    if (k === 'ldr') {
      const r = d3.interpolateRgb(panel, red), b = d3.interpolateRgb(panel, blue);
      return [r(0.95), r(0.62), r(0.32), b(0.45), b(0.92)];
    }
    const b = d3.interpolateRgb(panel, blue);
    return [0.16, 0.36, 0.56, 0.76, 0.96].map(b);
  }
  const classLabels = (k) => {
    const br = VAR[k].breaks, f = k === 'ldr' ? (v) => v + '%' : (v) => d3.format(',')(v);
    return [`ต่ำกว่า ${f(br[0])}`, ...br.slice(1).map((b, i) => `${f(br[i])}–${f(b)}`), `${f(br.at(-1))} ขึ้นไป`];
  };

  function moran() {
    const el = page.querySelector('#q2-moran');
    if (!C.prep(el.querySelector('.cg-draw'), ['moran_year'])) return;
    const rows = C.rows('moran_year').filter((r) => r.scope === st.scope && r.weights === st.weights);
    const c = dash.colors;
    const ser = (v, name, color) => ({ name, color, points: rows.filter((r) => r.variable === v).sort((a, b) => a.year_be - b.year_be).map((r) => ({ x: r.year_be, y: r.moran_I })) });
    C.lineChart(el, { fmt: F.d2, breaks: true, height: 280, yDomain: [0, 0.75],
      series: [ser('log_dep_pc', 'เงินฝากต่อหัว', c[1]), ser('ldr_dec', 'LDR', c[2]), ser('log_loan_pc', 'สินเชื่อต่อหัว', c[0])] });
  }

  function legend(el, items) {
    el.replaceChildren(...items.map(([color, text]) => {
      const it = document.createElement('div'); it.className = 'cg-leg';
      const sw = document.createElement('span'); sw.className = 'cg-sw cg-sw-lg'; sw.style.background = color;
      const t = document.createElement('span'); t.textContent = text; it.append(sw, t); return it;
    }));
  }

  function provMap() {
    const card = page.querySelector('#q2-map'), box = card.querySelector('.cg-mapbox');
    yearOut.textContent = st.year;
    if (!C.prep(box, ['geo_prov', 'prov_year', 'lisa_prov'])) return;
    const k = st.metric, v = VAR[k];
    const vals = new Map(C.rows('prov_year').filter((r) => r.year_be === st.year).map((r) => [r.prov_code_h, r]));
    const lis = new Map(C.rows('lisa_prov').filter((r) => r.year_be === st.year && r.variable === v.lisa).map((r) => [r.prov_code_h, r]));
    const cols = ramp(k), cls = (x) => cols[d3.bisectRight(v.breaks, x)];
    const fill = (g) => {
      if (st.view === 'lisa') return C.LISA[lis.get(g)?.cluster || 'ns'].color;
      const r = vals.get(g); return r ? cls(r[v.col]) : 'transparent';
    };
    box.replaceChildren();
    const svg = d3.select(box).append('svg').attr('viewBox', '0 0 410 750').attr('width', '100%').attr('role', 'img');
    const tip = C.tip(card);
    svg.selectAll('path').data(C.rows('geo_prov')).join('path').attr('d', (r) => r.d).attr('class', 'cg-area')
      .style('fill', (r) => fill(r.prov_code_h))
      .on('pointermove', (event, r) => {
        const x = vals.get(r.prov_code_h), l = lis.get(r.prov_code_h);
        tip.show(event, r.prov_name_th, [
          { label: v.name, value: fmtVal(k, x?.[v.col]) },
          { label: 'กลุ่ม LISA', value: l ? C.LISA[l.cluster].label : '—' },
          { label: 'p (permutation)', value: l ? d3.format('.4f')(l.p_sim) : '—' }]);
      })
      .on('pointerleave', () => tip.hide());
    const lg = card.querySelector('.cg-maplegend');
    if (st.view === 'lisa') {
      const n = d3.rollup([...lis.values()], (a) => a.length, (r) => r.cluster);
      legend(lg, Object.entries(C.LISA).map(([c, o]) => [o.color, `${o.label} (${n.get(c) || 0})`]));
    } else {
      const n = d3.rollup([...vals.values()], (a) => a.length, (r) => d3.bisectRight(v.breaks, r[v.col]));
      legend(lg, classLabels(k).map((t, i) => [cols[i], `${t} (${n.get(i) || 0})`]));
    }
    card.querySelector('.cg-legtitle').textContent = st.view === 'lisa' ? `กลุ่ม LISA ของ${v.name} · ${st.year}` : `${v.name} · ${v.unit} · ${st.year}`;
    // who is in each cluster
    const list = card.querySelector('#q2-members');
    list.replaceChildren(...['HH', 'LL', 'HL', 'LH'].map((c) => {
      const names = [...lis.values()].filter((r) => r.cluster === c).map((r) => vals.get(r.prov_code_h)?.prov_name_th).filter(Boolean);
      const dt = document.createElement('div'); dt.className = 'cg-member';
      const h = document.createElement('div'); h.className = 'cg-member-h';
      const sw = document.createElement('span'); sw.className = 'cg-sw'; sw.style.background = C.LISA[c].color;
      h.append(sw, document.createTextNode(`${C.LISA[c].label} · ${names.length}`));
      const p = document.createElement('div'); p.className = 'cg-member-b'; p.textContent = names.length ? names.join(', ') : '—';
      dt.append(h, p); return dt;
    }));
  }

  const VIEW = { all: '0 0 410 750', bkk: '124 304 68 54' };
  function distMap() {
    const card = page.querySelector('#q2-dist'), box = card.querySelector('.cg-mapbox');
    if (!C.prep(box, ['geo_dist', 'geo_prov', 'lisa_dist'])) return;
    const v = VAR[st.dvar];
    const lis = new Map(C.rows('lisa_dist').filter((r) => r.variable === v.lisa).map((r) => [r.area_id, r]));
    box.replaceChildren();
    const svg = d3.select(box).append('svg').attr('viewBox', VIEW[st.zoom]).attr('width', '100%').attr('role', 'img');
    const tip = C.tip(card);
    svg.append('g').selectAll('path').data(C.rows('geo_dist')).join('path').attr('d', (r) => r.d).attr('class', 'cg-area cg-thin')
      .style('fill', (r) => (lis.has(r.unit_id) ? C.LISA[lis.get(r.unit_id).cluster].color : 'transparent'))
      .on('pointermove', (event, r) => {
        const l = lis.get(r.unit_id);
        if (!l) { tip.show(event, 'ไม่มีสินเชื่อ', [{ label: 'หน่วย', value: r.unit_id }]); return; }
        tip.show(event, `${l.amphoe_name || r.unit_id} · ${l.prov_name_th}`, [
          { label: v.name, value: fmtVal(st.dvar, l.real_value) },
          { label: 'ประชากร', value: F.int(l.population) },
          { label: 'กลุ่ม LISA', value: C.LISA[l.cluster].label },
          { label: 'p (permutation)', value: d3.format('.3f')(l.p_sim) }]);
      })
      .on('pointerleave', () => tip.hide());
    svg.append('g').selectAll('path').data(C.rows('geo_prov')).join('path').attr('d', (r) => r.d).attr('class', 'cg-outline');
    if (st.zoom === 'all') svg.append('rect').attr('class', 'cg-zoombox').attr('x', 124).attr('y', 304).attr('width', 68).attr('height', 54);
    const sum = C.rows('dist_summary').filter((r) => r.variable === v.lisa);
    legend(card.querySelector('.cg-maplegend'), Object.entries(C.LISA).map(([c, o]) => {
      const s = sum.find((r) => r.cluster === c);
      return [o.color, s ? `${o.label} · ${s.units} หน่วย · ประชากร ${F.share(s.pop_share)}` : o.label];
    }));
    card.querySelector('.cg-legtitle').textContent = `กลุ่ม LISA ของ${v.name} ระดับอำเภอ · 2568`;
    hubs(lis, v);
  }

  function hubs(lis, v) {
    const table = page.querySelector('#q2-hubs'), body = table.querySelector('tbody');
    const rows = [...lis.values()].filter((r) => r.cluster === 'HL').sort((a, b) => b.real_value - a.real_value);
    page.querySelector('#q2-hubs-note').textContent = `${rows.length} หน่วยที่${v.name}สูงแต่รอบข้างต่ำ · ${rows.filter((r) => r.amphoe_name.startsWith('เมือง')).length} หน่วยเป็นอำเภอเมือง`;
    table.querySelector('th[data-field="real_value"]').textContent = v.name;
    body.replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr'); tr.dataset.key = r.key;
      for (const [t, c] of [[r.amphoe_name, ''], [r.prov_name_th, ''], [fmtVal(st.dvar, r.real_value), 'cg-num']]) {
        const td = document.createElement('td'); td.textContent = t; if (c) td.className = c; tr.append(td);
      }
      return tr;
    }));
  }

  function draw() {
    C.fillMarks(page);
    if (C.current !== 'q2') return;
    moran(); provMap(); distMap();
  }
  dash.onData(draw);
  window.addEventListener('cg-tab', draw);
})();
