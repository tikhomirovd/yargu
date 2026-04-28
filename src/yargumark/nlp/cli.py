from __future__ import annotations

import argparse

from yargumark.config import get_settings
from yargumark.db import get_all_document_ids, get_connection
from yargumark.nlp.pipeline import process_document


def process_document_cli() -> None:
    parser = argparse.ArgumentParser(description="Process document(s) with the NLP pipeline.")
    parser.add_argument("--doc-id", type=int, default=None, help="Single document id in SQLite.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every document in the database (optionally filtered by --source).",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="When used with --all, only documents where documents.source matches (e.g. uniyar).",
    )
    args = parser.parse_args()
    if args.all and args.doc_id is not None:
        parser.error("Use either --doc-id or --all, not both.")
    if not args.all and args.doc_id is None:
        parser.error("Specify --doc-id N or --all.")
    single_doc_id = args.doc_id
    settings = get_settings()
    with get_connection(settings.db_path) as connection:
        if args.all:
            doc_ids = get_all_document_ids(connection, args.source)
        else:
            if single_doc_id is None:
                raise RuntimeError("Expected --doc-id after validation.")
            doc_ids = [single_doc_id]
    total = len(doc_ids)
    for index, doc_id in enumerate(doc_ids, start=1):
        process_document(doc_id)
        print(f"Processed document {doc_id} ({index}/{total})")
    if total == 0:
        print("No documents matched the criteria.")
