from __future__ import annotations

from pathlib import Path

from yargumark.config import get_settings
from yargumark.db import (
    EntityRecord,
    finish_registry_sync,
    get_connection,
    start_registry_sync,
    upsert_entity,
)
from yargumark.registry.lemmatize import to_lemma_key
from yargumark.registry.normalize import normalize_name
from yargumark.registry.sources import (
    load_fz255_foreign_agents,
    load_local_registry_snapshots,
)


def sync_registry() -> None:
    settings = get_settings()
    with get_connection(settings.db_path) as connection:
        sync_id = start_registry_sync(connection, "registry_sync")
        entities_added = 0
        entities_updated = 0
        try:
            entities = load_fz255_foreign_agents()
            entities.extend(load_local_registry_snapshots(Path("data/registries")))
            for entity in entities:
                aliases = [
                    normalize_name(alias) for alias in entity.aliases if normalize_name(alias)
                ]
                canonical_name = normalize_name(entity.canonical_name)
                if not canonical_name:
                    continue
                if canonical_name not in aliases:
                    aliases.append(canonical_name)
                created = upsert_entity(
                    connection,
                    EntityRecord(
                        entity_type=entity.entity_type,
                        canonical_name=canonical_name,
                        registry_source=entity.registry_source,
                        registry_id=entity.registry_id,
                        included_at=entity.included_at,
                        aliases=aliases,
                        lemma_key=to_lemma_key(canonical_name),
                    ),
                )
                if created:
                    entities_added += 1
                else:
                    entities_updated += 1
            finish_registry_sync(connection, sync_id, entities_added, entities_updated, error=None)
            connection.commit()
        except Exception as exc:
            finish_registry_sync(
                connection,
                sync_id,
                entities_added,
                entities_updated,
                error=str(exc),
            )
            connection.commit()
            raise
    print(
        "Registry sync done: "
        f"added={entities_added}, updated={entities_updated}, db={settings.db_path}"
    )
