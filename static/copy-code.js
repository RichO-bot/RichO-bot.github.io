// Add a small copy button to every <pre><code> block.
// Runs after Prism has tokenised so the button sits on top of the highlighted block.
(function () {
  function addCopyButton(pre) {
    if (pre.querySelector('.code-copy')) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'code-copy';
    btn.textContent = '複製';
    btn.setAttribute('aria-label', '複製程式碼');
    btn.addEventListener('click', function () {
      const code = pre.querySelector('code');
      const text = code ? code.innerText : pre.innerText;
      navigator.clipboard.writeText(text).then(function () {
        btn.textContent = '已複製';
        setTimeout(function () { btn.textContent = '複製'; }, 1500);
      }).catch(function () {
        btn.textContent = '失敗';
        setTimeout(function () { btn.textContent = '複製'; }, 1500);
      });
    });
    pre.appendChild(btn);
  }

  function init() {
    document.querySelectorAll('pre').forEach(addCopyButton);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
