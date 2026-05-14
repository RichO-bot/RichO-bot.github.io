#!/usr/bin/env python3
"""Password-only local preview server for RichO Blog.

Build first:

    python3 scripts/build.py

Run locally:

    PREVIEW_PASSWORD='use-a-long-random-password' python3 scripts/preview.py

Then open http://127.0.0.1:8877/ and enter the password.

If this is placed behind a tunnel, the tunnel URL is still public, but the
static site content is protected by a password gate before files are served.
"""

from __future__ import annotations

import functools
import http.cookies
import http.server
import os
import secrets
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8877
COOKIE_NAME = "richo_preview"

LOGIN_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RichO private preview</title>
<style>
body { font-family: system-ui, sans-serif; background: #f6f1e6; color: #211915; display: grid; min-height: 100vh; place-items: center; }
main { width: min(28rem, calc(100vw - 2rem)); border: 1px solid #d8c7aa; background: #fffaf0; padding: 2rem; box-shadow: 8px 8px 0 #e2d4bd; }
input, button { font: inherit; padding: .7rem .8rem; }
input { width: 100%; box-sizing: border-box; border: 1px solid #bfae91; margin: .5rem 0 1rem; }
button { background: #b8431f; color: white; border: 0; cursor: pointer; }
.error { color: #9b1c1c; }
</style>
</head>
<body>
<main>
<h1>RichO private preview</h1>
<p>這是未公開預覽。請輸入密碼。</p>
{error}
<form method="post" action="/__preview_login">
<label>密碼
<input name="password" type="password" autofocus autocomplete="current-password">
</label>
<button type="submit">進入 preview</button>
</form>
</main>
</body>
</html>
"""


class PasswordPreviewHandler(http.server.SimpleHTTPRequestHandler):
    """Serve static files from dist/ behind a password-only cookie gate."""

    preview_password: str = ""
    session_token: str = ""

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path.startswith("/__preview_login"):
            self._serve_login()
            return
        if not self._authorized():
            self._serve_login()
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
        if not self._authorized():
            self.send_response(403)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if not self.path.startswith("/__preview_login"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(min(length, 4096)).decode("utf-8", "replace")
        form = urllib.parse.parse_qs(raw)
        password = form.get("password", [""])[0]
        if secrets.compare_digest(password, self.preview_password):
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}={self.session_token}; Path=/; HttpOnly; SameSite=Lax",
            )
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self._serve_login(error="<p class='error'>密碼不對。</p>")

    def _authorized(self) -> bool:
        header = self.headers.get("Cookie", "")
        if not header:
            return False
        cookies = http.cookies.SimpleCookie()
        try:
            cookies.load(header)
        except http.cookies.CookieError:
            return False
        morsel = cookies.get(COOKIE_NAME)
        return bool(morsel) and secrets.compare_digest(morsel.value, self.session_token)

    def _serve_login(self, error: str = "") -> None:
        body = LOGIN_PAGE.replace("{error}", error).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    password = os.environ.get("PREVIEW_PASSWORD")
    if not password:
        print("Set PREVIEW_PASSWORD before running preview server.")
        return 2
    if len(password) < 12:
        print("PREVIEW_PASSWORD should be at least 12 characters.")
        return 2
    if not DIST_DIR.exists():
        print("dist/ does not exist. Run: python3 scripts/build.py")
        return 2

    host = os.environ.get("PREVIEW_HOST", DEFAULT_HOST)
    port = int(os.environ.get("PREVIEW_PORT", str(DEFAULT_PORT)))
    token = secrets.token_urlsafe(32)

    class PreviewHandler(PasswordPreviewHandler):
        preview_password = password
        session_token = token

    handler = functools.partial(PreviewHandler, directory=str(DIST_DIR))

    with http.server.ThreadingHTTPServer((host, port), handler) as server:
        print(f"Serving password-gated preview at http://{host}:{port}/")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
