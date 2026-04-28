# Demo Script (10 Minutes)

## Objective
Show that YarguMark is practical, explainable, cost-aware, and safer than manual checks.

## Setup Before Call (5-10 minutes in advance)
- Start Streamlit locally.
- Confirm registry sync date is visible and recent.
- Preload one document with clear positive mentions.
- Warm cache with one pipeline run.
- Keep one fixture-heavy page ready for the final proof segment.

## Timeline

### 0:00-1:00 Problem and Value
- Explain legal requirement and risk of missed labels.
- State core value: automatic detection with legal-text-aware marking.
- Mention dual modes: Demo (clean) vs Production (recall-first).

### 1:00-3:00 News Library
- Open News Library.
- Show corpus size and mention counts.
- Filter to documents with markers to prove practical throughput.

### 3:00-5:00 Document View (Main Proof)
- Open one flagged document.
- Compare original and marked versions side by side.
- Open "why this was marked" panel:
  - surface form;
  - canonical entity;
  - match method;
  - confidence;
  - one-line reasoning.

### 5:00-6:30 Mode Switch Story
- Toggle Demo -> Production on the same document.
- Show additional gray-zone mentions appearing.
- Explain policy trade-off:
  - Demo avoids absurd false positives;
  - Production minimizes legal miss risk.

### 6:30-7:30 Sandbox
- Paste short text with masked aliases (for example, colloquial forms).
- Run pipeline and show immediate marked result.
- Point at token/cost counter to show economics.

### 7:30-9:00 Update Registry Wow
- Add one synthetic registry entity in the update demo page.
- Trigger incremental reindex.
- Show affected documents count, execution time, and `$0` LLM usage.
- Open one changed document and compare before/after effect.

### 9:00-10:00 Fixtures and Close
- Open fixtures tab.
- Show tricky cases and pass/fail summary.
- Close with rollout path:
  - MVP pilot on customer data now;
  - optional migration to local LLM later with same architecture.

## Talk Track Cheatsheet
- "We store all extracted spans, so registry updates do not require re-running LLM."
- "Reasoning is shown per mention, reducing black-box concerns."
- "Mode policy reflects legal risk tolerance, not model inconsistency."

## Backup Plan
- If API latency appears, run cached scenario only.
- If live update page fails, show pre-recorded 3-minute backup video.
