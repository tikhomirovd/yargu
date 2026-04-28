from __future__ import annotations

from yargumark.marker.markup import MentionPaint, build_marked_html


def test_build_marked_html_inserts_badge_after_surface() -> None:
    body = "Компания Meta тест."
    mentions = [
        MentionPaint(
            start=9,
            end=13,
            surface="Meta",
            entity_type="undesirable_org",
            canonical_name="Meta Platforms Inc.",
            confidence=0.95,
            match_method="alias",
            reasoning="unit",
        )
    ]
    marked = build_marked_html(body, mentions)
    assert "Meta" in marked.html_body
    assert "нежелательной" in marked.html_body
    assert marked.footnotes_html == ""
