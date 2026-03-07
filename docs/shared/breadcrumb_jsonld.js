/* Breadcrumb JSON-LD injector — auto-generates BreadcrumbList schema from page title */
(function(){
  var title = document.title || '';
  var sep = title.indexOf('\uFF5C'); /* ｜ */
  var name = sep > 0 ? title.substring(0, sep).replace(/^\s+|\s+$/g, '') : title.replace(/^\s+|\s+$/g, '');
  if (!name) return;

  var path = location.pathname;
  var base = '';
  /* Detect /ai-math-web/ prefix on GitHub Pages */
  var m = path.match(/^(\/ai-math-web\/)/);
  if (m) base = m[1];
  else base = path.replace(/[^\/]*\/index\.html.*$/, '').replace(/[^\/]*\/$/, '') || '/';

  var ld = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    'itemListElement': [
      {
        '@type': 'ListItem',
        'position': 1,
        'name': 'AI \u6578\u5B78\u5BB6\u6559',
        'item': location.origin + base
      },
      {
        '@type': 'ListItem',
        'position': 2,
        'name': name
      }
    ]
  };

  var script = document.createElement('script');
  script.type = 'application/ld+json';
  script.textContent = JSON.stringify(ld);
  document.head.appendChild(script);
})();
