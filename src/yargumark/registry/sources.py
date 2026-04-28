from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import requests  # type: ignore[import-untyped]

from yargumark.registry.models import RegistryEntity
from yargumark.registry.normalize import normalize_name, normalize_registry_full_name

FOREIGN_AGENTS_URL = (
    "https://raw.githubusercontent.com/fz255/foreign-agents/main/registry.json"
)
UNDESIRABLE_ORGS_URL = (
    "https://raw.githubusercontent.com/fz255/undesirable-organizations/main/registry.json"
)


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
