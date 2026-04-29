# YarguMark MVP

YarguMark is a local MVP for automatic legal marking of mentions from Russian registries:
- foreign agents;
- undesirable organizations;
- terrorist and extremist organizations;
- organizations banned by court decision.

This repository now includes Day 1 MVP foundation:
- Python project configuration (`uv`, strict typing, linting);
- SQLite schema and DB bootstrap;
- Scrapy-based crawler skeleton for `uniyar.ac.ru`.

## Execution Track

The active implementation track is **Plan A (Demo-first, 5 working days)**.

Why this track:
- fastest path to a convincing customer demo;
- still preserves production-oriented architecture;
- keeps Plan B (Production-first) as fallback if recall quality drops.

## Demo KPI Baseline

Target metrics for MVP demonstration:
- Demo mode precision: `>= 0.95`
- Demo mode recall: `>= 0.85`
- Production mode precision: `>= 0.80`
- Production mode recall: `>= 0.95`
- Incremental reindex (1 entity, 500 docs): `< 1s`
- Haiku cost for 500 docs: `< $2` (demo), `< $3` (production) — order-of-magnitude; see [NLP cost (Haiku)](#nlp-cost-haiku) below

## Operational Documents

- Track confirmation and KPI lock: `docs/plan-track.md`
- Day-by-day checklists: `docs/iteration-checklists.md`
- 10-minute demo script: `docs/demo-script-10min.md`
- Daily go/no-go gates: `docs/go-no-go.md`
- Session memory and calibration notes: `CLAUDE.md`

## Requirements

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) for installs and `uv run …`
- **Anthropic API key** for NLP (`yargumark-process-doc`, optional alias enrichment flows that call the API)

## Environment

Copy the example env file and edit values:

```bash
cp .env.example .env
```

Important variables (see `.env.example` for the full list):

| Variable | Role |
|----------|------|
| `ANTHROPIC_API_KEY` | Required for Haiku extraction / checks |
| `ANTHROPIC_MODEL` | Model id for the Anthropic client (default in repo: `claude-haiku-4-5-20251001`; alias `claude-haiku-4-5` tracks the latest 4.5 snapshot) |
| `DB_PATH` | SQLite file (default `data/yargumark.db`) |
| `MODE` | `demo` vs `production` — confidence thresholds in the UI |
| `DEMO_CONFIDENCE_THRESHOLD` / `PRODUCTION_CONFIDENCE_THRESHOLD` | Matcher cutoffs |
| `CONTEXT_CHECK_LOW` / `CONTEXT_CHECK_HIGH` | Optional extra Haiku “context” step for borderline `PERSON` spans |

## End-to-end pipeline (typical order)

1. **Install** — `uv sync`
2. **Database schema** — `uv run yargumark-init-db`
3. **Registries** — `uv run yargumark-registry-sync sync` (loads configured sources into `entities` / aliases; includes remote and bundled fallbacks depending on config)
4. **Crawl news** (optional) — `uv run yargumark-crawl` — see crawler CLI in `src/yargumark/crawler/run.py` for `--start-url`, `--max-depth`, `--link-limit`, `--only-new`, `--fast-local`
5. **NLP per document** — `uv run yargumark-process-doc --doc-id N` or batch `uv run yargumark-process-doc --all --source uniyar --limit 500`
6. **Reindex mentions** (no LLM) — `uv run yargumark-reindex` — rebuilds `mentions` from `extracted_spans` + current registry
7. **UI** — `uv run streamlit run src/yargumark/app/main.py`
8. **Benchmark** (optional) — `uv run python scripts/benchmark.py` — compares fixtures vs DB at demo/production thresholds

Demo seed (small canned corpus):

```bash
uv run python scripts/seed_demo.py
```

Optional: **LLM-assisted alias enrichment** for registry rows (uses Anthropic when enabled in that flow):

```bash
uv run yargumark-enrich-aliases --help
```

## CLI quick reference

