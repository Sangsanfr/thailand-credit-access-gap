// Minimal stand-in for the dashboard runtime the page was first written for.
// It gives common.js / q1.js / q2.js the same `dash` object they expect:
//   dash.data(id)          -> {status, data, columns, meta, refreshing}
//   dash.calc(id, spec)    -> a value worked out from other datasets or calcs
//   dash.onData(fn)        -> run fn now, and again on resize, theme or font changes
//   dash.colors            -> eight series colours (CSS variables, light and dark)
//   dash.setLink(name)     -> keep the open tab in the URL (#q1 / #q2)
// Rows come from data/data.js (window.CG_DATA), so the page also works when the
// file is opened straight from disk, with no web server.
(function () {
  'use strict';
  var DATA = window.CG_DATA || {};
  var calcs = {};
  var cache = {};
  var subs = [];

  function rowsOf(id) {
    if (Object.prototype.hasOwnProperty.call(DATA, id)) return DATA[id];
    if (Object.prototype.hasOwnProperty.call(calcs, id)) {
      if (!Object.prototype.hasOwnProperty.call(cache, id)) {
        var spec = calcs[id];
        cache[id] = spec.fn.apply(null, (spec.inputs || []).map(rowsOf));
      }
      return cache[id];
    }
    return undefined;
  }

  function result(status, rows, message) {
    var cols = Array.isArray(rows) && rows.length && typeof rows[0] === 'object' ? Object.keys(rows[0]) : [];
    return { status: status, data: rows, rows: rows, value: rows, columns: cols, meta: [], refreshing: false, message: message || '' };
  }

  function runAll() {
    for (var i = 0; i < subs.length; i++) {
      try { subs[i](); } catch (e) { console.error(e); }
    }
  }

  var colors = [];
  for (var i = 1; i <= 8; i++) colors.push('var(--series-' + i + ')');

  window.dash = {
    data: function (id) {
      try {
        var rows = rowsOf(id);
        if (rows === undefined) return result('missing', [], 'No dataset named ' + id);
        return result('ok', rows);
      } catch (e) {
        console.error('dash.data(' + id + ') failed', e);
        return result('error', [], String(e));
      }
    },
    calc: function (id, spec) { calcs[id] = spec; delete cache[id]; },
    loader: function () {},
    onData: function (fn) {
      subs.push(fn);
      try { fn(); } catch (e) { console.error(e); }
    },
    colors: colors,
    setLink: function (name) {
      try { history.replaceState(null, '', '#' + name); } catch (e) { /* file:// in some browsers */ }
    },
    params: function () { return {}; },
    setParams: function () {},
    resetParams: function () {},
    refresh: function () {},
  };

  // redraw when the width changes, the colour scheme flips, or the web fonts arrive
  var lastWidth = window.innerWidth, timer = null;
  window.addEventListener('resize', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      if (window.innerWidth !== lastWidth) { lastWidth = window.innerWidth; runAll(); }
    }, 150);
  });
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    if (mq.addEventListener) mq.addEventListener('change', runAll);
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(runAll);
})();
