from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, cast

import anthropic

from yargumark.config import get_settings

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _parse_list_payload(text: str) -> list[dict[str, Any]]:
    cleaned = text.strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if match is not None:
        cleaned = match.group(1).strip()
    payload = json.loads(cleaned)
    if not isinstance(payload, list):
        raise ValueError("Model must return a JSON array.")
    rows: list[dict[str, Any]] = []
    for row in cast(list[Any], payload):
        if isinstance(row, dict):
            rows.append(cast(dict[str, Any], row))
    return rows


def _build_prompt(count: int) -> str:
    lines = [
        f"Сгенерируй ровно {count} коротких новостей в стиле сайта российского вуза "
        "(факультет, конференция, интервью).",
        "Требования:",
        "- Половина текстов без упоминаний из реестров иноагентов/нежелательных/"
        "экстремистских (нейтральные).",
        "- Вторая половина: замаскированные или разговорные упоминания "
        "(падежи ФИО, «инста», «телега», «цукер», «фбк», звёздочки, аббревиатуры, "
        "опечатки, латиница).",
        "- Добавь 2-3 текста про тёзкие фамилии без политического контекста "
        "(ложные срабатывания).",
        "Верни СТРОГО JSON-массив объектов: "
        '{"url": "demo://fixture/generated/<slug>", "title": "...", "body": "..."}.',
        "Без комментариев и без текста вне JSON.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate demo fixtures via Claude Haiku.")
    parser.add_argument("--count", type=int, default=18, help="Number of news items to generate.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("demo/fixtures_generated.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("Set ANTHROPIC_API_KEY in .env")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        system=(
            "You write compact Russian university news copy. "
            "Output valid JSON only (array of objects with url, title, body)."
        ),
        messages=[{"role": "user", "content": _build_prompt(args.count)}],
    )
    text_parts: list[str] = []
    for block in getattr(response, "content", []):
        part = getattr(block, "text", None)
        if part:
            text_parts.append(part)
    items = _parse_list_payload("".join(text_parts))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} fixtures to {args.output}")
    print(
        "Next: manual review, merge into demo/fixtures.json, "
        "edit demo/fixtures_expected.json, run scripts/seed_demo.py."
    )


if __name__ == "__main__":
    main()
