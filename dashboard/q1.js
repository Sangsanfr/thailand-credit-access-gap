// Q1: how unequal is commercial-bank credit across provinces, and is the gap closing?
(() => {
  const C = window.CG, F = C.fmt;
  const page = document.getElementById('q1');
  const st = { scope: 'ex_bkk', basis: 'dec', regionMetric: 'ldr_dec', year: 2568, focus: 'ภาคตะวันออกเฉียงเหนือ', period: '2548-2557',
    sort: { col: 'loan_pc_dec', dir: -1 }, q: '' };

  const getScope = C.seg(page.querySelector('#q1-scope'), (v) => { st.scope = v; draw(); });
  const getBasis = C.seg(page.querySelector('#q1-basis'), (v) => { st.basis = v; draw(); });
  C.seg(page.querySelector('#q1-regmetric'), (v) => { st.regionMetric = v; draw(); });
  C.seg(page.querySelector('#q1-period'), (v) => { st.period = v; draw(); });
  const yearIn = page.querySelector('#q1-year'), yearOut = page.querySelector('#q1-year-out');
  yearIn.addEventListener('input', () => { st.year = Number(yearIn.value); draw(); });
  const focusSel = page.querySelector('#q1-focus');
  focusSel.addEventListener('change', () => { st.focus = focusSel.value; draw(); });
  const search = page.querySelector('#q1-search');
  search.addEventListener('input', () => { st.q = search.value.trim(); drawTable(); });
  const sortBy = (e) => {
    if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
    const th = e.target.closest('th[data-field]'); if (!th) return;
    e.preventDefault();
    const col = th.dataset.field;
    st.sort = { col, dir: st.sort.col === col ? -st.sort.dir : (col === 'prov_name_th' || col === 'region_bot' ? 1 : -1) };
    drawTable();
  };
  page.querySelector('#q1-table thead').addEventListener('click', sortBy);
  page.querySelector('#q1-table thead').addEventListener('keydown', sortBy);
  void getScope; void getBasis;

  function gini() {
    const el = page.querySelector('#q1-gini');
    if (!C.prep(el.querySelector('.cg-draw'), ['ineq_year'])) return;
    const rows = C.rows('ineq_year').filter((r) => r.scope === st.scope && r.basis === st.basis).sort((a, b) => a.year_be - b.year_be);
    const c = dash.colors;
    C.lineChart(el, {
      fmt: F.d3, breaks: true, height: 290,
      series: [
        { name: 'เงินฝากต่อหัว', color: c[1], points: rows.map((r) => ({ x: r.year_be, y: r.gini_dep_pc })) },
        { name: 'สินเชื่อต่อหัว', color: c[0], points: rows.map((r) => ({ x: r.year_be, y: r.gini_loan_pc })) },
      ],
    });
  }

  function regions() {
    const el = page.querySelector('#q1-region');
    if (!C.prep(el.querySelector('.cg-draw'), ['region_flows'])) return;
    const rows = C.rows('region_flows');
    const order = ['ภาคตะวันออกเฉียงเหนือ', 'ภาคใต้', 'ภาคเหนือ', 'ภาคกลาง', 'กรุงเทพมหานคร'];
    const k = st.regionMetric, c = dash.colors;
    const fmt = k === 'ldr_dec' ? F.pct0 : (v) => d3.format(',.0f')(v / 1000) + 'k';
    C.lineChart(el, {
      fmt, breaks: true, height: 290, ref: k === 'ldr_dec' ? { y: 100, label: '100% = สินเชื่อเท่ากับเงินฝาก' } : null,
      yDomain: k === 'ldr_dec' ? null : [0, d3.max(rows, (r) => r[k])],
      series: order.map((reg, i) => ({ name: C.REGIONS[reg], color: c[i],
        points: rows.filter((r) => r.region_bot === reg).sort((a, b) => a.year_be - b.year_be).map((r) => ({ x: r.year_be, y: r[k] })) })),
    });
  }

  function scatter() {
    const el = page.querySelector('#q1-scatter'), box = el.querySelector('.cg-draw');
    yearOut.textContent = st.year;
    if (!C.prep(box, ['prov_year'])) return;
    const rows = C.rows('prov_year').filter((r) => r.year_be === st.year && r.prov_code_h !== '10' && r.loan_pc_dec > 0);
    const W = Math.max(280, box.clientWidth), H = 340;
    box.replaceChildren();
    const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
    const xs0 = d3.scaleLog().domain([8000, 500000]);
    const ys0 = d3.scaleLinear().domain([0, Math.max(160, d3.max(rows, (r) => r.ldr_dec) + 5)]).nice();
    const yt = ys0.ticks(5), tw = C.textWidth(svg, yt.map((v) => v + '%'), 'cg-tick');
    const m = { t: 12, r: 14, b: 40, l: tw + 12 };
    const xs = xs0.range([m.l, W - m.r]), ys = ys0.range([H - m.b, m.t]);
    const xt = [10000, 20000, 50000, 100000, 200000, 500000].filter((v) => xs(v) <= W - m.r);
    svg.selectAll('.g1').data(yt).join('line').attr('class', 'cg-grid').attr('x1', m.l).attr('x2', W - m.r).attr('y1', ys).attr('y2', ys);
    svg.selectAll('.g2').data(xt).join('line').attr('class', 'cg-grid').attr('y1', m.t).attr('y2', H - m.b).attr('x1', xs).attr('x2', xs);
    svg.selectAll('.t1').data(yt).join('text').attr('class', 'cg-tick').attr('x', m.l - 8).attr('y', ys).attr('dy', '0.32em')
      .attr('text-anchor', 'end').text((v) => v + '%');
    svg.selectAll('.t2').data(xt).join('text').attr('class', 'cg-tick').attr('x', xs).attr('y', H - m.b + 16)
      .attr('text-anchor', 'middle').text((v) => d3.format(',')(v));
    svg.append('text').attr('class', 'cg-tick').attr('x', W - m.r).attr('y', H - 4).attr('text-anchor', 'end')
      .text('สินเชื่อต่อหัว (บาท, สเกล log) →');
    svg.append('line').attr('class', 'cg-ref').attr('x1', m.l).attr('x2', W - m.r).attr('y1', ys(100)).attr('y2', ys(100));
    svg.append('text').attr('class', 'cg-tick').attr('x', W - m.r - 4).attr('y', ys(100) - 5).attr('text-anchor', 'end').text('LDR 100%');
    const isF = (r) => r.region_bot === st.focus;
    const sorted = rows.slice().sort((a, b) => isF(a) - isF(b));
    const tip = C.tip(el);
    svg.append('g').selectAll('circle').data(sorted).join('circle')
      .attr('cx', (r) => xs(Math.min(500000, Math.max(8000, r.loan_pc_dec)))).attr('cy', (r) => ys(r.ldr_dec))
      .attr('r', (r) => (isF(r) ? 5.5 : 4.5)).attr('class', 'cg-pt')
      .style('fill', (r) => (isF(r) ? dash.colors[0] : 'var(--cds-chart-muted)'))
      .on('pointermove', (event, r) => tip.show(event, r.prov_name_th, [
        { label: 'ภาค', value: C.REGIONS[r.region_bot] },
        { label: 'สินเชื่อต่อหัว', value: F.baht(r.loan_pc_dec) + ' บาท' },
        { label: 'เงินฝากต่อหัว', value: F.baht(r.dep_pc_dec) + ' บาท' },
        { label: 'LDR', value: F.d1(r.ldr_dec) + '%' }]))
      .on('pointerleave', () => tip.hide());
    // label the extremes of the year
    const ext = [d3.least(rows, (r) => r.loan_pc_dec), d3.greatest(rows, (r) => r.loan_pc_dec), d3.greatest(rows, (r) => r.ldr_dec)];
    for (const r of new Set(ext)) {
      const x = xs(r.loan_pc_dec), left = x > W * 0.7;
      svg.append('text').attr('class', 'cg-ptlab').attr('x', x + (left ? -8 : 8)).attr('y', ys(r.ldr_dec) - 7)
        .attr('text-anchor', left ? 'end' : 'start').text(r.prov_name_th);
    }
    const focusRows = rows.filter(isF);
    page.querySelector('#q1-scatter-note').textContent = focusRows.length
      ? `${C.REGIONS[st.focus]}: ${focusRows.length} พื้นที่ · LDR มัธยฐาน ${F.d1(d3.median(focusRows, (r) => r.ldr_dec))}% · สินเชื่อต่อหัวมัธยฐาน ${F.baht(d3.median(focusRows, (r) => r.loan_pc_dec))} บาท`
      : '';
  }

  function convergence() {
    const el = page.querySelector('#q1-conv'), box = el.querySelector('.cg-draw');
    if (!C.prep(box, ['conv_points', 'conv_fit'])) return;
    const pts = C.rows('conv_points').filter((r) => r.period === st.period);
    const fit = C.rows('conv_fit').find((r) => r.period === st.period);
    const W = Math.max(280, box.clientWidth), H = 300;
    box.replaceChildren();
    const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
    const xs0 = d3.scaleLog().domain(d3.extent(pts, (r) => r.loan_pc_start)).nice();
    const ys0 = d3.scaleLinear().domain(d3.extent(pts, (r) => r.growth_pct_pa)).nice();
    const yt = ys0.ticks(5), tw = C.textWidth(svg, yt.map((v) => v + '%'), 'cg-tick');
    const m = { t: 12, r: 14, b: 40, l: tw + 12 };
    const xs = xs0.range([m.l, W - m.r]), ys = ys0.range([H - m.b, m.t]);
    const xt = [5000, 10000, 20000, 50000, 100000, 200000, 500000].filter((v) => v >= xs0.domain()[0] && v <= xs0.domain()[1]);
    svg.selectAll('.g1').data(yt).join('line').attr('class', 'cg-grid').attr('x1', m.l).attr('x2', W - m.r).attr('y1', ys).attr('y2', ys);
    svg.selectAll('.t1').data(yt).join('text').attr('class', 'cg-tick').attr('x', m.l - 8).attr('y', ys).attr('dy', '0.32em')
      .attr('text-anchor', 'end').text((v) => v + '%');
    svg.selectAll('.t2').data(xt).join('text').attr('class', 'cg-tick').attr('x', xs).attr('y', H - m.b + 16)
      .attr('text-anchor', 'middle').text((v) => d3.format(',')(v));
    svg.append('text').attr('class', 'cg-tick').attr('x', W - m.r).attr('y', H - 4).attr('text-anchor', 'end')
      .text('สินเชื่อต่อหัวปีเริ่มต้น (บาท, log) →');
    if (ys0.domain()[0] < 0) svg.append('line').attr('class', 'cg-axis').attr('x1', m.l).attr('x2', W - m.r).attr('y1', ys(0)).attr('y2', ys(0));
    const [x0, x1] = xs0.domain();
    svg.append('line').attr('class', 'cg-fit').attr('x1', xs(x0)).attr('x2', xs(x1))
      .attr('y1', ys(fit.intercept + fit.slope * Math.log(x0))).attr('y2', ys(fit.intercept + fit.slope * Math.log(x1)));
    const tip = C.tip(el);
    svg.append('g').selectAll('circle').data(pts).join('circle').attr('class', 'cg-pt')
      .attr('cx', (r) => xs(r.loan_pc_start)).attr('cy', (r) => ys(r.growth_pct_pa)).attr('r', 4.5)
      .style('fill', (r) => (r.region_bot === 'ภาคตะวันออกเฉียงเหนือ' ? dash.colors[0] : 'var(--cds-chart-muted)'))
      .on('pointermove', (event, r) => tip.show(event, r.prov_name_th, [
        { label: 'สินเชื่อต่อหัวปีเริ่มต้น', value: F.baht(r.loan_pc_start) + ' บาท' },
        { label: 'เติบโตเฉลี่ย', value: F.d1(r.growth_pct_pa) + '% ต่อปี' }]))
      .on('pointerleave', () => tip.hide());
  }

  function drawTable() {
    const table = page.querySelector('#q1-table'), body = table.querySelector('tbody');
    page.querySelector('#q1-table-year').textContent = st.year;
    if (C.state(['prov_year']) !== 'ok') { body.replaceChildren(); table.classList.toggle('dash-skeleton', C.state(['prov_year']) === 'loading'); return; }
    table.classList.remove('dash-skeleton');
    const { col, dir } = st.sort;
    let rows = C.rows('prov_year').filter((r) => r.year_be === st.year);
    if (st.q) rows = rows.filter((r) => (r.prov_name_th + ' ' + r.region_bot).includes(st.q));
    rows.sort((a, b) => (typeof a[col] === 'string' ? a[col].localeCompare(b[col], 'th') : a[col] - b[col]) * dir);
    const max = d3.max(C.rows('prov_year').filter((r) => r.year_be === st.year && r.prov_code_h !== '10'), (r) => r.loan_pc_dec);
    body.replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr'); tr.dataset.key = r.key;
      const td = (text, cls) => { const c = document.createElement('td'); c.textContent = text; if (cls) c.className = cls; tr.append(c); return c; };
      td(r.prov_name_th); td(r.region_bot, 'cg-hide-narrow');
      const lp = td('', 'cg-num cg-barcell');
      const bar = document.createElement('span'); bar.className = 'cg-bar'; bar.style.width = Math.min(100, r.loan_pc_dec / max * 100) + '%';
      const lv = document.createElement('span'); lv.textContent = F.baht(r.loan_pc_dec); lp.append(bar, lv);
      td(F.baht(r.dep_pc_dec), 'cg-num cg-hide-narrow'); td(F.d1(r.ldr_dec), 'cg-num'); td(F.d1(r.offices_per_100k), 'cg-num cg-hide-narrow');
      return tr;
    }));
    for (const th of table.querySelectorAll('th[data-field]')) th.setAttribute('aria-sort', th.dataset.field === col ? (dir > 0 ? 'ascending' : 'descending') : 'none');
  }

  function draw() {
    C.fillMarks(page);
    if (C.current !== 'q1') return;
    gini(); regions(); scatter(); convergence(); drawTable();
  }
  dash.onData(draw);
  window.addEventListener('cg-tab', draw);
})();
