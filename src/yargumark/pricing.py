from __future__ import annotations

# Rough USD per 1M tokens for the configured model; update when Anthropic pricing changes.
# Not a billing quote — demo estimate only.
DEFAULT_INPUT_USD_PER_MILLION = 1.0
DEFAULT_OUTPUT_USD_PER_MILLION = 5.0


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
