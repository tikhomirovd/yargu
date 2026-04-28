from __future__ import annotations

import argparse
import sys

from yargumark.config import get_settings
from yargumark.crawler.title import extract_article_title, is_blacklisted_title
from yargumark.db import get_connection


def run_backfill(*, only_blacklisted: bool = True, dry_run: bool = False) -> None:
    settings = get_settings()
    updated = 0
    skipped = 0
    with get_connection(settings.db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id, url, title, body, html_raw FROM documents ORDER BY id ASC")
        rows = cursor.fetchall()
        for raw_row in rows:
            doc_id = int(raw_row[0])
            url = str(raw_row[1])
            title = str(raw_row[2] or "")
            body = str(raw_row[3] or "")
            html_raw = str(raw_row[4] or "")
            if only_blacklisted and not is_blacklisted_title(title):
                continue
            new_title = extract_article_title(html_raw, body).strip()
            if not new_title or new_title == title:
                skipped += 1
                continue
            print(f"[{doc_id}] {title!r} -> {new_title!r}  ({url})")
            if not dry_run:
                connection.execute(
                    "UPDATE documents SET title = ? WHERE id = ?",
                    (new_title, doc_id),
                )
            updated += 1
        if not dry_run:
            connection.commit()
    print(f"Updated: {updated}, skipped: {skipped}, dry_run={dry_run}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-extract article titles from documents.html_raw.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every document, not only those with section/empty titles.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed renames without writing to DB.",
    )
    args = parser.parse_args(argv)
    run_backfill(only_blacklisted=not args.all, dry_run=args.dry_run)
    return 0


def cli_entry() -> None:
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli_entry()
