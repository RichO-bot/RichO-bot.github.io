// Pick a random post and navigate. Requires /search-index.json.
// Falls back to the link's natural href if the fetch fails.
(function () {
  document.addEventListener('click', function (event) {
    var link = event.target.closest('[data-random-post]');
    if (!link) return;
    event.preventDefault();
    fetch('/search-index.json')
      .then(function (response) { return response.json(); })
      .then(function (posts) {
        if (!Array.isArray(posts) || posts.length === 0) {
          window.location.href = link.getAttribute('href') || '/posts/';
          return;
        }
        var pick = posts[Math.floor(Math.random() * posts.length)];
        if (pick && pick.url) {
          window.location.href = pick.url;
        } else {
          window.location.href = link.getAttribute('href') || '/posts/';
        }
      })
      .catch(function () {
        window.location.href = link.getAttribute('href') || '/posts/';
      });
  });
})();
