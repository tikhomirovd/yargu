from __future__ import annotations

import json

from yargumark.db import DigestEntityRow

_FEW_SHOT_EXAMPLES: list[tuple[str, dict[str, object]]] = [
    (
        "Читали Медузе и Инста.",
        {
            "spans": [
                {
                    "start": 7,
                    "end": 13,
                    "surface": "Медузе",
                    "type": "MEDIA",
                    "normalized": "Meduza",
                    "registry_candidate": "42",
                    "confidence": 0.95,
                    "reasoning": "Oblique case of media brand from digest id=42.",
                },
                {
                    "start": 16,
                    "end": 21,
                    "surface": "Инста",
                    "type": "MEDIA",
                    "normalized": "Instagram",
                    "registry_candidate": None,
                    "confidence": 0.9,
                    "reasoning": "Colloquial alias maps to Instagram / Meta family.",
                },
            ]
        },
    ),
    (
        "Юрист сослался на материалы ФБК про закупки.",
        {
            "spans": [
                {
                    "start": 28,
                    "end": 31,
                    "surface": "ФБК",
                    "type": "ORG",
                    "normalized": "Фонд борьбы против коррупции",
                    "registry_candidate": "local_snapshot:fbk",
                    "confidence": 0.92,
                    "reasoning": "Abbreviation for the foundation listed in registry.",
                },
            ]
        },
    ),
    (
        "Текст упоминает имя Мет* и фамилию Навальному.",
        {
            "spans": [
                {
                    "start": 20,
                    "end": 24,
                    "surface": "Мет*",
                    "type": "ORG",
                    "normalized": "Meta",
                    "registry_candidate": None,
                    "confidence": 0.88,
                    "reasoning": "Masked brand name; star censorship.",
                },
                {
                    "start": 35,
                    "end": 45,
                    "surface": "Навальному",
                    "type": "PER",
                    "normalized": "Алексей Навальный",
                    "registry_candidate": None,
                    "confidence": 0.9,
                    "reasoning": "Dative case of listed person; registry id unknown in digest.",
                },
            ]
        },
    ),
]


def _few_shot_block() -> str:
    intro = (
        "Concrete JSON examples (user message is the first line; "
        "your reply is only the JSON object):"
    )
    chunks: list[str] = [intro, ""]
    for user_text, payload in _FEW_SHOT_EXAMPLES:
        chunks.extend(
            [
                "User text:",
                user_text,
                "",
                "Model output:",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                "",
            ]
        )
    return "\n".join(chunks).rstrip()


def build_system_prompt(digest: list[DigestEntityRow]) -> str:
    lines = [
        "You extract mentions of registry-listed persons and organizations in Russian news text.",
        "Return strict JSON only: "
        '{"spans":[{"start":int,"end":int,"surface":str,"type":"PER|ORG|MEDIA",'
        '"normalized":str,"registry_candidate":str|null,"confidence":float,"reasoning":str}]}',
        "Offsets are UTF-8 character indices into the user message text (0-based, end exclusive).",
        "registry_candidate: internal entity id as decimal string, "
        "or 'registry_source:registry_id', or null if unknown.",
        "Prefer marking with lower confidence over missing a true registry mention.",
        "Consider declensions, typos, masking (stars, dots), and colloquial aliases "
        "(инста→Instagram, телега→Telegram, фб→Facebook, цукер→Zuckerberg, мета→Meta).",
        "",
        "Few-shot JSON examples (illustrative offsets — always recompute for the real user text):",
        _few_shot_block(),
        "",
        "Registry digest (top entries, not exhaustive — full match is validated later):",
    ]
    for row in digest:
        aliases_part = (
            f" aliases=[{', '.join(row.short_aliases)}]" if row.short_aliases else ""
        )
        lines.append(
            f"- id={row.id} type={row.entity_type} name={row.canonical_name}"
            f"{aliases_part} source={row.registry_source}:{row.registry_id}"
        )
    lines.append("")
    return "\n".join(lines)


def build_user_prompt(document_body: str) -> str:
    return document_body
