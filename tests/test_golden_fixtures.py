from __future__ import annotations

from yargumark.benchmark.fixtures_metrics import precision_recall_surfaces


def test_precision_recall_perfect_overlap() -> None:
    result = precision_recall_surfaces(["Инста", "Meta"], ["инста", "meta"])
    assert result.true_positive == 2
    assert result.false_positive == 0
    assert result.false_negative == 0
    assert result.precision == 1.0
    assert result.recall == 1.0


def test_precision_recall_counts_false_positive() -> None:
    result = precision_recall_surfaces(["Инста"], ["Инста", "Лишнее"])
    assert result.true_positive == 1
    assert result.false_positive == 1
    assert result.false_negative == 0
    assert result.precision == 0.5
    assert result.recall == 1.0


def test_precision_recall_counts_false_negative() -> None:
    result = precision_recall_surfaces(["Инста", "Вторая"], ["Инста"])
    assert result.true_positive == 1
    assert result.false_positive == 0
    assert result.false_negative == 1
    assert result.precision == 1.0
    assert result.recall == 0.5
