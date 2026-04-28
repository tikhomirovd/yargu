from __future__ import annotations

import json
from pathlib import Path

from yargumark.config import get_settings
from yargumark.db import DocumentRecord, get_connection, upsert_document


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    fixtures_path = root / "demo" / "fixtures.json"
    payload = json.loads(fixtures_path.read_text(encoding="utf-8"))
    settings = get_settings()
    with get_connection(settings.db_path) as conn:
        for row in payload:
            url = str(row["url"])
            title = str(row["title"])
            body = str(row["body"])
            upsert_document(
                conn,
                DocumentRecord(
                    url=url,
                    title=title,
                    body=body,
                    html_raw=f"<article><p>{body}</p></article>",
                    published_at=None,
                    source="demo",
                ),
            )
        conn.commit()
    print(f"Seeded {len(payload)} demo documents from {fixtures_path}")


if __name__ == "__main__":
    main()
