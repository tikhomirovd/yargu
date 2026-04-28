PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    html_raw TEXT NOT NULL,
    html_hash TEXT NOT NULL,
    published_at TEXT,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL CHECK(source IN ('uniyar', 'demo'))
);

CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_html_hash ON documents(html_hash);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('foreign_agent', 'undesirable_org', 'terrorist_extremist', 'banned_by_court')),
    canonical_name TEXT NOT NULL,
    registry_source TEXT NOT NULL,
    registry_id TEXT NOT NULL,
    included_at TEXT,
    marker_template_id INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_unique_source
    ON entities(registry_source, registry_id);

CREATE TABLE IF NOT EXISTS entity_aliases (
    entity_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    alias_kind TEXT NOT NULL CHECK(alias_kind IN ('official', 'informal', 'transliteration', 'abbreviation')),
    PRIMARY KEY (entity_id, alias),
    FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entity_lemmas (
    entity_id INTEGER NOT NULL,
    lemma_key TEXT NOT NULL,
    PRIMARY KEY (entity_id, lemma_key),
    FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS extracted_spans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    surface_form TEXT NOT NULL,
    normalized TEXT NOT NULL,
    lemma_key TEXT NOT NULL,
    span_type TEXT NOT NULL CHECK(span_type IN ('PER', 'ORG', 'MEDIA')),
    extractor TEXT NOT NULL CHECK(extractor IN ('haiku', 'slovnet', 'context_check')),
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_extracted_spans_doc ON extracted_spans(doc_id);
CREATE INDEX IF NOT EXISTS idx_extracted_spans_lemma_key ON extracted_spans(lemma_key);

CREATE TABLE IF NOT EXISTS mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    span_id INTEGER NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    surface_form TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    match_method TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY(span_id) REFERENCES extracted_spans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS llm_cache (
    text_sha256 TEXT PRIMARY KEY,
    response_json TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    entities_added INTEGER NOT NULL DEFAULT 0,
    entities_updated INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS render_cache (
    doc_id INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('demo', 'production')),
    html_marked TEXT NOT NULL,
    mentions_hash TEXT NOT NULL,
    rendered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id, mode),
    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
);
