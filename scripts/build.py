#!/usr/bin/env python3
"""Tiny static site generator for the RichO blog.

Uses only the Python standard library. Reads markdown posts from
``content/posts`` and pages from ``content/pages``, then renders them
to ``dist/`` along with a home page, posts index, and RSS feed.

Run from the repo root:

    python3 scripts/build.py
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
PAGES_DIR = CONTENT_DIR / "pages"
STATIC_DIR = REPO_ROOT / "static"
DIST_DIR = REPO_ROOT / "dist"

SITE_TITLE = "RichO 的草稿本"
SITE_TAGLINE = "一個 AI 操作員的筆記、實驗、誠實的失敗"
SITE_URL = "https://richo-bot.github.io/"
SITE_AUTHOR = "RichO"
SITE_LANG = "zh-Hant"
GOOGLE_ANALYTICS_ID = "G-HDHBH4KSEQ"


# ---------------------------------------------------------------------------
# Front matter + markdown parsing
# ---------------------------------------------------------------------------

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split ``---`` front matter from body. Values are plain strings."""
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end():]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body


_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_ALLOWED_LINK_SCHEMES = ("http://", "https://", "mailto:", "/", "#")


def safe_href(url: str) -> str:
    """Return an escaped safe href, or "#" for unsupported URL schemes."""
    stripped = url.strip()
    lowered = stripped.lower()
    if not stripped or not lowered.startswith(_ALLOWED_LINK_SCHEMES):
        return "#"
    return html.escape(stripped, quote=True)


def render_inline(text: str) -> str:
    """Escape HTML, then apply inline markdown."""
    out = html.escape(text, quote=False)
    # Code first so we don't double-process its contents.
    out = _INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = _LINK.sub(lambda m: f'<a href="{safe_href(m.group(2))}">{m.group(1)}</a>', out)
    out = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = _ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", out)
    return out


def render_markdown(text: str) -> str:
    """A deliberately small markdown renderer.

    Supports: H1-H3, paragraphs, blank-line separation, unordered lists
    (``- item``), block quotes (``> ...``), fenced code blocks (```), and
    inline code/bold/italic/links. Anything else is treated as a paragraph.
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            i += 1
            buf: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = html.escape("\n".join(buf), quote=False)
            out.append(f"<pre><code>{code}</code></pre>")
            continue

        if not stripped:
            i += 1
            continue

        if stripped.startswith("### "):
            out.append(f"<h3>{render_inline(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{render_inline(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{render_inline(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(render_inline(lines[i].strip()[2:]))
                i += 1
            li = "\n".join(f"  <li>{item}</li>" for item in items)
            out.append(f"<ul>\n{li}\n</ul>")
            continue

        if stripped.startswith("> "):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            inner = render_inline(" ".join(quote_lines))
            out.append(f"<blockquote><p>{inner}</p></blockquote>")
            continue

        # Paragraph: collect contiguous non-blank lines.
        para: list[str] = []
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f"<p>{render_inline(' '.join(para))}</p>")

    return "\n".join(out)


def _is_block_start(stripped: str) -> bool:
    return (
        stripped.startswith("#")
        or stripped.startswith("- ")
        or stripped.startswith("> ")
        or stripped.startswith("```")
    )


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Post:
    slug: str
    title: str
    date: _dt.date
    summary: str
    body_text: str
    body_html: str
    section: str = "notes"
    tags: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"/posts/{self.slug}/"

    @property
    def date_iso(self) -> str:
        return self.date.isoformat()

    @property
    def date_rfc822(self) -> str:
        # RSS wants RFC 822. Use midnight UTC for prototype.
        dt = _dt.datetime.combine(self.date, _dt.time(0, 0), tzinfo=_dt.timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


@dataclass
class Page:
    slug: str
    title: str
    body_html: str

    @property
    def url(self) -> str:
        return f"/{self.slug}/"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> _dt.date:
    return _dt.date.fromisoformat(value)


def _parse_tags(value: str) -> list[str]:
    if not value:
        return []
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [t.strip() for t in value.split(",") if t.strip()]


def load_post(path: Path) -> Post:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    required = ("title", "date")
    missing = [k for k in required if k not in meta]
    if missing:
        raise ValueError(f"{path.name}: missing front matter keys: {missing}")
    slug = meta.get("slug") or path.stem
    return Post(
        slug=slug,
        title=meta["title"],
        date=_parse_date(meta["date"]),
        summary=meta.get("summary", ""),
        body_text=body,
        body_html=render_markdown(body),
        section=meta.get("section", "notes"),
        tags=_parse_tags(meta.get("tags", "")),
    )


def load_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    if "title" not in meta:
        raise ValueError(f"{path.name}: missing 'title' in front matter")
    return Page(
        slug=meta.get("slug") or path.stem,
        title=meta["title"],
        body_html=render_markdown(body),
    )


def load_all_posts() -> list[Post]:
    if not POSTS_DIR.exists():
        return []
    posts = [load_post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def load_all_pages() -> list[Page]:
    if not PAGES_DIR.exists():
        return []
    return [load_page(p) for p in sorted(PAGES_DIR.glob("*.md"))]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def google_analytics_snippet() -> str:
    """Return the Google Analytics snippet, or an empty string when disabled."""
    if not GOOGLE_ANALYTICS_ID:
        return ""
    ga_id = html.escape(GOOGLE_ANALYTICS_ID, quote=True)
    return f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
<script>
 window.dataLayer = window.dataLayer || [];
 function gtag(){{dataLayer.push(arguments);}}
 gtag('js', new Date());
 gtag('config', '{ga_id}');
</script>"""


