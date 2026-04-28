# Iteration Checklists (Plan A)

## Day 1 - Foundation and Crawl

### Inputs
- Agreed MVP scope and legal label categories.
- Access to local machine environment and target website routes.

### Checklist
- Define project skeleton and package layout.
- Lock SQLite schema and migration bootstrap.
- Enable WAL mode and idempotent ingest strategy by `html_hash`.
- Configure Scrapy spider for `news`, `events`, `pressroom`.
- Run controlled crawl sample and verify parser stability.
- Run overnight crawl target up to 500 pages.

### Outputs
- Populated `documents` table with reproducible crawl data.
- Stable selectors and crawl constraints documented.

### Risks and Mitigations
- Selector drift on source pages -> store fallback selectors and parser tests.
- Long crawl runtime -> staged crawl with checkpoint logging.

---

## Day 2 - Registry Sync and Normalization

### Inputs
- Crawler outputs from Day 1.
- Registry source access (fz255 + fallbacks).

### Checklist
- Implement source adapters for four registry categories.
- Normalize names, metadata, and status fields.
- Generate aliases and lemma keys.
- Populate `entities`, `entity_aliases`, `entity_lemmas`.
- Build top-200 registry digest for LLM prompt context.
- Log sync results with counts and failures.

### Outputs
- 1500+ active entities loaded.
- Queryable canonical and alias search path.
- Registry sync log for auditability.

### Risks and Mitigations
- Source format changes -> adapter-specific parser guards.
- Incomplete alias coverage -> backfill aliases from manual review.

---

## Day 3 - Extraction, Matching, Context Check, Cache

### Inputs
- Registry entities with aliases and lemmas.
- Document corpus subset for calibration (first 50 docs).

### Checklist
- Implement Haiku extraction prompt and structured response parsing.
- Persist extraction spans for all candidates (matched and unmatched).
- Add deterministic matcher cascade: lemma -> alias -> fuzzy.
- Add context-check step for PERSON gray zone.
- Add llm cache by `sha256(text)` and prompt cache usage.
- Collect baseline quality, latency, and cost.

### Outputs
- Stable `mentions` with method and reasoning.
- Baseline quality/cost report on sample batch.

### Risks and Mitigations
- Hallucinated registry candidates -> enforce matcher confirmation policy.
- Token or cost spikes -> tighten prompt digest and chunking.

---

## Day 4 - Marker, Fixtures, Streamlit MVP

### Inputs
- Working mention pipeline and cached sample runs.
- Approved legal text variants by entity type.

### Checklist
- Implement legal templates and HTML marker insertion flow.
- Generate 15-20 synthetic fixtures, then manually validate truth labels.
- Seed fixtures into demo dataset.
- Build Streamlit pages: library, document view, registry, sandbox, fixtures.
- Add mode switch (Demo/Production) and mention explanation panel.

### Outputs
- End-to-end demo flow on local machine.
- Fixtures with expected ground truth for tests.

### Risks and Mitigations
- False-positive-heavy demo output -> raise demo threshold and filter UI view.
- Markup offset issues -> render from plain text with strict span ordering.

---

## Day 5 - Incremental Reindex, Benchmark, Rehearsal

### Inputs
- Full pipeline from Day 4.
- Stable fixture-based validation set.

### Checklist
- Implement no-LLM incremental reindex from stored spans.
- Invalidate and rebuild render cache only for impacted docs/modes.
- Add benchmark script for precision/recall/timing/cost.
- Run full validation over 500 + fixtures.
- Rehearse 10-minute demo and record backup video.

### Outputs
- Measured reindex wow scenario with `$0` LLM spend.
- Shareable benchmark results for customer slide.

### Risks and Mitigations
- Reindex touching too many rows -> index optimization and change filters.
- Demo instability -> fixed script path plus warm cache before call.
