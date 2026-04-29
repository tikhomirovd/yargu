from __future__ import annotations

# Rough USD per 1M tokens for Claude 3.5 Haiku-class models; update when Anthropic pricing changes.
# Public list prices are often around $0.80 / $4.00 per MTok (input / output); confirm on
# https://www.anthropic.com/api before budgeting. Not a billing quote — demo estimate only.
DEFAULT_INPUT_USD_PER_MILLION = 0.8
DEFAULT_OUTPUT_USD_PER_MILLION = 4.0


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