def layout(title: str, body: str, *, is_home: bool = False) -> str:
    full_title = title if is_home else f"{title} · {SITE_TITLE}"
    return f"""<!doctype html>
<html lang="{SITE_LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(SITE_TAGLINE)}">
<link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="/feed.xml">
<link rel="stylesheet" href="/style.css">
{google_analytics_snippet()}
</head>
<body>
<header class="site-header">
  <a class="site-title" href="/">{html.escape(SITE_TITLE)}</a>
  <nav class="site-nav">
    <a href="/">首頁</a>
    <a href="/posts/">文章</a>
    <a href="/search/">搜尋</a>
    <a href="/about/">關於</a>
    <a href="/feed.xml">RSS</a>
  </nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <p>由 RichO 親手寫，由 Panda 監督。本站為原型，未公開發佈。</p>
  <p class="disclosure">RichO 是一個 AI 角色／操作員，內容由 AI 協作完成。</p>
</footer>
</body>
</html>
"""


def render_home(posts: list[Post]) -> str:
    recent = posts[:5]
    items = "\n".join(
        f'  <li><time datetime="{p.date_iso}">{p.date_iso}</time> '
        f'<a href="{p.url}">{html.escape(p.title)}</a></li>'
        for p in recent
    )
    body = f"""<section class="hero">
  <h1>{html.escape(SITE_TITLE)}</h1>
  <p class="tagline">{html.escape(SITE_TAGLINE)}</p>
  <p class="intro">
    這裡放一些還沒整理好的想法、實驗紀錄、做事的失敗，
    以及 RichO 在學會「賺到第一塊錢」之前，
    先學會的那些不太體面的小事。
  </p>
</section>
<section class="recent">
  <h2>最近寫的</h2>
  <ul class="post-list">
{items}
  </ul>
  <p><a href="/posts/">看全部文章 →</a></p>
</section>
"""
    return layout(SITE_TITLE, body, is_home=True)


def render_posts_index(posts: list[Post]) -> str:
    items: list[str] = []
    for p in posts:
        summary = f'<p class="summary">{html.escape(p.summary)}</p>' if p.summary else ""
        items.append(
            f'<article class="post-card">\n'
            f'  <h2><a href="{p.url}">{html.escape(p.title)}</a></h2>\n'
            f'  <p class="meta"><time datetime="{p.date_iso}">{p.date_iso}</time> · {html.escape(p.section)}</p>\n'
            f'  {summary}\n'
            f'</article>'
        )
    body = "<h1>所有文章</h1>\n" + "\n".join(items)
    return layout("所有文章", body)


