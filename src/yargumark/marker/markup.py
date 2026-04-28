from __future__ import annotations

import html
from dataclasses import dataclass

from yargumark.marker import templates


@dataclass(frozen=True)
class MentionPaint:
    start: int
    end: int
    surface: str
    entity_type: str
    canonical_name: str
    confidence: float
    match_method: str
    reasoning: str


@dataclass(frozen=True)
class MarkedDocument:
    html_body: str
    footnotes_html: str


def _validate_non_overlapping(mentions: list[MentionPaint]) -> list[MentionPaint]:
    sorted_mentions = sorted(mentions, key=lambda m: (m.start, -m.end))
    kept: list[MentionPaint] = []
    last_end = -1
    for mention in sorted_mentions:
        if mention.start < last_end:
            continue
        kept.append(mention)
        last_end = mention.end
    return kept


def build_marked_html(body: str, mentions: list[MentionPaint]) -> MarkedDocument:
    """Build HTML from plain text and mention offsets (UTF-8 character indices)."""
    safe_mentions = _validate_non_overlapping(mentions)
    foreign_names: list[str] = []
    terrorist_names: list[str] = []
    for mention in safe_mentions:
        if mention.entity_type == "foreign_agent" and mention.canonical_name not in foreign_names:
            foreign_names.append(mention.canonical_name)
        if (
            mention.entity_type == "terrorist_extremist"
            and mention.canonical_name not in terrorist_names
        ):
            terrorist_names.append(mention.canonical_name)

    parts: list[str] = []
    position = 0
    for mention in sorted(safe_mentions, key=lambda m: m.start):
        if mention.end > len(body) or mention.start < position:
            continue
        parts.append(html.escape(body[position : mention.start], quote=False))
        surface = body[mention.start : mention.end]
        if surface != mention.surface:
            surface = mention.surface
        escaped_surface = html.escape(surface, quote=False)
        badge = templates.inline_label_html(mention.entity_type, mention.canonical_name)
        parts.append(f'<mark class="ym-mark">{escaped_surface}{badge}</mark>')
        position = mention.end
    parts.append(html.escape(body[position:], quote=False))

    footnotes: list[str] = []
    for name in foreign_names:
        footnotes.append(templates.foreign_agent_footnote_html(name))
    for name in terrorist_names:
        footnotes.append(templates.terrorist_footnote_html(name))
    footnotes_html = "".join(footnotes)
    return MarkedDocument(html_body="".join(parts), footnotes_html=footnotes_html)


def wrap_article(inner_html: str, footnotes_html: str) -> str:
    blocks = [f'<article class="ym-article">{inner_html}</article>']
    if footnotes_html:
        blocks.append(f'<section class="ym-footnotes">{footnotes_html}</section>')
    return "".join(blocks)
