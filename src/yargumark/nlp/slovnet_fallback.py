from __future__ import annotations

# Optional Slovnet-based prefilter/fallback (not wired in MVP yet).


def extract_spans_slovnet_stub(document_body: str) -> list[tuple[int, int, str]]:
    _ = document_body
    return []
