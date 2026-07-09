(function () {
  var root = document.documentElement;
  var saved = localStorage.getItem('refs-theme');
  if (saved) root.setAttribute('data-theme', saved);
  function setIcon() {
    var b = document.getElementById('theme-toggle');
    if (b) b.textContent = root.getAttribute('data-theme') === 'dark' ? '☀' : '☾';
  }
  setIcon();
  function bar() { return document.querySelector('.topbar'); }
  function closeNav() {
    var b = bar(); if (b) b.classList.remove('nav-open');
    var nt = document.getElementById('nav-toggle');
    if (nt) nt.setAttribute('aria-expanded', 'false');
  }
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t && t.id === 'theme-toggle') {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      localStorage.setItem('refs-theme', next);
      setIcon();
      return;
    }
    if (t && t.id === 'nav-toggle') {
      var b = bar(); if (!b) return;
      var open = b.classList.toggle('nav-open');
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
      return;
    }
    // tapping a menu link closes the mobile menu
    if (t && t.closest && t.closest('.topbar nav a')) closeNav();
  });
  window.addEventListener('resize', function () {
    if (window.innerWidth > 760) closeNav();
  });
})();
