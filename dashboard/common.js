// Shared helpers, calculations and tab switching for the credit-gap dashboard.
dash.calc('surplus', {
  inputs: ['region_flows'],
  title: 'เงินฝากที่เกินสินเชื่อ นอกกรุงเทพฯ',
  description: 'ผลรวมของ (เงินฝาก − สินเชื่อ) ทุกภาคยกเว้นกรุงเทพฯ ยอด ธ.ค. หน่วยล้านล้านบาท',
  fn: (region_flows) => {
    const m = new Map();
    for (const r of region_flows) if (r.region_bot !== 'กรุงเทพมหานคร') m.set(r.year_be, (m.get(r.year_be) || 0) + r.net_outflow_dec);
    return [...m].map(([year_be, v]) => ({ year_be, surplus_trillion: v / 1e6 }));
  },
});

dash.calc('conv_points', {
  inputs: ['prov_year'],
  title: 'การเติบโตของสินเชื่อต่อหัว',
  description: 'สินเชื่อต่อหัวปีเริ่มต้น และอัตราเติบโตเฉลี่ยต่อปี (log, %) ของแต่ละช่วง ไม่รวมกรุงเทพฯ',
  fn: (prov_year) => {
    const out = [];
    for (const [a, b] of [[2548, 2557], [2559, 2568], [2548, 2568]]) {
      const end = new Map(prov_year.filter((r) => r.year_be === b).map((r) => [r.prov_code_h, r]));
      for (const r of prov_year) {
        const s = end.get(r.prov_code_h);
        if (r.year_be !== a || r.prov_code_h === '10' || !s) continue;
        out.push({ period: `${a}-${b}`, prov_code_h: r.prov_code_h, prov_name_th: r.prov_name_th, region_bot: r.region_bot,
          loan_pc_start: r.loan_pc_dec, growth_pct_pa: (Math.log(s.loan_pc_dec) - Math.log(r.loan_pc_dec)) / (b - a) * 100 });
      }
    }
    return out;
  },
});

dash.calc('conv_fit', {
  inputs: ['conv_points'],
  title: 'เส้นถดถอย β-convergence',
  description: 'OLS ของอัตราเติบโต (%/ปี) บน log สินเชื่อต่อหัวปีเริ่มต้น แยกตามช่วงเวลา',
  fn: (conv_points) => {
    const periods = [...new Set(conv_points.map((r) => r.period))];
    return periods.map((period) => {
      const rows = conv_points.filter((r) => r.period === period);
      const x = rows.map((r) => Math.log(r.loan_pc_start)), y = rows.map((r) => r.growth_pct_pa);
      const mx = x.reduce((s, v) => s + v, 0) / x.length, my = y.reduce((s, v) => s + v, 0) / y.length;
      let sxy = 0, sxx = 0;
      x.forEach((v, i) => { sxy += (v - mx) * (y[i] - my); sxx += (v - mx) ** 2; });
      return { period, slope: sxy / sxx, intercept: my - (sxy / sxx) * mx, n: rows.length };
    });
  },
});

dash.calc('lisa_counts', {
  inputs: ['lisa_prov'],
  title: 'จำนวนจังหวัดในแต่ละกลุ่ม LISA',
  description: 'นับจังหวัดตามปี ตัวแปร และกลุ่ม (p < 0.05) รวมกรุงเทพฯ',
  fn: (lisa_prov) => {
    const m = new Map();
    for (const r of lisa_prov) {
      const k = `${r.year_be}|${r.variable}|${r.cluster}`;
      m.set(k, (m.get(k) || 0) + 1);
    }
    return [...m].map(([k, n]) => {
      const [y, variable, cluster] = k.split('|');
      return { year_be: Number(y), variable, cluster, n };
    });
  },
});

dash.calc('dist_summary', {
  inputs: ['lisa_dist'],
  title: 'สรุปกลุ่ม LISA ระดับอำเภอ 2568',
  description: 'จำนวนหน่วย สัดส่วนประชากร และจำนวนอำเภอเมือง ในแต่ละกลุ่ม แยกตามตัวแปร',
  fn: (lisa_dist) => {
    const out = [];
    for (const variable of [...new Set(lisa_dist.map((r) => r.variable))]) {
      const rows = lisa_dist.filter((r) => r.variable === variable);
      const pop = rows.reduce((s, r) => s + r.population, 0);
      for (const cluster of ['HH', 'LL', 'HL', 'LH', 'ns']) {
        const g = rows.filter((r) => r.cluster === cluster);
        out.push({ variable, cluster, units: g.length, pop_share: g.reduce((s, r) => s + r.population, 0) / pop,
          muang: g.filter((r) => r.amphoe_name.startsWith('เมือง')).length });
      }
    }
    return out;
  },
});

