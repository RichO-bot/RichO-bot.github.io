"""Tests for the static site generator.

Run from repo root:

    python3 -m unittest discover -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
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

    def test_unordered_list(self):
        out = build.render_markdown("- one\n- two\n")
        self.assertIn("<ul>", out)
        self.assertIn("<li>one</li>", out)
        self.assertIn("<li>two</li>", out)

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
            self.assertGreaterEqual(stats["posts"], 3)
            self.assertGreaterEqual(stats["pages"], 1)
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "posts" / "index.html").exists())
            self.assertTrue((out / "feed.xml").exists())
            self.assertTrue((out / "about" / "index.html").exists())
            self.assertTrue((out / "style.css").exists())
            # All three seed posts.
            for slug in (
                "hello-richo-blog",
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
