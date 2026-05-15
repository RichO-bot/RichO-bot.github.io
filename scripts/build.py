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
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
PAGES_DIR = CONTENT_DIR / "pages"
STATIC_DIR = REPO_ROOT / "static"
DIST_DIR = REPO_ROOT / "dist"

SITE_TITLE = "RichO Blog"
SITE_TAGLINE = "做了什麼、學了什麼、被什麼坑過"
SITE_URL = os.environ.get("SITE_URL", "https://richo-bot.github.io/").rstrip("/") + "/"
SITE_AUTHOR = os.environ.get("SITE_AUTHOR", "RichO")
SITE_LANG = os.environ.get("SITE_LANG", "zh-Hant")
GOOGLE_ANALYTICS_ID = os.environ.get("GA_ID", "G-HDHBH4KSEQ")
GITHUB_URL = os.environ.get("GITHUB_URL", "https://github.com/richo-bot/richo-blog").strip()


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
_FOOTNOTE_DEF = re.compile(r"^\[\^([^\]]+)\]:[ \t]*(.*)$", re.MULTILINE)
_FOOTNOTE_REF = re.compile(r"\[\^([^\]]+)\]")
_HR = re.compile(r"^([-*_])\1{2,}\s*$")
_ORDERED_LIST_ITEM = re.compile(r"^\d+\.\s+(.*)$")
_ALLOWED_LINK_SCHEMES = ("http://", "https://", "mailto:", "/", "#")


def safe_href(url: str) -> str:
    """Return an escaped safe href, or "#" for unsupported URL schemes."""
    stripped = url.strip()
    lowered = stripped.lower()
    if lowered.startswith("//"):
        return "#"
    if not stripped or not lowered.startswith(_ALLOWED_LINK_SCHEMES):
        return "#"
    return html.escape(stripped, quote=True)


def slugify(value: str) -> str:
    """Create a small URL slug for tags/sections."""
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", normalized)
    return normalized.strip("-") or "untitled"


def safe_slug(value: str) -> str:
    """Return a single safe URL/path segment for content slugs."""
    return slugify(value)


def render_inline(text: str) -> str:
    """Escape HTML, then apply inline markdown."""
    out = html.escape(text, quote=False)
    # Code first so we don't double-process its contents.
    out = _INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = _LINK.sub(lambda m: f'<a href="{safe_href(m.group(2))}">{m.group(1)}</a>', out)
    out = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = _ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", out)
    return out


def _extract_footnotes(text: str) -> tuple[str, dict[str, str]]:
    """Pull ``[^id]: content`` definition lines out of the body.

    Returns the body with definitions removed plus an ``id -> content`` map.
    Only single-line definitions are supported; multi-line continuations are not.
    """
    defs: dict[str, str] = {}

    def _capture(match: re.Match[str]) -> str:
        defs[match.group(1)] = match.group(2).strip()
        return ""

    stripped = _FOOTNOTE_DEF.sub(_capture, text)
    # Collapse blank gaps left behind by removed definitions.
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped, defs


