from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryEntity:
    entity_type: str
    canonical_name: str
    registry_source: str
    registry_id: str
    included_at: str | None
    aliases: list[str]
