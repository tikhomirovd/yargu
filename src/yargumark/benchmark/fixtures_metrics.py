from __future__ import annotations

from dataclasses import dataclass

from yargumark.registry.normalize import normalize_name


def _norm_surface(value: str) -> str:
    return normalize_name(value).casefold()


@dataclass(frozen=True)
class PrecisionRecall:
    precision: float
    recall: float
    true_positive: int
    false_positive: int
    false_negative: int


def precision_recall_surfaces(expected: list[str], actual: list[str]) -> PrecisionRecall:
    expected_set = {_norm_surface(item) for item in expected if item.strip()}
    actual_set = {_norm_surface(item) for item in actual if item.strip()}
    true_positive = len(expected_set & actual_set)
    false_positive = len(actual_set - expected_set)
    false_negative = len(expected_set - actual_set)
    denom_p = true_positive + false_positive
    precision = true_positive / denom_p if denom_p else 1.0
    denom_r = true_positive + false_negative
    recall = true_positive / denom_r if denom_r else 1.0
    return PrecisionRecall(
        precision=precision,
        recall=recall,
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
    )
