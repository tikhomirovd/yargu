from __future__ import annotations

import re

WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(value: str) -> str:
    stripped = WHITESPACE_RE.sub(" ", value).strip()
    return stripped