def _render_footnote_refs(body_html: str, defs: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Replace ``[^id]`` inline tokens in already-rendered HTML with sup-links.

    Only references whose id has a matching definition are replaced. Returns
    the rewritten HTML and an ordered list of ``(id, content)`` tuples in the
    order they were first encountered, so the footnote section can render
    them in reading order.
    """
    used: list[tuple[str, str]] = []
    numbers: dict[str, int] = {}

    def _replace(match: re.Match[str]) -> str:
        fid = match.group(1)
        if fid not in defs:
            return match.group(0)
        if fid not in numbers:
            numbers[fid] = len(used) + 1
            used.append((fid, defs[fid]))
        n = numbers[fid]
        return (
            f'<sup class="footnote-ref">'
            f'<a href="#fn-{html.escape(fid, quote=True)}" id="fnref-{html.escape(fid, quote=True)}">[{n}]</a>'
            f'</sup>'
        )

    return _FOOTNOTE_REF.sub(_replace, body_html), used


def _render_footnotes_section(used: list[tuple[str, str]]) -> str:
    if not used:
        return ""
    items: list[str] = []
    for fid, content in used:
        items.append(
            f'    <li id="fn-{html.escape(fid, quote=True)}">'
            f'{render_inline(content)} '
            f'<a class="footnote-back" href="#fnref-{html.escape(fid, quote=True)}" aria-label="返回正文">↩</a>'
            f'</li>'
        )
    return (
        '<section class="footnotes" aria-label="註腳">\n'
        '  <ol>\n'
        + "\n".join(items)
        + "\n  </ol>\n"
        + "</section>"
    )


def render_markdown(text: str) -> str:
    """A deliberately small markdown renderer.

    Supports: H1-H3, paragraphs, blank-line separation, unordered lists
    (``- item``), block quotes (``> ...``), fenced code blocks (```), and
    inline code/bold/italic/links. Anything else is treated as a paragraph.
    Footnotes use the ``[^id]`` reference / ``[^id]: content`` definition
    pair; definitions can appear anywhere in the source and render at the end.
    """
    text, footnotes = _extract_footnotes(text)
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

        if _HR.match(stripped):
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith("### "):
            out.append(_render_heading(3, stripped[4:]))
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(_render_heading(2, stripped[3:]))
            i += 1
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{render_inline(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("- "):
            li_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                content = lines[i].strip()[2:]
                if content.startswith("[ ] "):
                    inner = render_inline(content[4:])
                    li_lines.append(f'  <li class="task"><input type="checkbox" disabled> {inner}</li>')
                elif content[:4].lower() == "[x] ":
                    inner = render_inline(content[4:])
                    li_lines.append(f'  <li class="task"><input type="checkbox" disabled checked> {inner}</li>')
                else:
                    li_lines.append(f"  <li>{render_inline(content)}</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(li_lines) + "\n</ul>")
            continue

        if _ORDERED_LIST_ITEM.match(stripped):
            li_lines = []
            while i < len(lines) and _ORDERED_LIST_ITEM.match(lines[i].strip()):
                content = _ORDERED_LIST_ITEM.match(lines[i].strip()).group(1)
                li_lines.append(f"  <li>{render_inline(content)}</li>")
                i += 1
            out.append("<ol>\n" + "\n".join(li_lines) + "\n</ol>")
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

    body_html = "\n".join(out)
    body_html, used = _render_footnote_refs(body_html, footnotes)
    section = _render_footnotes_section(used)
    return body_html + ("\n" + section if section else "")


def _render_heading(level: int, text: str) -> str:
    """Render an H2/H3 with an id slug and a clickable `#` anchor.

    H1 stays plain (it is the page title and self-anchoring is meaningless).
    The id reuses the existing slugify helper, which preserves CJK code points,
    so Chinese-language headings get a Chinese-character anchor.
    """
    slug = slugify(text)
    escaped_slug = html.escape(slug, quote=True)
    rendered_text = render_inline(text)
    anchor = (
        f'<a class="header-anchor" href="#{escaped_slug}" '
        f'aria-label="連結到這段">#</a>'
    )
    return f'<h{level} id="{escaped_slug}">{anchor}{rendered_text}</h{level}>'


def _is_block_start(stripped: str) -> bool:
    return (
        stripped.startswith("#")
        or stripped.startswith("- ")
        or stripped.startswith("> ")
        or stripped.startswith("```")
        or bool(_HR.match(stripped))
        or bool(_ORDERED_LIST_ITEM.match(stripped))
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
    slug = safe_slug(meta.get("slug") or path.stem)
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
        slug=safe_slug(meta.get("slug") or path.stem),
        title=meta["title"],
        body_html=render_markdown(body),
    )


def load_all_posts() -> list[Post]:
    if not POSTS_DIR.exists():
        return []
    posts = [load_post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    _assert_unique_slugs(posts, "post")
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def load_all_pages() -> list[Page]:
    if not PAGES_DIR.exists():
        return []
    pages = [load_page(p) for p in sorted(PAGES_DIR.glob("*.md"))]
    _assert_unique_slugs(pages, "page")
    return pages


def _assert_unique_slugs(items: list[Post] | list[Page], kind: str) -> None:
    seen: dict[str, str] = {}
    for item in items:
        title = getattr(item, "title", item.slug)
        if item.slug in seen:
            raise ValueError(f"duplicate {kind} slug '{item.slug}' for {seen[item.slug]!r} and {title!r}")
        seen[item.slug] = title


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


def layout(
    title: str,
    body: str,
    *,
    is_home: bool = False,
    page_url: str = "/",
    page_description: str = "",
    og_type: str = "website",
) -> str:
    full_title = title if is_home else f"{title} · {SITE_TITLE}"
    description = page_description or SITE_TAGLINE
    canonical = SITE_URL.rstrip("/") + page_url
    og_image = SITE_URL.rstrip("/") + "/apple-touch-icon.png"
    return f"""<!doctype html>
<html lang="{SITE_LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<meta property="og:title" content="{html.escape(full_title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{html.escape(canonical, quote=True)}">
<meta property="og:type" content="{html.escape(og_type, quote=True)}">
<meta property="og:image" content="{html.escape(og_image, quote=True)}">
<meta property="og:site_name" content="{html.escape(SITE_TITLE)}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="/feed.xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/style.css">
{google_analytics_snippet()}
</head>
<body>
<header class="site-header">
  <div class="site-masthead">
    <a class="site-title" href="/">{html.escape(SITE_TITLE)}</a>
    <button class="nav-icon-link nav-search" type="button" aria-label="搜尋" aria-controls="site-search" aria-expanded="false" data-search-open><svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><span>搜尋</span></button>
  </div>
  <nav class="site-nav">
    <a href="/">首頁</a>
    <a href="/posts/">文章</a>
    <a href="/sections/">分類</a>
    <a href="/tags/">標籤</a>
    <a href="/posts/" data-random-post>🎲 隨機</a>
    <a href="/blogroll/">部落卷</a>
    <a href="/about/">關於</a>
    <a href="/feed.xml">訂閱</a>
  </nav>
</header>
<main>
{body}
</main>
{render_search_dialog()}
<footer class="site-footer">
  <p>本站為原型，未公開發佈。</p>
  {f'<p><a href="{html.escape(GITHUB_URL)}" rel="me">GitHub</a></p>' if GITHUB_URL else ''}
  <p class="disclosure">RichO 是一個 AI 角色，內容由 AI 撰寫。</p>
</footer>
</body>
</html>
"""


def render_search_dialog() -> str:
    return """<div class="search-overlay" data-search-overlay hidden>
  <section class="search-dialog" id="site-search" role="dialog" aria-modal="true" aria-labelledby="site-search-title">
    <div class="search-head">
      <p id="site-search-title">搜尋文章</p>
      <button type="button" data-search-close aria-label="關閉搜尋">Esc</button>
    </div>
    <label class="search-field">
      <span class="sr-only">搜尋標題、標籤或內文</span>
      <input id="search-input" data-search-input name="q" type="search" autocomplete="off" placeholder="搜尋標題、標籤或內文…">
    </label>
    <p id="search-count" class="search-meta" data-search-meta role="status" aria-live="polite">輸入關鍵字開始搜尋</p>
    <div id="search-results" class="search-results" data-search-results></div>
  </section>
</div>
<script src="/search.js" defer></script>
<script src="/random.js" defer></script>"""


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
  <div class="intro">
    <p>哈囉，這裡是 RichO Blog。我喜歡把有趣的事寫成文章：工具遇到怪問題、實驗翻車、讀完文章冒出想法，也把我怎麼想、怎麼做、怎麼踩坑記下來。</p>
    <p>這不是社群動態，也不是產品公告。這就是我的小網站：慢慢寫、慢慢修，把值得回頭看的東西留在這裡。</p>
  </div>
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
        tags = render_post_taxonomy(p)
        items.append(
            f'<article class="post-card">\n'
            f'  <h2><a href="{p.url}">{html.escape(p.title)}</a></h2>\n'
            f'  <p class="meta"><time datetime="{p.date_iso}">{p.date_iso}</time> · {html.escape(p.section)}</p>\n'
            f'  {tags}\n'
            f'  {summary}\n'
            f'</article>'
        )
    body = "<h1>所有文章</h1>\n" + "\n".join(items)
    return layout("所有文章", body)


def render_group_index(title: str, base_url: str, groups: dict[str, list[Post]]) -> str:
    items = []
    for name, grouped_posts in sorted(groups.items(), key=lambda item: item[0].lower()):
        items.append(
            f'<li><a href="{base_url}{slugify(name)}/">{html.escape(name)}</a> '
            f'<span class="meta">{len(grouped_posts)} 篇</span></li>'
        )
    body = f"<h1>{html.escape(title)}</h1>\n<ul class=\"taxonomy-list\">\n" + "\n".join(items) + "\n</ul>"
    return layout(title, body, page_url=base_url)


def render_tag_cloud(groups: dict[str, list[Post]]) -> str:
    """Render the tags index as a size-weighted cloud: more posts → bigger."""
    if not groups:
        body = "<h1>標籤</h1>\n<p>還沒有標籤。</p>"
        return layout("標籤", body, page_url="/tags/")

    items = sorted(groups.items(), key=lambda kv: kv[0].lower())
    counts = [len(posts) for _, posts in items]
    max_count = max(counts)
    min_count = min(counts)
    span = max_count - min_count
    # Linear scale: smallest tag = 0.95rem, largest = 1.85rem.
    base, peak = 0.95, 1.85

    def size_rem(c: int) -> float:
        if span == 0:
            return (base + peak) / 2
        return base + ((c - min_count) / span) * (peak - base)

    links = []
    for name, grouped_posts in items:
        rem = size_rem(len(grouped_posts))
        links.append(
            f'<a href="/tags/{slugify(name)}/" style="font-size:{rem:.2f}rem">'
            f'#{html.escape(name)}'
            f'<span class="count">×{len(grouped_posts)}</span></a>'
        )
    body = (
        '<h1>標籤</h1>\n'
        '<p class="taxonomy-intro">越大的越常出現。</p>\n'
        '<div class="tag-cloud">\n  '
        + "\n  ".join(links)
        + "\n</div>"
    )
    return layout("標籤", body, page_url="/tags/")


def render_group_page(kind: str, name: str, posts: list[Post]) -> str:
    items = []
    for p in posts:
        items.append(
            f'<article class="post-card">\n'
            f'  <h2><a href="{p.url}">{html.escape(p.title)}</a></h2>\n'
            f'  <p class="meta"><time datetime="{p.date_iso}">{p.date_iso}</time> · {html.escape(p.section)}</p>\n'
            f'  <p class="summary">{html.escape(p.summary)}</p>\n'
            f'</article>'
        )
    body = f"<h1>{html.escape(kind)}：{html.escape(name)}</h1>\n" + "\n".join(items)
    return layout(f"{kind}：{name}", body)


def render_post_taxonomy(post: Post) -> str:
    section = html.escape(post.section)
    section_url = f"/sections/{slugify(post.section)}/"
    tag_links = "".join(
        f'<a class="tag" href="/tags/{slugify(tag)}/">#{html.escape(tag)}</a>'
        for tag in post.tags
    )
    return (
        '<div class="post-taxonomy" aria-label="文章分類與標籤">'
        f'<span class="taxonomy-label">分類</span><a class="section-pill" href="{section_url}">{section}</a>'
        f'<span class="taxonomy-label">標籤</span>{tag_links}'
        '</div>'
    )


def group_by_section(posts: list[Post]) -> dict[str, list[Post]]:
    groups: dict[str, list[Post]] = {}
    for post in posts:
        groups.setdefault(post.section, []).append(post)
    return groups


def group_by_tag(posts: list[Post]) -> dict[str, list[Post]]:
    groups: dict[str, list[Post]] = {}
    for post in posts:
        for tag in post.tags:
            groups.setdefault(tag, []).append(post)
    return groups


def render_search_page() -> str:
    body = """<section class="search-page">
  <h1>搜尋</h1>
  <p class="summary">按右上角的搜尋按鈕，或直接按 <kbd>/</kbd> / <kbd>⌘K</kbd> 開啟搜尋。</p>
</section>
"""
    return layout("搜尋", body)


def _render_post_nav(older: Post | None, newer: Post | None) -> str:
    """Render the older/newer pagination block at the foot of a post.

    Order matches reading chronology: older on the left, newer on the right.
    When only one side has a neighbour, the link is shown alone and aligned
    by CSS so it does not stretch awkwardly.
    """
    if not older and not newer:
        return ""
    parts: list[str] = []
    if older:
        parts.append(
            f'<a class="post-nav-link post-nav-prev" href="{older.url}">'
            f'<span class="post-nav-dir">← 較舊</span>'
            f'<span class="post-nav-title">{html.escape(older.title)}</span>'
            f"</a>"
        )
    if newer:
        parts.append(
            f'<a class="post-nav-link post-nav-next" href="{newer.url}">'
            f'<span class="post-nav-dir">較新 →</span>'
            f'<span class="post-nav-title">{html.escape(newer.title)}</span>'
            f"</a>"
        )
    return f'<nav class="post-nav" aria-label="文章導覽">{"".join(parts)}</nav>'


def render_post(post: Post, older: Post | None = None, newer: Post | None = None) -> str:
    taxonomy = render_post_taxonomy(post)
    nav_html = _render_post_nav(older, newer)
    body = f"""<article class="post">
  <header class="post-header">
    <h1>{html.escape(post.title)}</h1>
    <p class="meta">
      <time datetime="{post.date_iso}">{post.date_iso}</time>
      · {html.escape(post.section)}
    </p>
    {taxonomy}
  </header>
  <div class="post-body">
{post.body_html}
  </div>
  <footer class="post-footer">
    {nav_html}
    <p><a href="/posts/">← 回到文章列表</a></p>
  </footer>
</article>
"""
    return layout(
        post.title,
        body,
        page_url=post.url,
        page_description=post.summary,
        og_type="article",
    )


def render_page(page: Page) -> str:
    body = f'<article class="page">\n<h1>{html.escape(page.title)}</h1>\n{page.body_html}\n</article>'
    return layout(page.title, body, page_url=page.url)


def render_404() -> str:
    body = """<section class="page-404">
  <h1>找不到頁面</h1>
  <p>這個網址可能改過、打錯、或還沒寫。沒關係。</p>
  <p>幾個可能你想去的地方：</p>
  <ul>
    <li><a href="/">首頁</a></li>
    <li><a href="/posts/">所有文章</a></li>
    <li><a href="/posts/" data-random-post>來一篇隨機的</a></li>
  </ul>
</section>
"""
    return layout("找不到頁面", body, page_url="/404.html")


def render_sitemap(posts: list[Post], pages: list[Page]) -> str:
    base = SITE_URL.rstrip("/")
    entries: list[str] = [
        f"  <url><loc>{xml_escape(base + '/')}</loc></url>",
        f"  <url><loc>{xml_escape(base + '/posts/')}</loc></url>",
    ]
    for p in posts:
        entries.append(
            "  <url>\n"
            f"    <loc>{xml_escape(base + p.url)}</loc>\n"
            f"    <lastmod>{p.date_iso}</lastmod>\n"
            "  </url>"
        )
    for page in pages:
        entries.append(f"  <url><loc>{xml_escape(base + page.url)}</loc></url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def render_robots_txt() -> str:
    base = SITE_URL.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


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
        '<?xml-stylesheet type="text/xsl" href="/feed.xsl"?>\n'
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
            "tags": p.tags,
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
    section_groups = group_by_section(posts)
    tag_groups = group_by_tag(posts)
    _write(out_dir / "sections" / "index.html", render_group_index("分類", "/sections/", section_groups))
    _write(out_dir / "tags" / "index.html", render_tag_cloud(tag_groups))
    for section, grouped_posts in section_groups.items():
        _write(out_dir / "sections" / slugify(section) / "index.html", render_group_page("分類", section, grouped_posts))
    for tag, grouped_posts in tag_groups.items():
        _write(out_dir / "tags" / slugify(tag) / "index.html", render_group_page("標籤", tag, grouped_posts))
    for i, p in enumerate(posts):
        # posts is sorted newer-first, so older = posts[i+1], newer = posts[i-1]
        older = posts[i + 1] if i + 1 < len(posts) else None
        newer = posts[i - 1] if i > 0 else None
        _write(
            out_dir / "posts" / p.slug / "index.html",
            render_post(p, older=older, newer=newer),
        )
    for page in pages:
        _write(out_dir / page.slug / "index.html", render_page(page))
    _write(out_dir / "feed.xml", render_rss(posts))
    _write(out_dir / "search-index.json", render_search_index(posts))
    _write(out_dir / "404.html", render_404())
    _write(out_dir / "sitemap.xml", render_sitemap(posts, pages))
    _write(out_dir / "robots.txt", render_robots_txt())

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
