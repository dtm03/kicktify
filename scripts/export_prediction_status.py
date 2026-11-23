#!/usr/bin/env python
"""Write web/public/data/prediction_gate.json for static hosting (no /api needed)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kicktipp.matchday_window import prediction_gate  # noqa: E402


def main() -> None:
    out = ROOT / "web" / "public" / "data" / "prediction_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = prediction_gate(strict_monday=False)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"allowed={data['allowed']}: {data['message']}")


if __name__ == "__main__":
    main()