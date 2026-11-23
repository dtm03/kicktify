"""Vercel Python serverless: live prediction for the upcoming matchday."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kicktipp.backtest import predict_next_matchday_payload, save_live_prediction  # noqa: E402
from kicktipp.matchday_window import prediction_gate  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            gate = prediction_gate()
            if not gate["allowed"]:
                err = json.dumps({"error": gate["message"], "gate": gate}, ensure_ascii=False).encode("utf-8")
                self.send_response(403)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(err)
                return
            # Poisson + short history fits better in Vercel Hobby (~10s limit)
            backend = "poisson" if os.environ.get("VERCEL") else "xgboost"
            payload = predict_next_matchday_payload(backend=backend)
            if not os.environ.get("VERCEL"):
                LIVE = ROOT / "web" / "public" / "data" / "live_prediction.json"
                LIVE.parent.mkdir(parents=True, exist_ok=True)
                LIVE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(err)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()