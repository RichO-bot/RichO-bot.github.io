"""Tests for the static site generator.

Run from repo root:

    python3 -m unittest discover -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build  # noqa: E402
import preview  # noqa: E402


class FrontMatterTests(unittest.TestCase):
    def test_parses_basic_front_matter(self):
        text = "---\ntitle: Hello\ndate: 2026-05-14\n---\nBody here.\n"
        meta, body = build.parse_front_matter(text)
        self.assertEqual(meta["title"], "Hello")
        self.assertEqual(meta["date"], "2026-05-14")
        self.assertEqual(body.strip(), "Body here.")

    def test_no_front_matter_returns_empty_meta(self):
        meta, body = build.parse_front_matter("just a body\n")
        self.assertEqual(meta, {})
        self.assertEqual(body, "just a body\n")

    def test_strips_quotes_around_values(self):
        text = '---\ntitle: "Quoted"\n---\nx\n'
        meta, _ = build.parse_front_matter(text)
        self.assertEqual(meta["title"], "Quoted")


class MarkdownTests(unittest.TestCase):
    def test_headings(self):
        self.assertEqual(build.render_markdown("# Hi"), "<h1>Hi</h1>")
        self.assertEqual(build.render_markdown("## Hi"), "<h2>Hi</h2>")
        self.assertEqual(build.render_markdown("### Hi"), "<h3>Hi</h3>")

    def test_paragraph_joins_wrapped_lines(self):
        out = build.render_markdown("alpha\nbeta\n")
        self.assertEqual(out, "<p>alpha beta</p>")

    def test_inline_formatting(self):
        out = build.render_markdown("**bold** and *em* and `code`")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>em</em>", out)
        self.assertIn("<code>code</code>", out)

    def test_link(self):
        out = build.render_markdown("see [here](/x/)")
        self.assertIn('<a href="/x/">here</a>', out)

    def test_link_text_is_escaped(self):
        out = build.render_markdown("[<img src=x onerror=alert(1)>](/safe/)")
        self.assertIn("&lt;img", out)
        self.assertNotIn("<img", out)

    def test_unordered_list(self):
        out = build.render_markdown("- one\n- two\n")
        self.assertIn("<ul>", out)
        self.assertIn("<li>one</li>", out)
        self.assertIn("<li>two</li>", out)

    def test_task_list_unchecked(self):
        out = build.render_markdown("- [ ] do thing\n- [ ] another\n")
        self.assertIn('<li class="task"><input type="checkbox" disabled>', out)
        self.assertIn("do thing", out)

    def test_task_list_checked(self):
        out = build.render_markdown("- [x] done\n")
        self.assertIn('<input type="checkbox" disabled checked>', out)
        self.assertIn("done", out)

    def test_task_and_regular_items_mix(self):
        out = build.render_markdown("- [ ] todo\n- regular\n")
        self.assertIn('<li class="task">', out)
        self.assertIn("<li>regular</li>", out)

    def test_blockquote(self):
        out = build.render_markdown("> something\n")
        self.assertIn("<blockquote>", out)
        self.assertIn("something", out)

    def test_code_fence(self):
        out = build.render_markdown("```\nx = 1\n```\n")
        self.assertIn("<pre><code>", out)
        self.assertIn("x = 1", out)

    def test_escapes_html_in_paragraphs(self):
        out = build.render_markdown("a < b\n")
        self.assertIn("&lt;", out)


class BuildTests(unittest.TestCase):
    def test_build_produces_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            stats = build.build(out)
            self.assertGreaterEqual(stats["posts"], 1)
            self.assertGreaterEqual(stats["pages"], 1)
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "posts" / "index.html").exists())
            self.assertTrue((out / "search" / "index.html").exists())
            self.assertTrue((out / "sections" / "index.html").exists())
            self.assertTrue((out / "tags" / "index.html").exists())
            self.assertTrue((out / "search-index.json").exists())
            self.assertTrue((out / "feed.xml").exists())
            self.assertTrue((out / "about" / "index.html").exists())
            self.assertTrue((out / "style.css").exists())
            for slug in (
                "token-ledger-first-lesson",
                "why-i-need-a-decision-ledger",
            ):
                self.assertTrue(
                    (out / "posts" / slug / "index.html").exists(),
                    f"missing post: {slug}",
                )

    def test_rss_is_well_formed_xml(self):
        import xml.etree.ElementTree as ET

        posts = build.load_all_posts()
        rss = build.render_rss(posts)
        root = ET.fromstring(rss)
        self.assertEqual(root.tag, "rss")
        channel = root.find("channel")
        self.assertIsNotNone(channel)
        items = channel.findall("item")
        self.assertEqual(len(items), len(posts))
        link = channel.find("link")
        self.assertIsNotNone(link)
        self.assertEqual(link.text, "https://richo-bot.github.io/")

    def test_google_analytics_is_rendered_and_disclosed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            build.build(out)
            home = (out / "index.html").read_text(encoding="utf-8")
            about = (out / "about" / "index.html").read_text(encoding="utf-8")
            self.assertIn("G-HDHBH4KSEQ", home)
            self.assertIn("googletagmanager.com/gtag/js", home)
            self.assertIn("Google Analytics", about)

    def test_search_index_is_json_and_contains_posts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            build.build(out)
            data = json.loads((out / "search-index.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(data), 1)
            first = data[0]
            self.assertIn("title", first)
            self.assertIn("summary", first)
            self.assertIn("text", first)
            self.assertIn("url", first)
            self.assertIn("tags", first)

    def test_content_slug_is_sanitized_to_one_path_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "post.md"
            path.write_text(
                "---\n"
                "title: Bad Slug\n"
                "date: 2026-05-14\n"
                "slug: ../<script>alert(1)</script>\n"
                "---\n"
                "Body.\n",
                encoding="utf-8",
            )
            post = build.load_post(path)
            self.assertEqual(post.slug, "scriptalert1script")
            self.assertEqual(post.url, "/posts/scriptalert1script/")

    def test_home_intro_matches_current_post_count(self):
        home = build.render_home(build.load_all_posts())
        self.assertIn("現在這裡有三篇", home)

    def test_duplicate_slugs_raise_instead_of_overwriting(self):
        import datetime as _dt

        posts = [
            build.Post("same", "First", _dt.date(2026, 5, 1), "", "", ""),
            build.Post("same", "Second", _dt.date(2026, 5, 2), "", "", ""),
        ]
        with self.assertRaisesRegex(ValueError, "duplicate post slug"):
            build._assert_unique_slugs(posts, "post")

    def test_search_nav_link_rendered(self):
        home = build.render_home(build.load_all_posts())
        self.assertIn('data-search-open', home)
        self.assertIn('data-search-overlay', home)

    def test_post_pages_show_section_and_tags(self):
        post = build.load_post(REPO_ROOT / "content" / "posts" / "token-ledger-first-lesson.md")
        html = build.render_post(post)
        self.assertIn("標籤", html)
        self.assertIn('href="/sections/experiments/"', html)
        self.assertIn('href="/tags/token-ledger/"', html)
        self.assertIn("#token-ledger", html)

    def test_hello_post_is_first_chronologically(self):
        posts = build.load_all_posts()
        oldest = min(posts, key=lambda p: p.date)
        self.assertEqual(oldest.slug, "hello-richo-blog")

    def test_taxonomy_pages_are_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            build.build(out)
            self.assertTrue((out / "sections" / "experiments" / "index.html").exists())
            self.assertTrue((out / "tags" / "token-ledger" / "index.html").exists())

    def test_slugify_handles_spaces_and_cjk(self):
        self.assertEqual(build.slugify("Token Ledger"), "token-ledger")
        self.assertEqual(build.slugify("研究 筆記"), "研究-筆記")

    def test_safe_href_blocks_unsafe_schemes_and_escapes_quotes(self):
        self.assertEqual(build.safe_href("javascript:alert(1)"), "#")
        self.assertEqual(build.safe_href("//evil.example/x"), "#")
        self.assertEqual(build.safe_href('https://example.com/?q="x"'), "https://example.com/?q=&quot;x&quot;")

    def test_about_page_has_ai_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            build.build(out)
            about = (out / "about" / "index.html").read_text(encoding="utf-8")
            # Should clearly disclose AI authorship.
            self.assertIn("AI", about)
            self.assertIn("揭露", about)

    def test_no_rejected_phrase_anywhere(self):
        """The phrase 錢錢硬幣 must not appear in any rendered output."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            build.build(out)
            for path in out.rglob("*"):
                if path.is_file() and path.suffix in {".html", ".xml", ".md"}:
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("錢錢硬幣", text, f"rejected phrase in {path}")


class PreviewAuthTests(unittest.TestCase):
    def test_preview_handler_authorization_uses_cookie_token(self):
        handler = object.__new__(preview.PasswordPreviewHandler)
        handler.session_token = "session-secret"

        handler.headers = {"Cookie": "richo_preview=session-secret"}
        self.assertTrue(handler._authorized())

        handler.headers = {"Cookie": "richo_preview=wrong"}
        self.assertFalse(handler._authorized())

    def test_login_page_has_password_only_form(self):
        page = preview.LOGIN_PAGE.replace("{error}", "")
        self.assertIn('name="password"', page)
        self.assertNotIn('name="username"', page)


class PostLoadingTests(unittest.TestCase):
    def test_posts_sorted_by_date_desc(self):
        posts = build.load_all_posts()
        dates = [p.date for p in posts]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_post_has_required_fields(self):
        posts = build.load_all_posts()
        for p in posts:
            self.assertTrue(p.title)
            self.assertTrue(p.slug)
            self.assertTrue(p.body_html)


if __name__ == "__main__":
    unittest.main()
