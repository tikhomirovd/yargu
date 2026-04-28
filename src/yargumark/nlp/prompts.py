from __future__ import annotations

from yargumark.db import DigestEntityRow


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
        "Registry digest (top entries, not exhaustive — full match is validated later):",
    ]
    for row in digest:
        lines.append(
            f"- id={row.id} type={row.entity_type} name={row.canonical_name} "
            f"source={row.registry_source}:{row.registry_id}"
        )
    lines.append("")
    lines.append("Few-shot style: masked org names, PER in oblique case, informal ORG aliases.")
    return "\n".join(lines)


def build_user_prompt(document_body: str) -> str:
    return document_body
