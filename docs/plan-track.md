# Plan Track Confirmation

## Selected Track

**Primary track:** Plan A (Demo-first, 5 working days)  
**Fallback track:** Plan B (Production-first) if legal-risk recall gates are missed by Day 3.

## Selection Rationale

- Customer outcome is a strong local demo with clear business value.
- Plan A reaches end-to-end visibility sooner (UI + reasoning + wow reindex).
- Architecture still matches production trajectory (cache, matcher, registry sync, reindex).

## Scope Lock For Current Iteration

- Build and validate only MVP scope for local Streamlit demo.
- Do not include CI/CD, CMS write-back, multi-user auth, deployment, PDF/DOCX support.
- Keep the legal template logic explicit and type-dependent.

## KPI Lock For Demo Acceptance

### Quality
- Demo mode precision: `>= 0.95`
- Demo mode recall: `>= 0.85`
- Production mode precision: `>= 0.80`
- Production mode recall: `>= 0.95`
- Category recall checks: declensions, typos, aliases, masking, transliteration

### Performance and Cost
- Cached document processing: `< 2s/doc`
- Uncached document processing: `< 4s/doc`
- Incremental reindex (1 new entity, 500 docs): `< 1s`
- Haiku budget for 500 docs: `< $2` (demo target), `< $3` (production mode run)
- Prompt cache hit rate: `>= 90%`
- llm_cache repeat hit rate on same texts: `100%`

## Trigger To Switch To Plan B

Switch to Plan B if one or more conditions hold by Day 3 end:
- Production recall `< 0.90` on fixture-based validation;
- unresolved ambiguity in PERSON matching causing repeated misses;
- unstable extraction latency or frequent LLM availability issues.
