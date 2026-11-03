"""Bounded synthetic digest projection and context-escaped, no-JavaScript HTML."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape

from wrap_brief.editorial.controls import EditorialResult
from wrap_brief.models import Item, Source, _check, validate_references
from wrap_brief.state.snapshot import MAX_RECORDS, Snapshot

MAX_CARDS = 50
MAX_HTML_BYTES = 1_048_576
_AVAILABLE = {"active", "corrected"}
_CLAIM = {
    "reported": "Reported",
    "confirmed": "Confirmed by source",
    "rumor": "Rumor — unconfirmed",
}


@dataclass(frozen=True, slots=True)
class CoverageView:
    id: str
    source_id: str
    title: str
    url: str
    publisher: str
    attribution: str
    claim: str
    corrected: bool
    stamp: datetime
    published: bool


@dataclass(frozen=True, slots=True)
class StoryView:
    id: str
    topic: str
    claim: str
    corrected: bool
    lead: CoverageView
    alternatives: tuple[CoverageView, ...]
    withheld: int


@dataclass(frozen=True, slots=True)
class DigestView:
    observed_at: datetime
    stories: tuple[StoryView, ...]
    omitted_groups: int
    source_count: int


def _coverage(item: Item, source: Source) -> CoverageView:
    return CoverageView(
        item.id,
        source.id,
        item.title,
        item.url,
        source.name,
        source.attribution,
        _CLAIM[item.claim_status],
        item.status == "corrected",
        item.published_at or item.first_seen_at,
        item.published_at is not None,
    )


def digest_view(snapshot: Snapshot) -> DigestView:
    """Project only eligible public display fields; never substitute an unavailable lead."""
    _check(type(snapshot) is Snapshot, "render", "validated snapshot required")
    _check(snapshot.kind == "synthetic", "render", "synthetic snapshots only")
    _check(len(snapshot.clusters) <= MAX_RECORDS, "render", "cluster limit")
    validate_references(snapshot.sources, snapshot.items, snapshot.clusters)
    _check(
        all(
            host in {"example.com", "example.org", "example.net"}
            or host.endswith((".example", ".example.com", ".example.org", ".example.net"))
            for source in snapshot.sources
            for host in source.allowed_hosts
        ),
        "render",
        "reserved fixture hosts required",
    )
    seen: set[str] = set()
    for group in snapshot.clusters:
        _check(not seen.intersection(group.member_ids), "render", "overlapping membership")
        seen.update(group.member_ids)
    _check(
        all(item.id in seen for item in snapshot.items if item.status in _AVAILABLE),
        "render",
        "ungrouped available item",
    )
    items = {item.id: item for item in snapshot.items}
    sources = {source.id: source for source in snapshot.sources}
    stories = []
    for group in snapshot.clusters:
        if group.lead_id is None or group.correction_status == "retracted":
            continue
        lead = items[group.lead_id]
        available = [items[id] for id in group.member_ids if items[id].status in _AVAILABLE]
        stories.append(
            StoryView(
                group.id,
                group.topic,
                _CLAIM[group.claim_status],
                group.correction_status == "corrected" or lead.status == "corrected",
                _coverage(lead, sources[lead.source_id]),
                tuple(
                    _coverage(item, sources[item.source_id])
                    for item in available
                    if item.id != lead.id
                ),
                len(group.member_ids) - len(available),
            )
        )
    _check(len(stories) <= MAX_CARDS, "render", "eligible card limit")
    stories.sort(key=lambda story: story.id)
    stories.sort(key=lambda story: story.lead.stamp, reverse=True)
    source_ids = {
        coverage.source_id for story in stories for coverage in (story.lead, *story.alternatives)
    }
    return DigestView(
        snapshot.observed_at, tuple(stories), len(snapshot.clusters) - len(stories), len(source_ids)
    )


def _e(value: str) -> str:
    return escape(value, quote=True)


def _time(stamp: datetime) -> str:
    value = stamp.isoformat().replace("+00:00", "Z")
    return f'<time datetime="{_e(value)}">{_e(value.replace("T", " ").replace("Z", " UTC"))}</time>'


def _date(coverage: CoverageView) -> str:
    prefix = "Published" if coverage.published else "Publication time unavailable · First seen"
    return f"{prefix} {_time(coverage.stamp)}"


def _link(coverage: CoverageView, claim: str) -> str:
    visible = f"Read at {coverage.publisher}"
    label = f"{visible}: {coverage.title} — {claim}"
    return f'<a href="{_e(coverage.url)}" rel="external noreferrer" aria-label="{_e(label)}">{_e(visible)} <span aria-hidden="true">→</span></a>'


def _story(story: StoryView) -> str:
    title_id = f"story-title-{story.id}"
    status_id = f"story-status-{story.id}"
    time_id = f"story-time-{story.id}"
    status = story.claim + (" · Corrected coverage" if story.corrected else "")
    parts = [
        f'<li><article class="story-card" id="story-{_e(story.id)}" aria-labelledby="{_e(title_id)}" aria-describedby="{_e(status_id)} {_e(time_id)}">',
        f'<p class="eyebrow">{_e(story.topic)}</p>',
        f'<p class="story-status" id="{_e(status_id)}">{_e(status)}</p>',
        f'<h2 id="{_e(title_id)}">{_e(story.lead.title)}</h2>',
        f'<p class="source-credit">Headline from <strong>{_e(story.lead.publisher)}</strong></p>',
        f'<p class="story-time" id="{_e(time_id)}">{_date(story.lead)}</p>',
        _link(story.lead, story.claim),
        f'<p class="source-attribution">{_e(story.lead.attribution)}</p>',
    ]
    if story.alternatives:
        parts.append(
            f'<details class="coverage"><summary>Other coverage ({len(story.alternatives)})<span class="visually-hidden"> for {_e(story.lead.title)}</span></summary><ul>'
        )
        for alternate in story.alternatives:
            claim = alternate.claim + (" · Corrected source" if alternate.corrected else "")
            parts.extend(
                [
                    f'<li><p class="alternate-title">{_e(alternate.title)}</p>',
                    f'<p class="story-time">{_e(claim)} · {_date(alternate)}</p>',
                    _link(alternate, alternate.claim),
                    f'<p class="source-attribution">{_e(alternate.attribution)}</p></li>',
                ]
            )
        parts.append("</ul></details>")
    if story.withheld:
        parts.append(
            f'<p class="withheld">Unavailable source records not linked: {story.withheld}.</p>'
        )
    parts.append("</article></li>")
    return "\n".join(parts)


def _render(snapshot: Snapshot, editorial_html: str = "") -> str:
    view = digest_view(snapshot)
    cards = "\n".join(_story(story) for story in view.stories)
    content = (
        f'<ol class="story-list">{cards}</ol>'
        if cards
        else '<p class="fixture-notice">This synthetic fixture has no displayable story groups.</p>'
    )
    if view.omitted_groups:
        content += f'<p class="fixture-notice">Groups with unavailable or withdrawn coverage not displayed: {view.omitted_groups}.</p>'
    content += editorial_html
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>Wrap Brief — synthetic digest</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="page">
<header class="site-header" id="top" tabindex="-1">
<p class="brand">wrap brief<span aria-hidden="true">.</span></p>
<nav aria-label="Page navigation"><a href="#stories">Stories</a><a href="#about">About</a></nav>
</header>
<main id="main" tabindex="-1">
<div class="digest-intro">
<p class="eyebrow">Offline · Synthetic digest</p>
<h1>Nintendo news. Less repetition.</h1>
<p class="lede">Hand-authored examples only. These are not real stories. No live feeds are enabled.</p>
<p class="fixture-observation">Fixture observation: {_time(view.observed_at)}</p>
<p class="fixture-observation">Displayed groups: {len(view.stories)} · Fictional publishers: {view.source_count}</p>
</div>
<section id="stories" tabindex="-1" aria-label="Synthetic story groups">
<p class="reading-note">Ordered by lead publication time, or first seen when publication is unknown.</p>
{content}
</section>
<section class="about" id="about" tabindex="-1" aria-labelledby="about-title">
<p class="eyebrow">Less noise. More perspective.</p>
<h2 id="about-title">About this fixture digest</h2>
<p>These examples demonstrate grouped, attributed headline links and alternate coverage. Links use reserved example domains, not real publishers. No automated article summaries or original reporting are implied. Source approval and live publication remain separate gates.</p>
</section>
</main>
<footer class="site-footer"><div>
<p>Independent and unofficial. Not affiliated with, endorsed by, or sponsored by Nintendo.</p>
<p class="working-name">Wrap Brief is a working name; brand and domain clearance are pending.</p>
</div><a href="#top">Back to top <span aria-hidden="true">↑</span></a></footer>
</div>
</body>
</html>
"""
    _check(len(html.encode("utf-8")) <= MAX_HTML_BYTES, "render", "HTML byte limit")
    return html


