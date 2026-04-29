from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

import requests  # type: ignore[import-untyped]
import urllib3

from yargumark.registry.models import RegistryEntity
from yargumark.registry.normalize import normalize_name, normalize_registry_full_name

FOREIGN_AGENTS_URL = (
    "https://raw.githubusercontent.com/fz255/foreign-agents/main/registry.json"
)
UNDESIRABLE_ORGS_URL = (
    "https://raw.githubusercontent.com/fz255/undesirable-organizations/main/registry.json"
)
FEDSFM_TERROR_ALL_URL = "https://www.fedsfm.ru/documents/terrorists-catalog-portal-act"
FEDSFM_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.fedsfm.ru/",
}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _fetch_registry_json(url: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    out: list[dict[str, Any]] = []
    for item in cast(list[object], payload):
        if isinstance(item, dict):
            out.append(cast(dict[str, Any], item))
    return out


def _is_active_row(row: dict[str, Any]) -> bool:
    raw = row.get("dateOut")
    if raw is None:
        return True
    return str(raw).strip() == ""


def load_fz255_foreign_agents() -> list[RegistryEntity]:
    payload = _fetch_registry_json(FOREIGN_AGENTS_URL)
    entities: list[RegistryEntity] = []
    for row in payload:
        if not _is_active_row(row):
            continue
        full = normalize_registry_full_name(str(row.get("fullName", "")))
        if not full:
            continue
        raw_id = str(row.get("id", "")).strip() or full
        registry_id = f"agents/{raw_id}"
        date_in = str(row.get("dateIn", "")).strip() or None
        entities.append(
            RegistryEntity(
                entity_type="foreign_agent",
                canonical_name=full,
                registry_source="fz255",
                registry_id=registry_id,
                included_at=date_in,
                aliases=[full],
            )
        )
    return entities


def load_fz255_undesirable_orgs() -> list[RegistryEntity]:
    payload = _fetch_registry_json(UNDESIRABLE_ORGS_URL)
    entities: list[RegistryEntity] = []
    for row in payload:
        if not _is_active_row(row):
            continue
        full = normalize_registry_full_name(str(row.get("fullName", "")))
        if not full:
            continue
        raw_id = str(row.get("id", "")).strip() or full
        registry_id = f"undesirable/{raw_id}"
        date_in = str(row.get("dateIn", "")).strip() or None
        entities.append(
            RegistryEntity(
                entity_type="undesirable_org",
                canonical_name=full,
                registry_source="fz255",
                registry_id=registry_id,
                included_at=date_in,
                aliases=[full],
            )
        )
    return entities


def _extract_parenthesized_aliases(value: str) -> tuple[str, list[str]]:
    aliases: list[str] = []
    cleaned = value
    for part in re.findall(r"\(([^()]*)\)", value):
        variants = [normalize_registry_full_name(p) for p in part.split(";")]
        aliases.extend([v for v in variants if v])
    cleaned = re.sub(r"\([^()]*\)", "", cleaned)
    cleaned = normalize_registry_full_name(cleaned)
    return cleaned, aliases


def _parse_fedsfm_org_line(raw_line: str) -> tuple[str, list[str]] | None:
    line = normalize_registry_full_name(raw_line)
    if not line:
        return None
    line = re.sub(r"^\d+\.\s*", "", line)
    line = line.strip(" ;,")
    line = line.replace("*", "")
    line = normalize_registry_full_name(line)
    if not line:
        return None
    canonical, aliases = _extract_parenthesized_aliases(line)
    if not canonical:
        return None
    dedup_aliases: list[str] = []
    seen: set[str] = set()
    for alias in [canonical, *aliases]:
        if alias and alias not in seen:
            dedup_aliases.append(alias)
            seen.add(alias)
    return canonical, dedup_aliases


def load_fedsfm_terrorist_extremist_orgs() -> list[RegistryEntity]:
    try:
        response = requests.get(
            FEDSFM_TERROR_ALL_URL,
            timeout=60,
            headers=FEDSFM_HEADERS,
            verify=False,
        )
        response.raise_for_status()
        html = response.text
    except requests.RequestException:
        return []

    text = re.sub(r"<[^>]+>", "\n", html)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    text = text.replace("\r", "\n")
    lines = [normalize_registry_full_name(line) for line in text.split("\n")]
    lines = [line for line in lines if line]

    raw_entries: list[tuple[int, str]] = []
    in_org_block = False
    current_idx: int | None = None
    current_text = ""
    for line in lines:
        if line == "Организации":
            if current_idx is not None and current_text:
                raw_entries.append((current_idx, current_text))
                current_idx = None
                current_text = ""
            in_org_block = True
            continue
        if line == "Физические лица":
            if current_idx is not None and current_text:
                raw_entries.append((current_idx, current_text))
                current_idx = None
                current_text = ""
            in_org_block = False
            continue
        if not in_org_block:
            continue
        entry_match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if entry_match is not None:
            if current_idx is not None and current_text:
                raw_entries.append((current_idx, current_text))
            current_idx = int(entry_match.group(1))
            current_text = entry_match.group(2)
            continue
        if current_idx is None:
            continue

        # Some long rows are split across several text lines after tag stripping.
        current_text = normalize_registry_full_name(f"{current_text} {line}")

    if current_idx is not None and current_text:
        raw_entries.append((current_idx, current_text))

    entities: list[RegistryEntity] = []
    for idx, raw_line in raw_entries:
        parsed = _parse_fedsfm_org_line(raw_line)
        if parsed is None:
            continue
        canonical_name, aliases = parsed
        registry_id = f"org/{idx}"
        entities.append(
            RegistryEntity(
                entity_type="terrorist_extremist",
                canonical_name=canonical_name,
                registry_source="fedsfm",
                registry_id=registry_id,
                included_at=None,
                aliases=aliases,
            )
        )
    return entities


def load_local_registry_snapshots(base_path: Path) -> list[RegistryEntity]:
    snapshot_path = base_path / "fallback-entities.json"
    if not snapshot_path.exists():
        return []
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    entities: list[RegistryEntity] = []
    for row in payload:
        canonical_name = normalize_name(str(row.get("canonical_name", "")))
        if not canonical_name:
            continue
        aliases_raw = row.get("aliases", [])
        aliases = [normalize_name(str(alias)) for alias in aliases_raw if str(alias).strip()]
        entities.append(
            RegistryEntity(
                entity_type=str(row["entity_type"]),
                canonical_name=canonical_name,
                registry_source=str(row.get("registry_source", "local_snapshot")),
                registry_id=str(row.get("registry_id", canonical_name)),
                included_at=row.get("included_at"),
                aliases=aliases or [canonical_name],
            )
        )
    return entities
