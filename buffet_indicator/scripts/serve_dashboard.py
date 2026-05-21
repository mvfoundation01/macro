#!/usr/bin/env python3
"""Serve outputs/dashboard.html on http://127.0.0.1:8765 — avoids file:// CORS restrictions.

Per PROMPT_v11_2_2 §A.4.3. When the dashboard is opened directly via file://,
Chrome treats every hash-change as a different security origin and emits
"Unsafe attempt to load URL" warnings. Serving via HTTP makes file:// a non-issue.
"""
from __future__ import annotations

import http.server
import os
import pathlib
import socketserver
import sys
import webbrowser


PORT = 8765
ROOT = pathlib.Path(__file__).resolve().parent.parent / "outputs"


def main() -> int:
    if not (ROOT / "dashboard.html").exists():
        print(f"ERROR: {ROOT / 'dashboard.html'} not found. Run the build first.")
        return 1

    os.chdir(ROOT)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler) as httpd:
            url = f"http://127.0.0.1:{PORT}/dashboard.html"
            print()
            print(f"  Dashboard:  {url}")
            print(f"  Serving:    {ROOT}")
            print("  Press Ctrl+C to stop")
            print()
            try:
                webbrowser.open(url)
            except Exception:  # noqa: BLE001
                pass
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nStopped.")
    except OSError as exc:
        print(f"ERROR: cannot bind 127.0.0.1:{PORT} — {exc}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
