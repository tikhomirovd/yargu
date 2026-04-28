from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from yargumark.config import get_settings
from yargumark.registry.lemmatize import to_lemma_key
from yargumark.registry.normalize import normalize_name


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


@dataclass(frozen=True)
class EntityOverviewRow:
    id: int
    canonical_name: str
    entity_type: str
    registry_source: str
    registry_id: str
    alias_count: int
    mention_count: int


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


def get_all_document_ids(connection: sqlite3.Connection, source: str | None = None) -> list[int]:
    cursor = connection.cursor()
    if source is not None:
        cursor.execute(
            "SELECT id FROM documents WHERE source = ? ORDER BY id ASC",
            (source,),
        )
    else:
        cursor.execute("SELECT id FROM documents ORDER BY id ASC")
    return [int(row[0]) for row in cursor.fetchall()]


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
    cursor.execute(
        "DELETE FROM entity_aliases WHERE entity_id = ? AND alias_kind = 'official'",
        (entity_id,),
    )
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


def fetch_entity_aliases(connection: sqlite3.Connection, entity_id: int) -> list[str]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT alias FROM entity_aliases WHERE entity_id = ? ORDER BY alias ASC",
        (entity_id,),
    )
    return [str(row[0]) for row in cursor.fetchall()]


def fetch_entities_for_alias_enrichment(
    connection: sqlite3.Connection,
) -> list[tuple[int, str, str]]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, canonical_name, type
        FROM entities
        WHERE is_active = 1
        ORDER BY id ASC
        """
    )
    return [(int(row[0]), str(row[1]), str(row[2])) for row in cursor.fetchall()]


def try_insert_enriched_alias(
    connection: sqlite3.Connection,
    entity_id: int,
    alias: str,
    alias_kind: str,
) -> bool:
    normalized = normalize_name(alias)
    if not normalized:
        return False
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO entity_aliases (entity_id, alias, alias_kind)
        VALUES (?, ?, ?)
        ON CONFLICT(entity_id, alias) DO NOTHING
        """,
        (entity_id, normalized, alias_kind),
    )
    if cursor.rowcount == 0:
        return False
    lemma_key = to_lemma_key(normalized)
    if lemma_key:
        cursor.execute(
            """
            INSERT INTO entity_lemmas (entity_id, lemma_key)
            VALUES (?, ?)
            ON CONFLICT(entity_id, lemma_key) DO NOTHING
            """,
            (entity_id, lemma_key),
        )
    return True


def ensure_entity_aliases_supports_manual(connection: sqlite3.Connection) -> None:
    """Recreate `entity_aliases` if the table predates the `manual` alias_kind value."""
    cursor = connection.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='entity_aliases'"
    )
    row = cursor.fetchone()
    if row is None or row[0] is None:
        return
    ddl = str(row[0])
    if "manual" in ddl:
        return
    connection.executescript(
        """
        PRAGMA foreign_keys=OFF;
        BEGIN;
        CREATE TABLE entity_aliases_new (
            entity_id INTEGER NOT NULL,
            alias TEXT NOT NULL,
            alias_kind TEXT NOT NULL CHECK(
                alias_kind IN (
                    'official', 'informal', 'transliteration', 'abbreviation', 'manual'
                )
            ),
            PRIMARY KEY (entity_id, alias),
            FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
        );
        INSERT INTO entity_aliases_new SELECT * FROM entity_aliases;
        DROP TABLE entity_aliases;
        ALTER TABLE entity_aliases_new RENAME TO entity_aliases;
        COMMIT;
        PRAGMA foreign_keys=ON;
        """
    )


def rebuild_entity_lemmas(connection: sqlite3.Connection, entity_id: int) -> None:
    cursor = connection.cursor()
    cursor.execute("SELECT canonical_name FROM entities WHERE id = ?", (entity_id,))
    row = cursor.fetchone()
    if row is None:
        return
    canonical = normalize_name(str(row[0]))
    cursor.execute("DELETE FROM entity_lemmas WHERE entity_id = ?", (entity_id,))
    canon_lemma = to_lemma_key(canonical)
    if canon_lemma:
        cursor.execute(
            """
            INSERT INTO entity_lemmas (entity_id, lemma_key)
            VALUES (?, ?)
            ON CONFLICT(entity_id, lemma_key) DO NOTHING
            """,
            (entity_id, canon_lemma),
        )
    cursor.execute(
        "SELECT alias FROM entity_aliases WHERE entity_id = ?",
        (entity_id,),
    )
    for (alias_row,) in cursor.fetchall():
        nk = to_lemma_key(normalize_name(str(alias_row)))
        if nk:
            cursor.execute(
                """
                INSERT INTO entity_lemmas (entity_id, lemma_key)
                VALUES (?, ?)
                ON CONFLICT(entity_id, lemma_key) DO NOTHING
                """,
                (entity_id, nk),
            )


