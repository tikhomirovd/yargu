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
- Haiku cost for 500 docs: `< $2` (demo), `< $3` (production)

## Operational Documents

- Track confirmation and KPI lock: `docs/plan-track.md`
- Day-by-day checklists: `docs/iteration-checklists.md`
- 10-minute demo script: `docs/demo-script-10min.md`
- Daily go/no-go gates: `docs/go-no-go.md`
- Session memory and calibration notes: `CLAUDE.md`

## Quick Start (Day 1)

```bash
uv sync
cp .env.example .env
uv run yargumark-init-db
uv run yargumark-registry-sync sync
uv run yargumark-crawl
uv run yargumark-process-doc --doc-id 1
uv run python scripts/seed_demo.py
uv run streamlit run src/yargumark/app/main.py
uv run yargumark-reindex
uv run python scripts/benchmark.py
```

Static checks:

```bash
uv run ruff check .
uv run mypy src
uv run pyright
```