(() => {
  const C = (window.CG = {});
  const root = document.getElementById('dash-root');

  C.fmt = {
    d3: d3.format('.3f'), d2: d3.format('.2f'), d1: d3.format('.1f'), int: d3.format(','),
    baht: d3.format(',.0f'), pct0: (v) => d3.format('.0f')(v) + '%', share: d3.format('.0%'),
    tn: (v) => d3.format('.2f')(v) + ' ล้านล้าน', signed2: d3.format('+.2f'),
  };
  C.REGIONS = { 'กรุงเทพมหานคร': 'กรุงเทพฯ', 'ภาคกลาง': 'กลาง', 'ภาคตะวันออกเฉียงเหนือ': 'อีสาน', 'ภาคเหนือ': 'เหนือ', 'ภาคใต้': 'ใต้' };
  C.LISA = {
    HH: { color: '#184f95', label: 'สูง ล้อมรอบด้วยสูง' }, LL: { color: '#c93837', label: 'ต่ำ ล้อมรอบด้วยต่ำ' },
    HL: { color: '#6da7ec', label: 'สูง แต่รอบข้างต่ำ' }, LH: { color: '#ee8885', label: 'ต่ำ แต่รอบข้างสูง' },
    ns: { color: 'color-mix(in srgb, var(--color-fg) 9%, var(--color-panel))', label: 'ไม่มีนัยสำคัญ' },
  };

  C.state = (ids) => {
    let s = 'ok';
    for (const id of ids) {
      const st = dash.data(id).status;
      if (st === 'error' || st === 'connect' || st === 'declined' || st === 'missing') return 'error';
      if (st !== 'ok') s = 'loading';
    }
    return s;
  };
  C.rows = (id) => { const d = dash.data(id); return d.status === 'ok' && Array.isArray(d.data) ? d.data : []; };

  // a box that holds a drawing: skeleton while loading, one failed line on error
  C.prep = (el, ids) => {
    const st = C.state(ids);
    el.classList.toggle('dash-skeleton', st === 'loading');
    if (st !== 'ok') {
      el.replaceChildren();
      if (st === 'error') {
        const f = document.createElement('div'); f.className = 'cg-failed';
        const dot = document.createElement('span'); dot.className = 'cg-dot';
        f.append(dot, document.createTextNode('Failed to load')); el.append(f);
      }
      return false;
    }
    return true;
  };

  C.probe = (css) => {
    const el = document.createElement('span'); el.style.color = css; el.hidden = true; root.append(el);
    const c = getComputedStyle(el).color; el.remove(); return c;
  };

  // fill every single-value mark from its row
  C.fillMarks = (scope) => {
    for (const el of scope.querySelectorAll('[data-where][data-field][data-fmt]')) {
      const d = dash.data(el.dataset.source);
      if (d.status !== 'ok') { el.textContent = '—'; el.classList.toggle('dash-skeleton', d.status === 'loading'); continue; }
      el.classList.remove('dash-skeleton');
      const want = new URLSearchParams(el.dataset.where.replaceAll('&amp;', '&'));
      const row = (d.data || []).find((r) => [...want].every(([k, v]) => String(r[k]) === v));
      const v = row ? row[el.dataset.field] : null;
      el.textContent = v == null ? '—' : C.fmt[el.dataset.fmt](v);
    }
  };

  // tooltip inside a position:relative box
  C.tip = (box) => {
    let t = box.querySelector(':scope > .cg-tip');
    if (!t) { t = document.createElement('div'); t.className = 'cg-tip'; t.hidden = true; box.append(t); }
    return {
      show(event, head, lines) {
        t.replaceChildren();
        const h = document.createElement('div'); h.className = 'cg-tip-head'; h.textContent = head; t.append(h);
        for (const l of lines) {
          const row = document.createElement('div'); row.className = 'cg-tip-row';
          if (l.color) { const sw = document.createElement('span'); sw.className = 'cg-sw'; sw.style.background = l.color; row.append(sw); }
          const n = document.createElement('span'); n.textContent = l.label; row.append(n);
          const v = document.createElement('b'); v.textContent = l.value; row.append(v);
          t.append(row);
        }
        t.hidden = false;
        const b = box.getBoundingClientRect(), [x, y] = [event.clientX - b.left, event.clientY - b.top];
        const w = t.offsetWidth, hh = t.offsetHeight;
        t.style.left = Math.max(4, Math.min(b.width - w - 4, x + 14 + w > b.width ? x - w - 14 : x + 14)) + 'px';
        t.style.top = Math.max(4, Math.min(b.height - hh - 4, y - hh / 2)) + 'px';
      },
      hide() { t.hidden = true; },
    };
  };

  C.textWidth = (svg, texts, cls) => {
    const t = svg.append('text').attr('class', cls);
    let w = 0;
    for (const s of texts) { t.text(s); w = Math.max(w, t.node().getComputedTextLength()); }
    t.remove(); return w;
  };

  // line chart over BE years; o: {series:[{name,color,points:[{x,y}]}], fmt, yDomain?, ref?, height?, breaks?}
  C.lineChart = (el, o) => {
    const host = el.querySelector(':scope > .cg-draw') || el;
    const W = Math.max(280, host.clientWidth), H = o.height || 300, narrow = W < 560;
    host.replaceChildren();
    const svg = d3.select(host).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img');
    const all = o.series.flatMap((s) => s.points.map((p) => p.y)).filter((v) => v != null);
    let yd = o.yDomain ? o.yDomain.slice() : d3.extent(all);
    if (o.ref != null) yd = [Math.min(yd[0], o.ref.y), Math.max(yd[1], o.ref.y)];
    const pad = (yd[1] - yd[0]) * 0.08 || 1;
    const ys0 = d3.scaleLinear().domain([o.yDomain ? yd[0] : yd[0] - pad, yd[1] + pad]).nice();
    const yticks = ys0.ticks(5);
    const ends = o.series.map((s) => ({ s, p: s.points.filter((p) => p.y != null).at(-1) }));
    const lw = narrow ? 0 : C.textWidth(svg, ends.map((e) => `${e.s.name}  ${o.fmt(e.p.y)}`), 'cg-endlab');
    const tw = C.textWidth(svg, yticks.map(o.tickFmt || o.fmt), 'cg-tick');
    const m = { t: o.breaks ? 26 : 14, r: narrow ? 10 : lw + 18, b: 26, l: tw + 12 };
    const xd = d3.extent(o.series.flatMap((s) => s.points.map((p) => p.x)));
    const xs = d3.scaleLinear(xd, [m.l, W - m.r]);
    const ys = ys0.copy().range([H - m.b, m.t]);
    const g = svg.append('g');
    g.selectAll('.cg-grid').data(yticks).join('line').attr('class', 'cg-grid')
      .attr('x1', m.l).attr('x2', W - m.r).attr('y1', ys).attr('y2', ys);
    g.selectAll('.cg-ytick').data(yticks).join('text').attr('class', 'cg-tick').attr('x', m.l - 8).attr('y', ys)
      .attr('dy', '0.32em').attr('text-anchor', 'end').text(o.tickFmt || o.fmt);
    const step = (W - m.l - m.r) / (xd[1] - xd[0]) < 26 ? 4 : 2;
    const xt = d3.range(xd[0], xd[1] + 1, step);
    g.selectAll('.cg-xtick').data(xt).join('text').attr('class', 'cg-tick').attr('x', xs).attr('y', H - 6)
      .attr('text-anchor', 'middle').text((d) => d);
    g.append('line').attr('class', 'cg-axis').attr('x1', m.l).attr('x2', W - m.r).attr('y1', H - m.b).attr('y2', H - m.b);
    if (o.breaks) {
      for (const [x, anchor, dx] of [[2558, 'end', -4], [2561, 'start', 4]]) {
        g.append('line').attr('class', 'cg-break').attr('x1', xs(x)).attr('x2', xs(x)).attr('y1', m.t - 6).attr('y2', H - m.b);
        g.append('text').attr('class', 'cg-breaklab').attr('x', xs(x) + dx).attr('y', m.t - 12).attr('text-anchor', anchor)
          .text(`รอยต่อข้อมูล ${x}`);
      }
    }
    if (o.ref) {
      g.append('line').attr('class', 'cg-ref').attr('x1', m.l).attr('x2', W - m.r).attr('y1', ys(o.ref.y)).attr('y2', ys(o.ref.y));
      g.append('text').attr('class', 'cg-tick').attr('x', m.l + 4).attr('y', ys(o.ref.y) - 5).text(o.ref.label);
    }
    const line = d3.line().defined((p) => p.y != null).x((p) => xs(p.x)).y((p) => ys(p.y));
    for (const s of o.series) {
      g.append('path').attr('class', 'cg-line').attr('d', line(s.points)).style('stroke', s.color)
        .style('stroke-dasharray', s.dash ? '4 3' : null).style('stroke-width', s.thin ? 1.25 : 2);
    }
    if (!narrow) {
      const placed = ends.map((e) => ({ ...e, y: ys(e.p.y) })).sort((a, b) => a.y - b.y);
      for (let i = 1; i < placed.length; i++) placed[i].y = Math.max(placed[i].y, placed[i - 1].y + 15);
      for (const e of placed) {
        g.append('circle').attr('cx', xs(e.p.x)).attr('cy', ys(e.p.y)).attr('r', 3).style('fill', e.s.color);
        g.append('text').attr('class', 'cg-endlab').attr('x', W - m.r + 8).attr('y', e.y).attr('dy', '0.32em')
          .text(`${e.s.name}  ${o.fmt(e.p.y)}`);
      }
    }
    const legend = el.querySelector(':scope > .cg-legend');
    if (legend) {
      legend.hidden = !narrow;
      legend.replaceChildren(...ends.slice().sort((a, b) => b.p.y - a.p.y).map(({ s }) => {
        const it = document.createElement('span'); it.className = 'cg-leg';
        const sw = document.createElement('span'); sw.className = 'cg-sw'; sw.style.background = s.color;
        it.append(sw, document.createTextNode(s.name)); return it;
      }));
    }
    const tip = C.tip(el);
    const rule = g.append('line').attr('class', 'cg-hover').attr('y1', m.t).attr('y2', H - m.b).style('opacity', 0);
    const dots = g.append('g');
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b)
      .style('fill', 'transparent')
      .on('pointermove', (event) => {
        const x = Math.round(xs.invert(d3.pointer(event)[0]));
        rule.attr('x1', xs(x)).attr('x2', xs(x)).style('opacity', 1);
        const hits = o.series.map((s) => ({ s, p: s.points.find((p) => p.x === x) })).filter((h) => h.p && h.p.y != null).sort((a, b) => b.p.y - a.p.y);
        dots.selectAll('circle').data(hits).join('circle').attr('r', 4).attr('cx', (h) => xs(h.p.x))
          .attr('cy', (h) => ys(h.p.y)).style('fill', (h) => h.s.color);
        tip.show(event, `ปี ${x}`, hits.map((h) => ({ color: h.s.color, label: h.s.name, value: o.fmt(h.p.y) })));
      })
      .on('pointerleave', () => { rule.style('opacity', 0); dots.selectAll('*').remove(); tip.hide(); });
  };

  // segmented control helper
  C.seg = (el, onPick) => {
    el.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-v]'); if (!b) return;
      for (const x of el.querySelectorAll('button')) x.setAttribute('aria-pressed', String(x === b));
      onPick(b.dataset.v);
    });
    return () => el.querySelector('button[aria-pressed="true"]').dataset.v;
  };

  // tabs
  const tabs = [...root.querySelectorAll('.cg-tab')];
  C.current = 'q1';
  C.show = (id) => {
    C.current = id;
    for (const t of tabs) t.setAttribute('aria-selected', String(t.dataset.tab === id));
    for (const s of root.querySelectorAll('.cg-page')) s.hidden = s.id !== id;
    dash.setLink(id);
    window.dispatchEvent(new Event('cg-tab'));
  };
  for (const t of tabs) t.addEventListener('click', () => C.show(t.dataset.tab));
  const named = location.hash.slice(1);
  if (named === 'q2') C.show('q2'); else dash.setLink('q1');
})();
