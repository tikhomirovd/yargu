from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections.abc import Sequence
from typing import cast

import anthropic

from yargumark.config import Settings, get_settings
from yargumark.db import (
    LlmCacheRow,
    fetch_entities_for_alias_enrichment,
    fetch_entity_aliases,
    get_connection,
    get_llm_cache,
    try_insert_enriched_alias,
    upsert_llm_cache,
)
from yargumark.index.reindex import reindex_mentions_from_extracted_spans
from yargumark.nlp.llm_cache import text_sha256
from yargumark.registry.normalize import normalize_name

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

ALIAS_SYSTEM = "\n".join(
    [
        "Ты эксперт по русскоязычным СМИ. Дано официальное название организации",
        "или персоны из российского реестра. Верни JSON-список всех вариантов,",
        "которыми эта сущность может упоминаться в новостных текстах:",
        "аббревиатуры, склонения, разговорные имена, транслитерации, английские варианты.",
        "Только список строк, без пояснений. Пример: [\"ФБК\", \"Фонду борьбы\", \"навальники\"]",
    ]
)

_ENTITY_TYPE_RU: dict[str, str] = {
    "foreign_agent": "иноагент / иностранный агент",
    "undesirable_org": "нежелательная организация",
    "terrorist_extremist": "террористическая или экстремистская организация",
    "banned_by_court": "организация, запрещённая решением суда",
}


def _alias_kind_for(surface: str) -> str:
    normalized = normalize_name(surface)
    if not normalized:
        return "informal"
    letters_only = "".join(ch for ch in normalized if ch.isalpha())
    if 1 < len(normalized) <= 8 and letters_only.isupper():
        return "abbreviation"
    has_latin = bool(re.search(r"[A-Za-z]", normalized))
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", normalized))
    if has_latin and not has_cyrillic:
        return "transliteration"
    return "informal"


def _extract_usage(response: object) -> tuple[int, int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return (0, 0, 0)
    input_tokens = int(getattr(usage, "input_tokens", 0))
    output_tokens = int(getattr(usage, "output_tokens", 0))
    cached = int(
        getattr(usage, "cache_read_input_tokens", 0)
        or getattr(usage, "cache_creation_input_tokens", 0)
    )
    return (input_tokens, output_tokens, cached)


def _extract_text_blocks(response: object) -> str:
    content = getattr(response, "content", [])
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


def _strings_from_json_list_field(val: object) -> list[str]:
    if not isinstance(val, list):
        return []
    items = cast(list[object], val)
    out: list[str] = []
    for el in items:
        s = str(el).strip()
        if s:
            out.append(s)
    return out


def _parse_alias_json_payload(text: str) -> list[str]:
    cleaned = text.strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match is not None:
        cleaned = match.group(1).strip()
    payload = json.loads(cleaned)
    if not isinstance(payload, list):
        raise ValueError("Model must return a JSON array of strings.")
    out: list[str] = []
    for item in cast(Sequence[object], payload):
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, int | float):
            out.append(str(item))
    return out


def _cache_key_for_alias_enrich(canonical_name: str) -> str:
    return text_sha256(f"alias_enrich:{normalize_name(canonical_name)}")


def enrich_entity_aliases(
    connection: sqlite3.Connection,
    entity_id: int,
    canonical_name: str,
    entity_type: str,
    settings: Settings | None = None,
) -> list[str]:
    """
    Return normalized alias strings suggested by Haiku that are not already stored
    for this entity. Results are cached in llm_cache under key alias_enrich:{name}.
    """
    if entity_id < 1:
        raise ValueError("entity_id must be positive.")
    resolved = settings or get_settings()
    if not resolved.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    existing = {a.lower() for a in fetch_entity_aliases(connection, entity_id)}
    existing.add(normalize_name(canonical_name).lower())

    cache_key = _cache_key_for_alias_enrich(canonical_name)
    cached = get_llm_cache(connection, cache_key)
    usage: tuple[int, int, int]
    raw_list: list[str]
    if cached is not None:
        payload = json.loads(cached.response_json)
        aliases_field = payload.get("aliases", [])
        raw_list = _strings_from_json_list_field(aliases_field)
        usage = (0, 0, 0)
    else:
        type_ru = _ENTITY_TYPE_RU.get(entity_type, entity_type)
        user_msg = (
            f"Официальное название: {canonical_name}\n"
            f"Тип в реестре: {type_ru}\n"
            "Верни только JSON-массив строк (варианты упоминаний в новостях)."
        )
        client = anthropic.Anthropic(api_key=resolved.anthropic_api_key)
        response = client.messages.create(
            model=resolved.anthropic_model,
            max_tokens=2048,
            system=ALIAS_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = _extract_text_blocks(response)
        raw_list = _parse_alias_json_payload(text)
        usage = _extract_usage(response)
        upsert_llm_cache(
            connection,
            LlmCacheRow(
                text_sha256=cache_key,
                response_json=json.dumps({"aliases": raw_list}, ensure_ascii=False),
                model=resolved.anthropic_model,
                input_tokens=usage[0],
                output_tokens=usage[1],
                cached_input_tokens=usage[2],
            ),
        )

    additions: list[str] = []
    seen: set[str] = set(existing)
    for item in raw_list:
        normalized = normalize_name(str(item))
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        additions.append(normalized)
    return additions


def enrich_aliases_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich entity aliases via Haiku and reindex mentions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N entities (for smoke tests).",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    with get_connection(settings.db_path) as connection:
        rows = fetch_entities_for_alias_enrichment(connection)
        if args.limit is not None:
            rows = rows[: args.limit]
        inserted = 0
        for index, (entity_id, canonical_name, entity_type) in enumerate(rows, start=1):
            candidates = enrich_entity_aliases(
                connection,
                entity_id,
                canonical_name,
                entity_type,
                settings=settings,
            )
            n_here = 0
            for alias in candidates:
                kind = _alias_kind_for(alias)
                if try_insert_enriched_alias(connection, entity_id, alias, kind):
                    inserted += 1
                    n_here += 1
            print(f"[{index}/{len(rows)}] entity_id={entity_id} new_aliases={n_here}")
        connection.commit()
    with get_connection(settings.db_path) as connection:
        stats = reindex_mentions_from_extracted_spans(connection, settings)
        connection.commit()
    print(
        "Alias enrichment + reindex done: "
        f"aliases_inserted={inserted}, mentions={stats.mentions_written}, "
        f"docs_touched={stats.documents_touched}"
    )
