from __future__ import annotations

import html


def escape_label_name(name: str) -> str:
    return html.escape(name.strip(), quote=False)


def inline_label_html(entity_type: str, _canonical_name: str) -> str:
    """Return HTML fragment placed immediately after the surface form (name already in text)."""
    if entity_type == "foreign_agent":
        return (
            '<span class="ym-badge ym-foreign_agent"> (выполняет функции иностранного агента)'
            "<sup>*</sup></span>"
        )
    if entity_type == "undesirable_org":
        return (
            '<span class="ym-badge ym-undesirable_org"> '
            "(деятельность организации признана нежелательной на территории РФ)</span>"
        )
    if entity_type == "terrorist_extremist":
        return (
            '<span class="ym-badge ym-terrorist_extremist">'
            "<sup>*</sup> (организация запрещена в РФ как экстремистская/"
            "террористическая)</span>"
        )
    if entity_type == "banned_by_court":
        return (
            '<span class="ym-badge ym-banned_by_court"> '
            "(организация запрещена в РФ по решению суда)</span>"
        )
    return f'<span class="ym-badge ym-unknown">{escape_label_name(_canonical_name)}</span>'


def foreign_agent_footnote_html(canonical_name: str) -> str:
    safe = escape_label_name(canonical_name)
    return (
        f"<p><sup>*</sup> Настоящий материал произведён/распространён иностранным агентом "
        f"{safe}.</p>"
        f"<p>Содержание доступно только для аудитории 18+.</p>"
    )


def terrorist_footnote_html(canonical_name: str) -> str:
    safe = escape_label_name(canonical_name)
    return (
        f"<p><sup>*</sup> {safe} — организация запрещена в РФ как экстремистская/"
        f"террористическая.</p>"
    )
