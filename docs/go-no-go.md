# Go/No-Go Criteria By Day

## Usage
This matrix defines whether to continue on Plan A or switch to contingency actions.

## Day 1 Gate - Foundation

- **Data**
  - Go: at least 100 successfully parsed pages in trial crawl, schema applies cleanly.
  - No-Go: parser instability or repeated schema failures.
- **Quality**
  - Go: duplicate handling works by `html_hash`.
  - No-Go: repeated duplicate inserts or broken offsets.
- **Cost/Time**
  - Go: crawl throughput predicts 500 pages overnight.
  - No-Go: estimated crawl exceeds practical demo window.
- **Stability**
  - Go: WAL mode enabled, no lock contention in basic tests.
  - No-Go: recurring DB lock errors.

## Day 2 Gate - Registry Layer

- **Data**
  - Go: all 4 categories loaded, 1500+ active entities.
  - No-Go: missing category or incomplete critical source.
- **Quality**
  - Go: canonical + alias lookup returns expected results on manual sample.
  - No-Go: poor normalization causes frequent misses in sample checks.
- **Cost/Time**
  - Go: full sync within acceptable local runtime.
  - No-Go: sync too slow or brittle for rehearsal usage.
- **Stability**
  - Go: sync logs include counts/errors and are reproducible.
  - No-Go: non-deterministic outcomes across identical runs.

## Day 3 Gate - NER and Matching

- **Data**
  - Go: extraction outputs persisted as spans including unmatched candidates.
  - No-Go: partial persistence or missing span metadata.
- **Quality**
  - Go: production recall >= 0.90 on calibration set.
  - No-Go: production recall < 0.90 or severe PERSON ambiguity misses.
- **Cost/Time**
  - Go: average uncached runtime under 4s/doc on calibration sample.
  - No-Go: sustained runtime above threshold.
- **Stability**
  - Go: retry and cache mechanisms absorb transient LLM/API failures.
  - No-Go: frequent failed runs without graceful fallback.

## Day 4 Gate - UI and Demo Readiness

- **Data**
  - Go: fixtures and expected labels are available and validated.
  - No-Go: fixture set incomplete or unreviewed.
- **Quality**
  - Go: demo precision >= 0.95 on fixtures.
  - No-Go: obvious false positives in demo mode.
- **Cost/Time**
  - Go: cache hit behavior visible and token/cost reporting works.
  - No-Go: no reliable cost visibility for demo narrative.
- **Stability**
  - Go: all core pages load and basic flow is repeatable.
  - No-Go: page crashes or unstable rendering.

## Day 5 Gate - Final Acceptance

- **Data**
  - Go: benchmark report generated for 500 docs + fixtures.
  - No-Go: missing metrics for customer slide.
- **Quality**
  - Go: demo and production KPI targets met or justified with explicit caveats.
  - No-Go: KPI gaps without mitigation narrative.
- **Cost/Time**
  - Go: incremental reindex demo shows sub-second and `$0` LLM spend.
  - No-Go: reindex path still triggers LLM or exceeds target.
- **Stability**
  - Go: live rehearsal completed; backup video ready.
  - No-Go: untested live flow with no fallback.

## Escalation Rules

- If Day 3 quality gate fails, temporarily pivot to Plan B priorities:
  - improve recall first;
  - reduce UI scope;
  - preserve explainability.
- If Day 4 stability gate fails, freeze new features and fix only demo-critical paths.