| Command | Purpose |
|---------|---------|
| `yargumark-init-db` | Create / migrate SQLite schema |
| `yargumark-registry-sync` | Sync registry sources into the DB |
| `yargumark-crawl` | Scrapy crawl for configured news hosts |
| `yargumark-process-doc` | Haiku extraction + matcher (+ optional context check) |
| `yargumark-reindex` | Rebuild `mentions` and clear render cache |
| `yargumark-enrich-aliases` | Optional Haiku pass on registry aliases |
| `yargumark-backfill-titles` | Backfill document titles from stored HTML |

## NLP cost (Haiku)

### What gets billed

- **Main extraction**: roughly **one** `messages` call per **distinct article body** (cache key is `sha256(utf-8 body)` in `llm_cache`). Re-running `yargumark-process-doc` on the same text hits the cache and does not spend another extraction call.
- **Optional context check**: borderline **person** spans can trigger **additional** Haiku calls; those are **not** always reflected in the same per-body rollup, so treat totals as a lower bound when many person hits sit in the check band.
- **Prompt caching** (Anthropic): long system prompts may accumulate **cached read** tokens at a lower $/MTok than fresh input. The Streamlit cost panel shows `cached_input_tokens`; the built-in USD helper uses headline input/output rates only — **real invoices can be lower** on large batches.

### Default $/MTok in code

`src/yargumark/pricing.py` uses **illustrative** list-style defaults (**$0.80 / $4.00** per million input / output tokens). **Confirm current numbers** on [Anthropic API pricing](https://www.anthropic.com/api) before signing off budgets.

### Empirical snapshot (one dev database, ~6.3k `uniyar` rows)

Measured from SQLite: documents whose body matched an `llm_cache` row used for extraction, **median ≈ 1.3k total tokens/doc**, **mean ≈ 2.5k**, **p90 ≈ 4.7k** (input+output as recorded). Unique cached extraction bodies in that snapshot: **121** rows for **158** processed docs (duplicate bodies amortize cost).

### Rough USD vs number of pages

Assume **one unique body per page** and use **median ~1.3k** and **mean ~2.5k** total tokens with the same **mean input/output split** as in that snapshot (~58% / ~42% of tokens). At **$0.80 / $4.00 per MTok**:

| New unique pages | ~USD (median-shaped est.) | ~USD (mean-shaped est.) |
|------------------|---------------------------|-------------------------|
| 100 | ~$0.27 | ~$0.53 |
| 500 | ~$1.3 | ~$2.6 |
| 1 000 | ~$2.7 | ~$5.3 |
| 6 000 | ~$16 | ~$32 |

**Scaling:** multiply the per-page column by your expected count of **distinct bodies** you will actually send to Haiku the first time. Template pages, duplicates, and re-runs after cache warm-up cost **much less**.

## Quick Start (Day 1)

```bash
uv sync
cp .env.example .env
uv run yargumark-init-db
uv run yargumark-registry-sync sync
uv run yargumark-crawl
uv run yargumark-process-doc --doc-id 1
uv run python scripts/seed_demo.py
uv run yargumark-reindex
uv run streamlit run src/yargumark/app/main.py
uv run python scripts/benchmark.py
```

Static checks:

```bash
uv run ruff check .
uv run mypy src
uv run pyright
```

## Кратко по-русски

1. `uv sync` → скопировать `.env` из `.env.example`, выставить `ANTHROPIC_API_KEY` и при необходимости `DB_PATH`.
2. `uv run yargumark-init-db` — схема SQLite.
3. `uv run yargumark-registry-sync sync` — загрузка реестров в БД.
4. `uv run yargumark-crawl` — обход новостей (см. флаги в коде CLI паука).
5. `uv run yargumark-process-doc --doc-id …` или `--all --source uniyar --limit N` — извлечение Haiku + матчинг; **повтор по тому же тексту тела статьи идёт из кэша**, отдельный вызов за извлечение не платится.
6. `uv run yargumark-reindex` — пересборка `mentions` без LLM.
7. `uv run streamlit run src/yargumark/app/main.py` — интерфейс.

Оценка денег: ориентир **~$0.003 на «типичную» страницу** (медиана по выборке) и **~$0.005** по среднему при тех же допущениях о $/MTok; **6k уникальных страниц** порядка **$16–32** за первичный прогон извлечения без учёта скидки prompt cache и без массовых context-check. Точные цифры — в биллинге Anthropic и в панели Streamlit по токенам.
