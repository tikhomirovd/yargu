from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from yargumark.config import get_settings


@dataclass(frozen=True)
class DocumentRecord:
    url: str
    title: str
    body: str
    html_raw: str
    published_at: str | None
    source: str


@dataclass(frozen=True)
class EntityRecord:
    entity_type: str
    canonical_name: str
    registry_source: str
    registry_id: str
    included_at: str | None
    aliases: list[str]
    lemma_key: str


def _read_schema(schema_path: Path) -> str:
    return schema_path.read_text(encoding="utf-8")


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    return connection


def init_db() -> None:
    settings = get_settings()
    schema_path = Path(__file__).with_name("schema.sql")
    with get_connection(settings.db_path) as connection:
        connection.executescript(_read_schema(schema_path))
        connection.commit()
    print(f"Initialized database at {settings.db_path}")


def _hash_html(html_raw: str) -> str:
    return hashlib.sha256(html_raw.encode("utf-8")).hexdigest()


def upsert_document(connection: sqlite3.Connection, record: DocumentRecord) -> int:
    now = datetime.now(UTC).isoformat()
    html_hash = _hash_html(record.html_raw)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO documents (
            url, title, body, html_raw, html_hash, published_at, fetched_at, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title = excluded.title,
            body = excluded.body,
            html_raw = excluded.html_raw,
            html_hash = excluded.html_hash,
            published_at = excluded.published_at,
            fetched_at = excluded.fetched_at,
            source = excluded.source
        WHERE documents.html_hash != excluded.html_hash
        """,
        (
            record.url,
            record.title,
            record.body,
            record.html_raw,
            html_hash,
            record.published_at,
            now,
            record.source,
        ),
    )
    if cursor.rowcount == 0:
        cursor.execute("SELECT id FROM documents WHERE url = ?", (record.url,))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Failed to fetch existing document id for URL: {record.url}")
        return int(row[0])
    cursor.execute("SELECT id FROM documents WHERE url = ?", (record.url,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to fetch upserted document id for URL: {record.url}")
    return int(row[0])


def start_registry_sync(connection: sqlite3.Connection, source: str) -> int:
    started_at = datetime.now(UTC).isoformat()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO registry_sync_log (source, started_at)
        VALUES (?, ?)
        """,
        (source, started_at),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("Failed to start registry sync log row.")
    return int(cursor.lastrowid)


def finish_registry_sync(
    connection: sqlite3.Connection,
    sync_id: int,
    entities_added: int,
    entities_updated: int,
    error: str | None,
) -> None:
    finished_at = datetime.now(UTC).isoformat()
    connection.execute(
        """
        UPDATE registry_sync_log
        SET finished_at = ?, entities_added = ?, entities_updated = ?, error = ?
        WHERE id = ?
        """,
        (finished_at, entities_added, entities_updated, error, sync_id),
    )


def upsert_entity(connection: sqlite3.Connection, record: EntityRecord) -> bool:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1 FROM entities WHERE registry_source = ? AND registry_id = ?
        """,
        (record.registry_source, record.registry_id),
    )
    existed = cursor.fetchone() is not None
    cursor.execute(
        """
        INSERT INTO entities (
            type, canonical_name, registry_source, registry_id,
            included_at, metadata_json, is_active
        ) VALUES (?, ?, ?, ?, ?, '{}', 1)
        ON CONFLICT(registry_source, registry_id) DO UPDATE SET
            type = excluded.type,
            canonical_name = excluded.canonical_name,
            included_at = excluded.included_at,
            is_active = 1
        """,
        (
            record.entity_type,
            record.canonical_name,
            record.registry_source,
            record.registry_id,
            record.included_at,
        ),
    )
    cursor.execute(
        """
        SELECT id FROM entities WHERE registry_source = ? AND registry_id = ?
        """,
        (record.registry_source, record.registry_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(
            f"Failed to fetch entity after upsert: {record.registry_source}:{record.registry_id}"
        )
    entity_id = int(row[0])
    cursor.execute("DELETE FROM entity_aliases WHERE entity_id = ?", (entity_id,))
    cursor.executemany(
        """
        INSERT INTO entity_aliases (entity_id, alias, alias_kind)
        VALUES (?, ?, 'official')
        ON CONFLICT(entity_id, alias) DO NOTHING
        """,
        [(entity_id, alias) for alias in sorted(set(record.aliases))],
    )
    cursor.execute("DELETE FROM entity_lemmas WHERE entity_id = ?", (entity_id,))
    cursor.execute(
        """
        INSERT INTO entity_lemmas (entity_id, lemma_key)
        VALUES (?, ?)
        ON CONFLICT(entity_id, lemma_key) DO NOTHING
        """,
        (entity_id, record.lemma_key),
    )
    return not existed


@dataclass(frozen=True)
class DocumentRow:
    id: int
    body: str


@dataclass(frozen=True)
class DigestEntityRow:
    id: int
    entity_type: str
    canonical_name: str
    registry_source: str
    registry_id: str


@dataclass(frozen=True)
class EntityForMatch:
    id: int
    entity_type: str
    canonical_name: str
    registry_source: str
    registry_id: str
    aliases: list[str]
    lemma_keys: set[str]


@dataclass(frozen=True)
class ExtractedSpanRecord:
    doc_id: int
    start_offset: int
    end_offset: int
    surface_form: str
    normalized: str
    lemma_key: str
    span_type: str
    extractor: str


@dataclass(frozen=True)
class MentionRecord:
    doc_id: int
    entity_id: int
    span_id: int
    start_offset: int
    end_offset: int
    surface_form: str
    confidence: float
    match_method: str
    reasoning: str


@dataclass(frozen=True)
class LlmCacheRow:
    text_sha256: str
    response_json: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int


def fetch_document(connection: sqlite3.Connection, doc_id: int) -> DocumentRow | None:
    cursor = connection.cursor()
    cursor.execute("SELECT id, body FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return DocumentRow(id=int(row[0]), body=str(row[1]))


def clear_nlp_for_document(connection: sqlite3.Connection, doc_id: int) -> None:
    connection.execute("DELETE FROM mentions WHERE doc_id = ?", (doc_id,))
    connection.execute("DELETE FROM extracted_spans WHERE doc_id = ?", (doc_id,))


def fetch_digest_entities(connection: sqlite3.Connection, limit: int) -> list[DigestEntityRow]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, type, canonical_name, registry_source, registry_id
        FROM entities
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    return [
        DigestEntityRow(
            id=int(r[0]),
            entity_type=str(r[1]),
            canonical_name=str(r[2]),
            registry_source=str(r[3]),
            registry_id=str(r[4]),
        )
        for r in rows
    ]


def fetch_entities_for_matching(connection: sqlite3.Connection) -> list[EntityForMatch]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, type, canonical_name, registry_source, registry_id
        FROM entities
        WHERE is_active = 1
        """
    )
    entity_rows = cursor.fetchall()
    entities: list[EntityForMatch] = []
    for row in entity_rows:
        entity_id = int(row[0])
        cursor.execute("SELECT alias FROM entity_aliases WHERE entity_id = ?", (entity_id,))
        aliases = [str(alias_row[0]) for alias_row in cursor.fetchall()]
        cursor.execute("SELECT lemma_key FROM entity_lemmas WHERE entity_id = ?", (entity_id,))
        lemma_keys = {str(lemma_row[0]) for lemma_row in cursor.fetchall()}
        entities.append(
            EntityForMatch(
                id=entity_id,
                entity_type=str(row[1]),
                canonical_name=str(row[2]),
                registry_source=str(row[3]),
                registry_id=str(row[4]),
                aliases=aliases,
                lemma_keys=lemma_keys,
            )
        )
    return entities


