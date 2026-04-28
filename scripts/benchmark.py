from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from yargumark.benchmark.fixtures_metrics import precision_recall_surfaces
from yargumark.config import get_settings, ui_threshold
from yargumark.db import fetch_mention_surfaces, get_connection, get_document_id_by_url


def _load_expected(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("fixtures_expected.json must be a list.")
    rows: list[dict[str, Any]] = []
    for item in cast(Sequence[object], payload):
        if isinstance(item, dict):
            rows.append(cast(dict[str, Any], item))
    return rows


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    expected_path = root / "demo" / "fixtures_expected.json"
    rows = _load_expected(expected_path)
    settings = get_settings()
    demo_threshold = ui_threshold(settings, "demo")
    production_threshold = ui_threshold(settings, "production")
    report: list[dict[str, Any]] = []
    with get_connection(settings.db_path) as conn:
        for row in rows:
            url = str(row["url"])
            expected_raw = row.get("expected_mention_surfaces", [])
            if not isinstance(expected_raw, list):
                continue
            expected = [str(item) for item in cast(Sequence[object], expected_raw)]
            doc_id = get_document_id_by_url(conn, url)
            if doc_id is None:
                report.append({"url": url, "error": "document_missing"})
                continue
            demo_actual = fetch_mention_surfaces(conn, doc_id, demo_threshold)
            prod_actual = fetch_mention_surfaces(conn, doc_id, production_threshold)
            demo_pr = precision_recall_surfaces(expected, demo_actual)
            prod_pr = precision_recall_surfaces(expected, prod_actual)
            report.append(
                {
                    "url": url,
                    "doc_id": doc_id,
                    "demo": {
                        "precision": round(demo_pr.precision, 4),
                        "recall": round(demo_pr.recall, 4),
                        "tp": demo_pr.true_positive,
                        "fp": demo_pr.false_positive,
                        "fn": demo_pr.false_negative,
                    },
                    "production": {
                        "precision": round(prod_pr.precision, 4),
                        "recall": round(prod_pr.recall, 4),
                        "tp": prod_pr.true_positive,
                        "fp": prod_pr.false_positive,
                        "fn": prod_pr.false_negative,
                    },
                }
            )
    print(json.dumps({"fixtures": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
