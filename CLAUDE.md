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
- `fz255` remote JSON URL used in code returned 404; sync falls back to `data/registries/fallback-entities.json` until a stable dump URL is confirmed.
- NLP: `yargumark-process-doc --doc-id N` runs Haiku extraction + matcher + optional PERSON context check; requires `ANTHROPIC_API_KEY`.
- UI: Streamlit entry `src/yargumark/app/main.py` + pages under `src/yargumark/app/pages/`; sidebar `demo|production` maps to confidence thresholds via `ui_threshold`.
- Marker: legal labels in `marker/templates.py`; HTML assembly in `marker/markup.py` with footnotes for `foreign_agent` and `terrorist_extremist`.
- Reindex: `index/reindex.py` rebuilds `mentions` from `extracted_spans` + current registry (no LLM); clears `render_cache`. CLI: `yargumark-reindex`. Streamlit: page **Update Registry Demo**.
- Benchmark: `scripts/benchmark.py` compares `demo/fixtures_expected.json` surfaces vs DB mentions at demo/production thresholds.

## 2026-04-29
- `data/registries/fallback-entities.json` expanded to ~26 demo rows (mixed types + rich aliases). This is a **local teaching snapshot**, not a certified Minjust/export dump — validate wording with counsel before production.
- Priority plan wrap-up: global `inject_global_styles()` on all Streamlit pages; `nlp/prompts.py` few-shot JSON (3 examples via `json.dumps`); `5_Fixtures.py` shows body vs rendered HTML + expected vs demo/production precision/recall surfaces; `demo/generate_fixtures.py` kept ruff-clean (wrapped prompt lines).