def fetch_entity_aliases_with_kind(
    connection: sqlite3.Connection,
    entity_id: int,
) -> list[tuple[str, str]]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT alias, alias_kind FROM entity_aliases
        WHERE entity_id = ?
        ORDER BY alias_kind ASC, alias ASC
        """,
        (entity_id,),
    )
    return [(str(r[0]), str(r[1])) for r in cursor.fetchall()]


def delete_entity_alias(connection: sqlite3.Connection, entity_id: int, alias: str) -> bool:
    normalized = normalize_name(alias)
    if not normalized:
        return False
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM entity_aliases WHERE entity_id = ? AND alias = ?",
        (entity_id, normalized),
    )
    if cursor.rowcount == 0:
        return False
    rebuild_entity_lemmas(connection, entity_id)
    return True


def count_entities_for_overview(
    connection: sqlite3.Connection,
    *,
    search: str | None,
    entity_type: str | None,
) -> int:
    where_parts = ["e.is_active = 1"]
    params: list[object] = []
    if entity_type:
        where_parts.append("e.type = ?")
        params.append(entity_type)
    if search and search.strip():
        pat = f"%{search.strip()}%"
        where_parts.append(
            "(e.canonical_name LIKE ? OR e.registry_id LIKE ? OR e.registry_source LIKE ?)"
        )
        params.extend([pat, pat, pat])
    where_sql = " AND ".join(where_parts)
    cursor = connection.cursor()
    cursor.execute(
        f"SELECT COUNT(*) FROM entities e WHERE {where_sql}",
        tuple(params),
    )
    row = cursor.fetchone()
    return int(row[0]) if row is not None else 0


def fetch_entity_brief(
    connection: sqlite3.Connection,
    entity_id: int,
) -> tuple[str, str] | None:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT canonical_name, type FROM entities WHERE id = ? AND is_active = 1
        """,
        (entity_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return (str(row[0]), str(row[1]))


def list_entities_overview(
    connection: sqlite3.Connection,
    *,
    min_confidence: float,
    search: str | None,
    entity_type: str | None,
    limit: int,
    offset: int,
) -> list[EntityOverviewRow]:
    where_parts = ["e.is_active = 1"]
    params: list[object] = [min_confidence]
    if entity_type:
        where_parts.append("e.type = ?")
        params.append(entity_type)
    if search and search.strip():
        pat = f"%{search.strip()}%"
        where_parts.append(
            "(e.canonical_name LIKE ? OR e.registry_id LIKE ? OR e.registry_source LIKE ?)"
        )
        params.extend([pat, pat, pat])
    where_sql = " AND ".join(where_parts)
    params.extend([limit, offset])
    cursor = connection.cursor()
    cursor.execute(
        f"""
        SELECT
            e.id,
            e.canonical_name,
            e.type,
            e.registry_source,
            e.registry_id,
            (SELECT COUNT(*) FROM entity_aliases ea WHERE ea.entity_id = e.id) AS alias_count,
            (
                SELECT COUNT(*)
                FROM mentions m
                WHERE m.entity_id = e.id AND m.confidence >= ?
            ) AS mention_count
        FROM entities e
        WHERE {where_sql}
        ORDER BY e.canonical_name COLLATE NOCASE
        LIMIT ? OFFSET ?
        """,
        tuple(params),
    )
    out: list[EntityOverviewRow] = []
    for r in cursor.fetchall():
        out.append(
            EntityOverviewRow(
                id=int(r[0]),
                canonical_name=str(r[1]),
                entity_type=str(r[2]),
                registry_source=str(r[3]),
                registry_id=str(r[4]),
                alias_count=int(r[5]),
                mention_count=int(r[6]),
            )
        )
    return out


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
    short_aliases: list[str]


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
        ORDER BY id ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    result: list[DigestEntityRow] = []
    for r in rows:
        entity_id = int(r[0])
        aliases_cursor = connection.cursor()
        aliases_cursor.execute(
            """
            SELECT alias FROM entity_aliases
            WHERE entity_id = ?
              AND length(alias) <= 40
            ORDER BY length(alias) ASC
            LIMIT 5
            """,
            (entity_id,),
        )
        short_aliases = [str(a[0]) for a in aliases_cursor.fetchall()]
        result.append(
            DigestEntityRow(
                id=entity_id,
                entity_type=str(r[1]),
                canonical_name=str(r[2]),
                registry_source=str(r[3]),
                registry_id=str(r[4]),
                short_aliases=short_aliases,
            )
        )
    return result


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


@dataclass(frozen=True)
class DocumentDetailRow:
    id: int
    title: str
    url: str
    body: str
    source: str
    published_at: str | None


@dataclass(frozen=True)
class DocumentSummaryRow:
    id: int
    title: str
    url: str
    published_at: str | None
    source: str
    mention_count: int


@dataclass(frozen=True)
class MentionMarkupRow:
    start: int
    end: int
    surface: str
    entity_type: str
    canonical_name: str
    confidence: float
    match_method: str
    reasoning: str


@dataclass(frozen=True)
class RenderCacheRow:
    doc_id: int
    mode: str
    html_marked: str
    mentions_hash: str


def fetch_document_detail(connection: sqlite3.Connection, doc_id: int) -> DocumentDetailRow | None:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, title, url, body, source, published_at
        FROM documents
        WHERE id = ?
        """,
        (doc_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return DocumentDetailRow(
        id=int(row[0]),
        title=str(row[1]),
        url=str(row[2]),
        body=str(row[3]),
        source=str(row[4]),
        published_at=str(row[5]) if row[5] is not None else None,
    )


def list_documents_with_mentions(
    connection: sqlite3.Connection,
    min_confidence: float,
    source: str | None = None,
    limit: int = 500,
    *,
    only_with_mentions: bool = False,
) -> list[DocumentSummaryRow]:
    cursor = connection.cursor()
    source_filter = ""
    params: list[object] = [min_confidence]
    if source is not None:
        source_filter = "AND d.source = ?"
        params.append(source)
    having = ""
    if only_with_mentions:
        having = "HAVING COUNT(m.id) > 0"
    order_by = (
        "ORDER BY mention_count DESC, d.fetched_at DESC"
        if only_with_mentions
        else "ORDER BY d.fetched_at DESC"
    )
    params.append(limit)
    cursor.execute(
        f"""
        SELECT d.id, d.title, d.url, d.published_at, d.source,
               COUNT(m.id) AS mention_count
        FROM documents d
        LEFT JOIN mentions m
          ON m.doc_id = d.id AND m.confidence >= ?
        WHERE 1=1 {source_filter}
        GROUP BY d.id
        {having}
        {order_by}
        LIMIT ?
        """,
        tuple(params),
    )
    rows = cursor.fetchall()
    return [
        DocumentSummaryRow(
            id=int(r[0]),
            title=str(r[1]),
            url=str(r[2]),
            published_at=str(r[3]) if r[3] is not None else None,
            source=str(r[4]),
            mention_count=int(r[5]),
        )
        for r in rows
    ]


def fetch_mentions_for_markup(
    connection: sqlite3.Connection,
    doc_id: int,
    min_confidence: float,
) -> list[MentionMarkupRow]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT m.start_offset, m.end_offset, m.surface_form, e.type, e.canonical_name,
               m.confidence, m.match_method, m.reasoning
        FROM mentions m
        JOIN entities e ON e.id = m.entity_id
        WHERE m.doc_id = ? AND m.confidence >= ?
        ORDER BY m.start_offset ASC, m.end_offset DESC
        """,
        (doc_id, min_confidence),
    )
    return [
        MentionMarkupRow(
            start=int(r[0]),
            end=int(r[1]),
            surface=str(r[2]),
            entity_type=str(r[3]),
            canonical_name=str(r[4]),
            confidence=float(r[5]),
            match_method=str(r[6]),
            reasoning=str(r[7]),
        )
        for r in cursor.fetchall()
    ]


