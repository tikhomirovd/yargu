from __future__ import annotations

import argparse

from yargumark.nlp.pipeline import process_document


def process_document_cli() -> None:
    parser = argparse.ArgumentParser(description="Process a document with the NLP pipeline.")
    parser.add_argument("--doc-id", type=int, required=True, help="Document id in SQLite.")
    args = parser.parse_args()
    process_document(args.doc_id)
    print(f"Processed document {args.doc_id}")
