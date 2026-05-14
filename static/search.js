(() => {
  const overlay = document.querySelector('[data-search-overlay]');
  const input = document.querySelector('[data-search-input]');
  const results = document.querySelector('[data-search-results]');
  const count = document.querySelector('[data-search-meta]');
  const openButtons = document.querySelectorAll('[data-search-open]');
  const closeButtons = document.querySelectorAll('[data-search-close]');
  if (!overlay || !input || !results || !count) return;

  let itemsPromise = null;
  let restoreFocusTo = null;

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
  const isEditable = (target) => target instanceof HTMLElement && Boolean(target.closest('input, textarea, select, [contenteditable="true"]'));

  const loadItems = () => {
    itemsPromise ??= fetch('/search-index.json', { cache: 'no-store' })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('search index missing')));
    return itemsPromise;
  };

  const render = (items, tokens) => {
    if (!tokens.length) {
      count.textContent = '輸入關鍵字開始搜尋';
      results.textContent = '';
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

    count.textContent = matches.length ? `找到 ${matches.length} 筆結果` : '沒有找到符合的內容';
    results.innerHTML = matches.map(({ item }) => {
      const tags = tagsFor(item);
      const tagText = tags ? ` · ${tags.split(/\s+/).filter(Boolean).map((tag) => `#${tag}`).join(' ')}` : '';
      return `
      <article class="search-result">
        <a href="${escapeHtml(item.url)}">
          <span class="result-kicker">${escapeHtml(item.date)} · ${escapeHtml(item.section)}${escapeHtml(tagText)}</span>
          <strong class="result-title">${escapeHtml(item.title)}</strong>
          <span class="result-snippet">${escapeHtml(item.summary || '')}</span>
        </a>
      </article>
    `;
    }).join('');
  };

  const update = () => {
    loadItems()
      .then((items) => render(items, tokensFor(input.value)))
      .catch(() => {
        count.textContent = '搜尋索引載入失敗。';
      });
  };

  const openSearch = () => {
    restoreFocusTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    overlay.hidden = false;
    document.documentElement.classList.add('search-open');
    openButtons.forEach((button) => button.setAttribute('aria-expanded', 'true'));
    requestAnimationFrame(() => input.focus());
    update();
  };

  const closeSearch = () => {
    overlay.hidden = true;
    document.documentElement.classList.remove('search-open');
    openButtons.forEach((button) => button.setAttribute('aria-expanded', 'false'));
    restoreFocusTo?.focus();
    restoreFocusTo = null;
  };

  openButtons.forEach((button) => button.addEventListener('click', openSearch));
  closeButtons.forEach((button) => button.addEventListener('click', closeSearch));
  input.addEventListener('input', update);
  overlay.addEventListener('mousedown', (event) => {
    if (event.target === overlay) closeSearch();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !overlay.hidden) {
      event.preventDefault();
      closeSearch();
      return;
    }
    if ((event.key === '/' && !isEditable(event.target)) || ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k')) {
      event.preventDefault();
      openSearch();
    }
  });

  const initialQuery = new URLSearchParams(window.location.search).get('q');
  if (initialQuery) {
    input.value = initialQuery;
    openSearch();
  }
})();
