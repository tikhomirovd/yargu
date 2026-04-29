from __future__ import annotations

from typing import Literal

# Rough USD per 1M tokens for Claude Haiku (e.g. 4.5); update when Anthropic pricing changes.
# Public list prices are often around $0.80 / $4.00 per MTok (input / output); confirm on
# https://www.anthropic.com/api before budgeting. Not a billing quote — demo estimate only.
DEFAULT_INPUT_USD_PER_MILLION = 0.8
DEFAULT_OUTPUT_USD_PER_MILLION = 4.0

# --- Document extraction (`yargumark-process-doc`, cache key = sha256(body)) ---
# Empirical: join `documents` to `llm_cache` on body hash for one dev uniyar-heavy DB
# (median/mean total = input+output per first-time extraction row).
_DOCUMENT_EXTRACTION_MEDIAN_INPUT = 734
_DOCUMENT_EXTRACTION_MEDIAN_OUTPUT = 523
_DOCUMENT_EXTRACTION_MEAN_INPUT = 1451
_DOCUMENT_EXTRACTION_MEAN_OUTPUT = 1033

# --- Alias enrichment (`yargumark-enrich-aliases`, one `messages` call per entity, cached) ---
# Empirical: `llm_cache` rows whose `response_json` starts with `{"aliases":` (alias-enrich
# payload only), averaged input/output token columns across ~1.7k rows in the same dev DB.
_ALIAS_ENRICH_AVG_INPUT_TOKENS = 235
_ALIAS_ENRICH_AVG_OUTPUT_TOKENS = 180


def estimate_llm_usd(
    input_tokens: int,
    output_tokens: int,
    *,
    input_per_million: float = DEFAULT_INPUT_USD_PER_MILLION,
    output_per_million: float = DEFAULT_OUTPUT_USD_PER_MILLION,
) -> float:
    return (max(0, input_tokens) / 1_000_000.0) * input_per_million + (
        max(0, output_tokens) / 1_000_000.0
    ) * output_per_million


def estimate_document_extraction_pass_tokens(
    new_unique_pages: int,
    *,
    profile: Literal["median", "mean"] = "median",
) -> tuple[int, int]:
    """Return (input_tokens, output_tokens) for N first-time body extractions (no cache)."""
    if profile == "mean":
        return (
            new_unique_pages * _DOCUMENT_EXTRACTION_MEAN_INPUT,
            new_unique_pages * _DOCUMENT_EXTRACTION_MEAN_OUTPUT,
        )
    return (
        new_unique_pages * _DOCUMENT_EXTRACTION_MEDIAN_INPUT,
        new_unique_pages * _DOCUMENT_EXTRACTION_MEDIAN_OUTPUT,
    )


def estimate_document_extraction_pass_usd(
    new_unique_pages: int,
    *,
    profile: Literal["median", "mean"] = "median",
    input_per_million: float = DEFAULT_INPUT_USD_PER_MILLION,
    output_per_million: float = DEFAULT_OUTPUT_USD_PER_MILLION,
) -> float:
    """USD for N first-time Haiku extractions on distinct bodies (see README caveats)."""
    inp, out = estimate_document_extraction_pass_tokens(new_unique_pages, profile=profile)
    return estimate_llm_usd(
        inp,
        out,
        input_per_million=input_per_million,
        output_per_million=output_per_million,
    )


def estimate_alias_enrich_batch_tokens(n_entities: int) -> tuple[int, int]:
    """Return (input_tokens, output_tokens) for N first-time alias-enrich calls (no cache)."""
    return (
        n_entities * _ALIAS_ENRICH_AVG_INPUT_TOKENS,
        n_entities * _ALIAS_ENRICH_AVG_OUTPUT_TOKENS,
    )


def estimate_alias_enrich_batch_usd(
    n_entities: int,
    *,
    input_per_million: float = DEFAULT_INPUT_USD_PER_MILLION,
    output_per_million: float = DEFAULT_OUTPUT_USD_PER_MILLION,
) -> float:
    """USD for N first-time `enrich_entity_aliases` API calls (see README caveats)."""
    inp, out = estimate_alias_enrich_batch_tokens(n_entities)
    return estimate_llm_usd(
        inp,
        out,
        input_per_million=input_per_million,
        output_per_million=output_per_million,
    )