def render_digest(snapshot: Snapshot) -> str:
    """Return deterministic fixture-only HTML; stylesheet pairing belongs to the caller."""
    return _render(snapshot)


def render_editorial(result: EditorialResult) -> str:
    """Render result-bound reviewed records; the caller supplies trusted current authority."""
    _check(type(result) is EditorialResult, "editorial", "bound editorial result required")
    result.validate()
    labels = {
        "reported": "Reported claim evidence",
        "confirmed": "Confirmed by source — claim evidence",
        "rumor": "Rumor — unconfirmed claim evidence",
        "correct": "Correction acknowledged",
        "retract": "Coverage withdrawn following review",
    }
    records = []
    for notice in result.notices:
        target = f" · Item <code>{_e(notice.item_id)}</code>" if notice.item_id is not None else ""
        records.append(
            f"<li><p>{_e(labels[notice.kind])}{target} · Reviewed {_time(notice.reviewed_at)}"
            f" · Record <code>{_e(notice.public_ref)}</code></p></li>"
        )
    section = (
        (
            '\n<section id="editorial-records" aria-labelledby="editorial-records-title">'
            '<h2 id="editorial-records-title">Editorial records</h2>'
            "<p>Reviewed source labels and correction references, not original reporting. References are shown as text, not fetched or implied working links.</p>"
            "<ul>" + "\n".join(records) + "</ul></section>"
        )
        if records
        else ""
    )
    return _render(result.snapshot, section)
