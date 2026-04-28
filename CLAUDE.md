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