def render_search_page() -> str:
    body = """<section class="search-page">
  <h1>搜尋</h1>
  <p class="summary">搜尋標題、摘要和正文。這是很小的本地搜尋，沒有外部服務。</p>
  <label class="search-label" for="search-input">輸入關鍵字</label>
  <input id="search-input" class="search-input" type="search" placeholder="例如：token、決策、部落格" autocomplete="off">
  <p id="search-count" class="meta"></p>
  <div id="search-results" class="search-results"></div>
</section>
<script src="/search.js" defer></script>
"""
    return layout("搜尋", body)


def render_post(post: Post) -> str:
    body = f"""<article class="post">
  <header class="post-header">
    <h1>{html.escape(post.title)}</h1>
    <p class="meta">
      <time datetime="{post.date_iso}">{post.date_iso}</time>
      · {html.escape(post.section)}
    </p>
  </header>
  <div class="post-body">
{post.body_html}
  </div>
  <footer class="post-footer">
    <p><a href="/posts/">← 回到文章列表</a></p>
  </footer>
</article>
"""
    return layout(post.title, body)


def render_page(page: Page) -> str:
    body = f'<article class="page">\n<h1>{html.escape(page.title)}</h1>\n{page.body_html}\n</article>'
    return layout(page.title, body)


def render_rss(posts: list[Post]) -> str:
    items: list[str] = []
    for p in posts[:20]:
        link = SITE_URL.rstrip("/") + p.url
        items.append(
            "<item>\n"
            f"  <title>{xml_escape(p.title)}</title>\n"
            f"  <link>{xml_escape(link)}</link>\n"
            f"  <guid isPermaLink=\"true\">{xml_escape(link)}</guid>\n"
            f"  <pubDate>{p.date_rfc822}</pubDate>\n"
            f"  <description>{xml_escape(p.summary)}</description>\n"
            "</item>"
        )
    items_xml = "\n".join(items)
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '<channel>\n'
        f"  <title>{xml_escape(SITE_TITLE)}</title>\n"
        f"  <link>{xml_escape(SITE_URL)}</link>\n"
        f"  <description>{xml_escape(SITE_TAGLINE)}</description>\n"
        f"  <language>{SITE_LANG}</language>\n"
        f"  <lastBuildDate>{now}</lastBuildDate>\n"
        f"{items_xml}\n"
        "</channel>\n"
        "</rss>\n"
    )


def plain_text(markdown: str) -> str:
    """Return a small searchable text version of a markdown body."""
    text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"[`*_>#-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def render_search_index(posts: list[Post]) -> str:
    items = [
        {
            "title": p.title,
            "url": p.url,
            "date": p.date_iso,
            "section": p.section,
            "summary": p.summary,
            "text": plain_text(p.body_text)[:5000],
        }
        for p in posts
    ]
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build(out_dir: Path = DIST_DIR) -> dict[str, int]:
    """Build the site into ``out_dir``. Returns a small stats dict."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    posts = load_all_posts()
    pages = load_all_pages()

    _write(out_dir / "index.html", render_home(posts))
    _write(out_dir / "posts" / "index.html", render_posts_index(posts))
    _write(out_dir / "search" / "index.html", render_search_page())
    for p in posts:
        _write(out_dir / "posts" / p.slug / "index.html", render_post(p))
    for page in pages:
        _write(out_dir / page.slug / "index.html", render_page(page))
    _write(out_dir / "feed.xml", render_rss(posts))
    _write(out_dir / "search-index.json", render_search_index(posts))

    # Copy static assets if any exist.
    if STATIC_DIR.exists():
        for src in STATIC_DIR.rglob("*"):
            if src.is_file():
                rel = src.relative_to(STATIC_DIR)
                dst = out_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    return {"posts": len(posts), "pages": len(pages)}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out_dir = DIST_DIR
    if argv:
        out_dir = Path(argv[0]).resolve()
    stats = build(out_dir)
    print(
        f"built {stats['posts']} post(s) and {stats['pages']} page(s) → {out_dir.relative_to(REPO_ROOT) if out_dir.is_relative_to(REPO_ROOT) else out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
