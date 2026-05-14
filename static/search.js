(() => {
  const input = document.querySelector('#search-input');
  const results = document.querySelector('#search-results');
  const count = document.querySelector('#search-count');
  if (!input || !results || !count) return;

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));

  const normalize = (value) => String(value || '').toLowerCase().trim();
  const tokensFor = (query) => normalize(query).split(/\s+/).filter(Boolean);
  const tagsFor = (item) => Array.isArray(item.tags) ? item.tags.join(' ') : '';

  const render = (items, tokens) => {
    if (!tokens.length) {
      count.textContent = '輸入關鍵字後開始搜尋。';
      results.innerHTML = '';
      return;
    }
    const matches = items
      .map((item) => {
        const tags = tagsFor(item);
        const haystack = normalize(`${item.title} ${item.summary} ${item.section} ${tags} ${item.text}`);
        const score = tokens.reduce((sum, token) => sum + (haystack.includes(token) ? 1 : 0), 0);
        return { item, score };
      })
      .filter(({ score }) => score === tokens.length)
      .slice(0, 20);

    count.textContent = matches.length ? `找到 ${matches.length} 筆。` : '沒有找到。';
    results.innerHTML = matches.map(({ item }) => {
      const tags = tagsFor(item);
      const tagText = tags ? ` · ${tags.split(/\s+/).filter(Boolean).map((tag) => `#${tag}`).join(' ')}` : '';
      return `
      <article class="post-card search-result">
        <h2><a href="${escapeHtml(item.url)}">${escapeHtml(item.title)}</a></h2>
        <p class="meta">${escapeHtml(item.date)} · ${escapeHtml(item.section)}${escapeHtml(tagText)}</p>
        <p class="summary">${escapeHtml(item.summary || '')}</p>
      </article>
    `;
    }).join('');
  };

  fetch('/search-index.json', { cache: 'no-store' })
    .then((response) => response.ok ? response.json() : Promise.reject(new Error('search index missing')))
    .then((items) => {
      const update = () => render(items, tokensFor(input.value));
      input.addEventListener('input', update);
      update();
    })
    .catch(() => {
      count.textContent = '搜尋索引載入失敗。';
    });
})();