def compute_mentions_hash(
    connection: sqlite3.Connection,
    doc_id: int,
    min_confidence: float,
) -> str:
    cursor = connection.cursor()
    cursor.execute("SELECT body FROM documents WHERE id = ?", (doc_id,))
    body_row = cursor.fetchone()
    body_text = str(body_row[0]) if body_row is not None and body_row[0] is not None else ""
    body_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()[:16]
    cursor.execute(
        """
        SELECT id, entity_id, confidence
        FROM mentions
        WHERE doc_id = ? AND confidence >= ?
        ORDER BY id ASC
        """,
        (doc_id, min_confidence),
    )
    mentions_part = "|".join(
        f"{int(r[0])}:{int(r[1])}:{float(r[2]):.6f}" for r in cursor.fetchall()
    )
    # Bump when legal/badge HTML templates change so `render_cache` is not reused.
    markup_v = "2"
    return hashlib.sha256(f"{markup_v}:{body_hash}::{mentions_part}".encode()).hexdigest()


def upsert_render_cache(connection: sqlite3.Connection, row: RenderCacheRow) -> None:
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO render_cache (doc_id, mode, html_marked, mentions_hash, rendered_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(doc_id, mode) DO UPDATE SET
            html_marked = excluded.html_marked,
            mentions_hash = excluded.mentions_hash,
            rendered_at = excluded.rendered_at
        """,
        (row.doc_id, row.mode, row.html_marked, row.mentions_hash, now),
    )


def get_render_cache(
    connection: sqlite3.Connection,
    doc_id: int,
    mode: str,
) -> RenderCacheRow | None:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT doc_id, mode, html_marked, mentions_hash
        FROM render_cache
        WHERE doc_id = ? AND mode = ?
        """,
        (doc_id, mode),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return RenderCacheRow(
        doc_id=int(row[0]),
        mode=str(row[1]),
        html_marked=str(row[2]),
        mentions_hash=str(row[3]),
    )


def count_entities_by_type(connection: sqlite3.Connection) -> dict[str, int]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT type, COUNT(*) FROM entities WHERE is_active = 1 GROUP BY type
        """
    )
    return {str(r[0]): int(r[1]) for r in cursor.fetchall()}


def latest_registry_sync_finished_at(connection: sqlite3.Connection) -> str | None:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT finished_at
        FROM registry_sync_log
        WHERE finished_at IS NOT NULL AND error IS NULL
        ORDER BY finished_at DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])


@dataclass(frozen=True)
class ExtractedSpanRow:
    id: int
    doc_id: int
    start_offset: int
    end_offset: int
    surface_form: str
    normalized: str
    lemma_key: str
    span_type: str
    extractor: str


def fetch_all_extracted_spans(connection: sqlite3.Connection) -> list[ExtractedSpanRow]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, doc_id, start_offset, end_offset, surface_form, normalized,
               lemma_key, span_type, extractor
        FROM extracted_spans
        ORDER BY doc_id ASC, id ASC
        """
    )
    return [
        ExtractedSpanRow(
            id=int(r[0]),
            doc_id=int(r[1]),
            start_offset=int(r[2]),
            end_offset=int(r[3]),
            surface_form=str(r[4]),
            normalized=str(r[5]),
            lemma_key=str(r[6]),
            span_type=str(r[7]),
            extractor=str(r[8]),
        )
        for r in cursor.fetchall()
    ]