def insert_extracted_span(connection: sqlite3.Connection, record: ExtractedSpanRecord) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO extracted_spans (
            doc_id, start_offset, end_offset, surface_form, normalized,
            lemma_key, span_type, extractor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.doc_id,
            record.start_offset,
            record.end_offset,
            record.surface_form,
            record.normalized,
            record.lemma_key,
            record.span_type,
            record.extractor,
        ),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("Failed to insert extracted span.")
    return int(cursor.lastrowid)


def insert_mention(connection: sqlite3.Connection, record: MentionRecord) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO mentions (
            doc_id, entity_id, span_id, start_offset, end_offset,
            surface_form, confidence, match_method, reasoning
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.doc_id,
            record.entity_id,
            record.span_id,
            record.start_offset,
            record.end_offset,
            record.surface_form,
            record.confidence,
            record.match_method,
            record.reasoning,
        ),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("Failed to insert mention.")
    return int(cursor.lastrowid)


def get_llm_cache(connection: sqlite3.Connection, text_sha256: str) -> LlmCacheRow | None:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT text_sha256, response_json, model, input_tokens, output_tokens, cached_input_tokens
        FROM llm_cache
        WHERE text_sha256 = ?
        """,
        (text_sha256,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return LlmCacheRow(
        text_sha256=str(row[0]),
        response_json=str(row[1]),
        model=str(row[2]),
        input_tokens=int(row[3]),
        output_tokens=int(row[4]),
        cached_input_tokens=int(row[5]),
    )


def upsert_llm_cache(connection: sqlite3.Connection, row: LlmCacheRow) -> None:
    connection.execute(
        """
        INSERT INTO llm_cache (
            text_sha256, response_json, model, input_tokens, output_tokens, cached_input_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(text_sha256) DO UPDATE SET
            response_json = excluded.response_json,
            model = excluded.model,
            input_tokens = excluded.input_tokens,
            output_tokens = excluded.output_tokens,
            cached_input_tokens = excluded.cached_input_tokens
        """,
        (
            row.text_sha256,
            row.response_json,
            row.model,
            row.input_tokens,
            row.output_tokens,
            row.cached_input_tokens,
        ),
    )
