from __future__ import annotations

import json
from pathlib import Path

import requests  # type: ignore[import-untyped]

from yargumark.registry.models import RegistryEntity
from yargumark.registry.normalize import normalize_name

FZ255_URL = "https://raw.githubusercontent.com/fz255/fz255/main/data/foreign-agents.json"


def load_fz255_foreign_agents() -> list[RegistryEntity]:
    try:
        response = requests.get(FZ255_URL, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []
    entities: list[RegistryEntity] = []
    for row in payload:
        name = normalize_name(str(row.get("name", "")))
        if not name:
            continue
        registry_id = str(row.get("id", name))
        entities.append(
            RegistryEntity(
                entity_type="foreign_agent",
                canonical_name=name,
                registry_source="fz255",
                registry_id=registry_id,
                included_at=str(row.get("date", "")) or None,
                aliases=[name],
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
