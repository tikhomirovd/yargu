from __future__ import annotations

from yargumark.db import EntityForMatch
from yargumark.nlp.matcher import match_span_to_entity
from yargumark.nlp.types import LlmSpan


def test_lemma_match_prefers_single_entity() -> None:
    entities = [
        EntityForMatch(
            id=1,
            entity_type="undesirable_org",
            canonical_name="Meta Platforms Inc.",
            registry_source="local",
            registry_id="meta",
            aliases=["Meta"],
            lemma_keys={"platforms_meta"},
        )
    ]
    span = LlmSpan(
        start=0,
        end=4,
        surface="Meta",
        span_type="ORG",
        normalized="Meta",
        registry_candidate=None,
        confidence=0.9,
        reasoning="test",
    )
    result = match_span_to_entity(span, "platforms_meta", entities)
    assert result is not None
    assert result.entity_id == 1
    assert result.match_method == "lemma"
