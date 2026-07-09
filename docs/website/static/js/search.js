(function () {
  var input = document.getElementById('search-input');
  var box = document.getElementById('search-results');
  if (!input || !box) return;
  var idx = null, loading = false;

  function load() {
    if (idx || loading) return;
    loading = true;
    fetch(window.SEARCH_INDEX || '/index.json').then(function (r) { return r.json(); }).then(function (d) { idx = d; });
  }
  input.addEventListener('focus', load);

  function esc(s) { return s.replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }

  function search(q) {
    if (!idx || q.length < 2) { box.classList.remove('show'); box.innerHTML = ''; return; }
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    var hits = [];
    for (var i = 0; i < idx.length; i++) {
      var p = idx[i];
      var hay = (p.title + ' ' + p.section + ' ' + p.text).toLowerCase();
      var ok = true, score = 0;
      for (var t = 0; t < terms.length; t++) {
        var pos = hay.indexOf(terms[t]);
        if (pos < 0) { ok = false; break; }
        score += p.title.toLowerCase().indexOf(terms[t]) >= 0 ? 10 : 1;
      }
      if (ok) hits.push({ p: p, score: score });
    }
    hits.sort(function (a, b) { return b.score - a.score; });
    hits = hits.slice(0, 12);
    if (!hits.length) { box.innerHTML = '<a><span class="r-title">No results</span></a>'; box.classList.add('show'); return; }
    box.innerHTML = hits.map(function (h) {
      return '<a href="' + h.p.url + '"><span class="r-sec">' + esc(h.p.section || '') +
        '</span><div class="r-title">' + esc(h.p.title) + '</div></a>';
    }).join('');
    box.classList.add('show');
  }

  input.addEventListener('input', function () { search(input.value.trim()); });
  document.addEventListener('click', function (e) {
    if (!box.contains(e.target) && e.target !== input) box.classList.remove('show');
  });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { var a = box.querySelector('a[href]'); if (a) window.location = a.getAttribute('href'); }
    if (e.key === 'Escape') { box.classList.remove('show'); input.blur(); }
  });
})();
