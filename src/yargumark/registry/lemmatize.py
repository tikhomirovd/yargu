from __future__ import annotations

import re

import pymorphy3  # type: ignore[import-untyped]

# Includes Latin and Cyrillic letters plus digits.
TOKEN_RE = re.compile(r"[0-9A-Za-z\u0400-\u04FF]+")
MORPH = pymorphy3.MorphAnalyzer()


def to_lemma_key(value: str) -> str:
    tokens = TOKEN_RE.findall(value.lower())
    lemmas: list[str] = []
    for token in tokens:
        parsed = MORPH.parse(token)
        if not parsed:
            lemmas.append(token)
            continue
        lemmas.append(parsed[0].normal_form)
    return "_".join(sorted(lemmas))
