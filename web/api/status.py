"""Read-only: may the user predict the next matchday? (no model training)."""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kicktipp.matchday_window import prediction_gate  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            body = json.dumps(prediction_gate(strict_monday=False), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err = json.dumps({"error": str(e), "allowed": False}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(err)