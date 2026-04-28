# YarguMark Working Notes

## Purpose
This file stores session-to-session operational memory to avoid repeating solved problems.

## Mandatory Update Rule
At the end of each work session, append concise notes for:
- fuzzy threshold outcomes (good/bad values and examples);
- registry parser quirks (fz255, minjust HTML, fedsfm format details);
- lemmatization edge cases (non-Russian names, initials, mixed scripts);
- observed Haiku latency/cost/cache trends;
- crawler selector changes on source pages;
- legal label wording updates, if any;
- high-impact false positives and their reasoning patterns.

## Current Decisions
- Primary delivery track: Plan A (Demo-first).
- Fallback delivery track: Plan B on recall-gate failure.
- Dual-threshold policy: strict demo mode, recall-first production mode.

## 2026-04-28
- Git repository initialized on branch `main`; initial commit includes crawler, registry sync, and NLP pipeline skeleton.
- `fz255` registry JSON: `foreign-agents` and `undesirable-organizations` repos on GitHub (raw `registry.json`); inactive rows filtered via empty `dateOut`. Numeric ids namespaced as `registry_id` `agents/{id}` and `undesirable/{id}` under `registry_source=fz255` to avoid collisions. Live row counts drift over time (not guaranteed 866+188).
- NLP: `yargumark-process-doc --doc-id N` runs Haiku extraction + matcher + optional PERSON context check; requires `ANTHROPIC_API_KEY`.
- UI: Streamlit entry `src/yargumark/app/main.py` + pages under `src/yargumark/app/pages/`; sidebar `demo|production` maps to confidence thresholds via `ui_threshold`.
- Marker: legal labels in `marker/templates.py`; HTML assembly in `marker/markup.py` with footnotes for `foreign_agent` and `terrorist_extremist`.
- Reindex: `index/reindex.py` rebuilds `mentions` from `extracted_spans` + current registry (no LLM); clears `render_cache`. CLI: `yargumark-reindex`. Streamlit: page **Update Registry Demo**.
- Benchmark: `scripts/benchmark.py` compares `demo/fixtures_expected.json` surfaces vs DB mentions at demo/production thresholds.

## 2026-04-29
- `data/registries/fallback-entities.json` expanded to ~26 demo rows (mixed types + rich aliases). This is a **local teaching snapshot**, not a certified Minjust/export dump — validate wording with counsel before production.
- Priority plan wrap-up: global `inject_global_styles()` on all Streamlit pages; `nlp/prompts.py` few-shot JSON (3 examples via `json.dumps`); `5_Fixtures.py` shows body vs rendered HTML + expected vs demo/production precision/recall surfaces; `demo/generate_fixtures.py` kept ruff-clean (wrapped prompt lines).
- Crawler: `trafilatura` for article body; `www.uniyar.ac.ru` + http start URLs; title from `og:title` / second `h1`; `DOWNLOAD_DELAY=0` for local runs (revisit before production crawl).
- NLP digest: `fetch_digest_entities` returns up to 5 short aliases per entity for the Haiku system prompt; digest order `id ASC`. CLI `--all --limit N` for batch caps.
- Extractor: `_align_span_to_body` falls back to full-text search when windowed match fails.
- Local DB snapshot (not in git): ~13k `uniyar` docs, 19 `demo`; entities ~843 fz255 rows + type counts; NLP runs concentrated on `documents.id` 20–29 (10 uniyar pages, injected/forbidden coverage); `mentions` total 10 in that snapshot.
- Streamlit **Document**: dropdown defaults to documents that already have `mentions` above the sidebar threshold; checkbox expands to the full catalog (same SQL flag as News Library «только помеченные»).
- Crawler: `extract_article_title` убирает шапочный h1 с полным именем ЯрГУ; порядок og → контентные заголовки → `<title>`; `upsert_document` обновляет при конфликте URL без смены `html_hash`. Паук: `LinkExtractor`, запись через **Item → `YarguDocumentPipeline`** (как yagu); Scrapy-настройки как в yagu-scraper: delay+jitter, **concurrent 4**, AutoThrottle, `Accept-Language`, reactor asyncio; старт по умолчанию только **главная** — весь сайт добирается обходом; опционально `--start-url URL` (повторяемо); `--fast-local` — без задержек для дев; CLI: `--max-depth`, `--link-limit`, `--only-new`.
- Scrapy 2.15: `YarguDocumentPipeline` — `from_crawler` + хуки без аргумента `spider` (иначе asyncio-ветка ItemPipeline зовёт `open_spider()` без аргументов и возможен TypeError, если параметр не называется `spider`). Старт паука через `start_urls` в `__init__`, без переопределения `start_requests`.
