from __future__ import annotations

import re

WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(value: str) -> str:
    stripped = WHITESPACE_RE.sub(" ", value).strip()
    return stripped


def normalize_registry_full_name(raw: str) -> str:
    """Strip guillemets / straight quotes often wrapping official registry titles."""
    cleaned = raw.replace("«", "").replace("»", "").replace('"', "").replace("\u201c", "").replace(
        "\u201d", ""
    )
    return normalize_name(cleaned)