def delete_all_mentions(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM mentions")


def clear_render_cache(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM render_cache")


def get_document_id_by_url(connection: sqlite3.Connection, url: str) -> int | None:
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM documents WHERE url = ?", (url,))
    row = cursor.fetchone()
    if row is None:
        return None
    return int(row[0])


def fetch_mention_surfaces(
    connection: sqlite3.Connection,
    doc_id: int,
    min_confidence: float,
) -> list[str]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT surface_form
        FROM mentions
        WHERE doc_id = ? AND confidence >= ?
        ORDER BY start_offset ASC
        """,
        (doc_id, min_confidence),
    )
    return [str(r[0]) for r in cursor.fetchall()]


@dataclass(frozen=True)
class DocumentCounts:
    total: int
    by_source: dict[str, int]


def count_documents_by_source(connection: sqlite3.Connection) -> DocumentCounts:
    cursor = connection.cursor()
    cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
    by_source = {str(r[0]): int(r[1]) for r in cursor.fetchall()}
    total = sum(by_source.values())
    return DocumentCounts(total=total, by_source=by_source)


@dataclass(frozen=True)
class LlmCacheRollup:
    row_count: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int


def _body_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def rollup_llm_cache_for_document_bodies(connection: sqlite3.Connection) -> LlmCacheRollup:
    """llm_cache rows keyed by sha256(document.body); primary NER call per page."""
    cursor = connection.cursor()
    cursor.execute("SELECT body FROM documents")
    hashes = {_body_sha256(str(r[0])) for r in cursor.fetchall() if r[0] is not None}
    if not hashes:
        return LlmCacheRollup(0, 0, 0, 0)
    cursor.execute(
        "SELECT text_sha256, input_tokens, output_tokens, cached_input_tokens FROM llm_cache"
    )
    row_count = 0
    input_tokens = 0
    output_tokens = 0
    cached_input_tokens = 0
    for r in cursor.fetchall():
        if str(r[0]) in hashes:
            row_count += 1
            input_tokens += int(r[1])
            output_tokens += int(r[2])
            cached_input_tokens += int(r[3])
    return LlmCacheRollup(row_count, input_tokens, output_tokens, cached_input_tokens)


def rollup_llm_cache_all(connection: sqlite3.Connection) -> LlmCacheRollup:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0),
               COALESCE(SUM(cached_input_tokens), 0)
        FROM llm_cache
        """
    )
    row = cursor.fetchone()
    if row is None:
        return LlmCacheRollup(0, 0, 0, 0)
    return LlmCacheRollup(
        int(row[0]),
        int(row[1]),
        int(row[2]),
        int(row[3]),
    )


def count_mentions_by_entity_type(
    connection: sqlite3.Connection,
    min_confidence: float,
) -> dict[str, int]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT e.type, COUNT(m.id)
        FROM mentions m
        JOIN entities e ON e.id = m.entity_id
        WHERE m.confidence >= ?
        GROUP BY e.type
        """,
        (min_confidence,),
    )
    return {str(r[0]): int(r[1]) for r in cursor.fetchall()}
