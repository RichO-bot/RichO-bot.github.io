#!/usr/bin/env python3
"""Password-protected local preview server for RichO Blog.

Build first:

    python3 scripts/build.py

Run locally:

    PREVIEW_USER=panda PREVIEW_PASSWORD='change-me' python3 scripts/preview.py

Then open http://127.0.0.1:8877/.

If this is placed behind a tunnel, the tunnel URL is still public, but the
static site requires HTTP Basic Auth before content is shown.
"""

from __future__ import annotations

import base64
import functools
import http.server
import os
import secrets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8877


class AuthenticatedStaticHandler(http.server.SimpleHTTPRequestHandler):
    """Serve static files from dist/ behind HTTP Basic Auth."""

    preview_user: str = ""
    preview_password: str = ""

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if not self._authorized():
            self._reject()
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
        if not self._authorized():
            self._reject()
            return
        super().do_HEAD()

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Basic "
        if not header.startswith(prefix):
            return False
        try:
            decoded = base64.b64decode(header[len(prefix):], validate=True).decode("utf-8")
        except Exception:
            return False
        user, sep, password = decoded.partition(":")
        if not sep:
            return False
        return secrets.compare_digest(user, self.preview_user) and secrets.compare_digest(
            password, self.preview_password
        )

    def _reject(self) -> None:
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="RichO private preview"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b"Authentication required for RichO private preview.\n")


def main() -> int:
    user = os.environ.get("PREVIEW_USER")
    password = os.environ.get("PREVIEW_PASSWORD")
    if not user or not password:
        print("Set PREVIEW_USER and PREVIEW_PASSWORD before running preview server.")
        return 2
    if not DIST_DIR.exists():
        print("dist/ does not exist. Run: python3 scripts/build.py")
        return 2

    host = os.environ.get("PREVIEW_HOST", DEFAULT_HOST)
    port = int(os.environ.get("PREVIEW_PORT", str(DEFAULT_PORT)))
    class PreviewHandler(AuthenticatedStaticHandler):
        preview_user = user
        preview_password = password

    handler = functools.partial(PreviewHandler, directory=str(DIST_DIR))

    with http.server.ThreadingHTTPServer((host, port), handler) as server:
        print(f"Serving password-protected preview at http://{host}:{port}/")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
