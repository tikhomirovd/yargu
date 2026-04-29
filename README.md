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

Heuristic USD math lives in **`src/yargumark/pricing.py`** (`estimate_llm_usd`, `estimate_document_extraction_pass_usd`, `estimate_alias_enrich_batch_usd`). Constants come from **one dev SQLite** (mostly `uniyar` news + registry work); re-fit after you accumulate your own `llm_cache` rows.

### What gets billed

- **Main extraction** (`yargumark-process-doc`): roughly **one** `messages` call per **distinct article body** (cache key is `sha256(utf-8 body)` in `llm_cache`). Re-running on the same text does **not** call the API again for extraction.
- **Alias enrichment** (`yargumark-enrich-aliases`): **one** Haiku call per **active** row in `entities` the first time each canonical name is enriched (cache key `alias_enrich:{normalized_name}`). Re-runs are cheap (cache hit, no API).
- **Optional context check**: borderline **person** spans can add **extra** Haiku calls; totals below are **without** that tail risk.
- **Prompt caching** (Anthropic): cached input is billed at a **lower** $/MTok than fresh input. Streamlit shows `cached_input_tokens`; `pricing.py` uses headline input/output rates only — **real invoices are often lower** on long batches.

### Default $/MTok in code

**$0.80 / $4.00** per million **input / output** tokens (placeholder list-style rates for Haiku-class models). **Confirm** on [Anthropic API pricing](https://www.anthropic.com/api) for your exact model (e.g. Haiku 4.5).

### Alias enrichment — «все нежелательные организации»

The CLI walks **every** `is_active=1` entity (all registry types). To budget **only** `undesirable_org`, multiply the **per-entity** numbers below by `SELECT COUNT(*) FROM entities WHERE is_active=1 AND type='undesirable_org'` on your DB (after `yargumark-registry-sync`). In one synced snapshot that count was **~195**; the published `fz255` undesirable list **drifts** over time (~high hundreds of rows in the upstream JSON is normal; inactive rows are dropped).

Per **first-time** alias call (empirical average from `llm_cache` rows whose JSON is the alias payload only):

| Quantity | ~total tokens (in+out) | ~USD @ $0.80/$4 per MTok |
|----------|------------------------|---------------------------|
| 1 entity | ~415 | **~$0.0009** |
| **~195** undesirable orgs | **~81k** | **~$0.18** |
| ~1.7k (all active types in that DB: agents + undesirable + terrorist + banned) | **~705k** | **~$1.5** |

Formula: `estimate_alias_enrich_batch_usd(n)` in `pricing.py` (uses **~235** input + **~180** output tokens per entity on average in that sample).

### Document extraction — «все страницы сайта»

There is **no authoritative public sitemap** that matches today’s URL shape (the hosted `sitemap_000.xml` is **stale / legacy** `detail.php` URLs). Treat **“все страницы”** as a **planning bracket**:

| Scenario | How to think about `N` |
|----------|-------------------------|
| **What you already crawled** | `SELECT COUNT(*) FROM documents WHERE source='uniyar'` — often **~6–7k** URLs after a default crawl. |
| **Fuller site coverage** | Raise `--max-depth`, `--link-limit`, add `--start-url` seeds; expect **roughly high single-digit thousands → low tens of thousands** of *HTML* pages depending on policy pages, faculties, and archives — **only a crawl or external `site:` index** narrows this. |
| **Per-page NLP cost** | Scale by **`N` distinct bodies** you run through Haiku the **first** time (templates and duplicates hit extraction cache). |

Per **first-time** extraction (empirical **median** vs **mean** total tokens per document-with-cache in the same dev DB: **~1.3k** vs **~2.5k** total; split encoded as **~734 / ~523** vs **~1451 / ~1033** input/output tokens in `pricing.py`):

| New unique bodies `N` | ~total tokens (median profile) | ~USD (median) | ~total tokens (mean profile) | ~USD (mean) |
|-------------------------|----------------------------------|---------------|--------------------------------|-------------|
| 1 000 | ~1.26M | ~$2.7 | ~2.48M | ~$5.3 |
| **~6.3k** (typical current crawl) | **~7.9M** | **~$17** | **~15.6M** | **~$33** |
| 10 000 | ~12.6M | ~$27 | ~24.8M | ~$53 |
| 15 000 | ~18.8M | ~$40 | ~37.3M | ~$80 |

Use `estimate_document_extraction_pass_usd(N, profile="median"|"mean")` in code.

**Scaling:** multiply by the number of **distinct bodies** you actually process once. Empty-body pages are **skipped** by the crawler pipeline and never become `documents` rows with NLP cache in the usual path — see `src/yargumark/crawler/pipelines.py`.

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

Оценка денег: **страницы** — ориентир **~$0.003** за первичное извлечение с «типичного» тела (медиана) и **~$0.005** по среднему; **~6k уникальных тел** порядка **$17 / $33** (медиана / средний профиль) при $0.80/$4 за MTok; **10–15k** страниц — умножить на те же доллары/страницу (см. таблицу в разделе [NLP cost](#nlp-cost-haiku)). **Алиасы**: только нежелательные (**~195** строк в одной синхронизированной базе) — порядка **~81k токенов и ~$0.18** один раз; все активные сущности всех типов в той же базе — **~$1.5**. Реальный счёт ниже при prompt cache; context-check не включён. Подробности и функции — `src/yargumark/pricing.py`.
