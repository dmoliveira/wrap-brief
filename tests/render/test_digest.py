from __future__ import annotations

import socket
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from fixtures.support import read_json

from tools import build_fixture_site as builder
from wrap_brief.models import Cluster, ContractError
from wrap_brief.render import digest
from wrap_brief.state.snapshot import PollCheckpoint, Snapshot

ROOT = Path(__file__).resolve().parents[2]


def fixture(case: str = "digest") -> Snapshot:
    return Snapshot.from_dict(read_json(f"views/{case}.json"))


class Parsed(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class DigestTests(unittest.TestCase):
    def test_all_shared_views_match_reviewable_golden_html(self):
        for case in builder.CASES:
            with self.subTest(case=case):
                expected = (ROOT / "tests" / "render" / "goldens" / f"{case}.html").read_text()
                self.assertEqual(digest.render_digest(fixture(case)), expected)

    def test_view_is_frozen_deterministic_and_leaves_snapshot_unchanged(self):
        value = fixture()
        before = value.to_json()
        view = digest.digest_view(value)
        self.assertEqual(
            [story.id for story in view.stories],
            ["demo-unknown-group", "demo-rumor-group", "demo-update-group"],
        )
        self.assertEqual(view.source_count, 3)
        with self.assertRaises(FrozenInstanceError):
            view.stories[0].topic = "changed"
        reordered = replace(
            value,
            items=tuple(reversed(value.items)),
            sources=tuple(reversed(value.sources)),
            clusters=tuple(reversed(value.clusters)),
        )
        self.assertEqual(digest.render_digest(value), digest.render_digest(reordered))
        self.assertEqual(value.to_json(), before)

    def test_render_is_pure_and_does_not_fetch_or_read_assets(self):
        value = fixture()
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(Path, "read_bytes", side_effect=AssertionError("filesystem")),
        ):
            self.assertIn("Synthetic digest", digest.render_digest(value))

    def test_all_dynamic_text_fields_are_escaped_in_text_and_attributes(self):
        payload = "\"><img src=x onerror=alert(1)>&'"
        base = fixture()
        for field in ("title", "publisher", "attribution", "topic"):
            with self.subTest(field=field):
                value = base
                if field == "title":
                    value = replace(
                        value,
                        items=tuple(
                            replace(i, title=payload) if i.id == "demo-update-a" else i
                            for i in value.items
                        ),
                    )
                elif field in {"publisher", "attribution"}:
                    key = "name" if field == "publisher" else field
                    value = replace(
                        value,
                        sources=tuple(
                            replace(s, **{key: payload}) if s.id == "demo-a" else s
                            for s in value.sources
                        ),
                    )
                else:
                    value = replace(
                        value,
                        clusters=tuple(
                            replace(c, topic=payload) if c.id == "demo-update-group" else c
                            for c in value.clusters
                        ),
                    )
                html = digest.render_digest(value)
                parsed = Parsed(html)
                self.assertNotIn("<img", html)
                self.assertTrue(any(payload in text for text in parsed.text))
                self.assertFalse(
                    {tag for tag, _ in parsed.tags} & {"img", "script", "iframe", "style"}
                )
                self.assertFalse(
                    any(
                        name.startswith("on") or name == "style"
                        for _, attrs in parsed.tags
                        for name in attrs
                    )
                )
                self.assertFalse(any("target" in attrs for _, attrs in parsed.tags))

    def test_source_urls_preserve_query_bytes_and_never_become_markup(self):
        value = fixture()
        url = "https://example.com/news/update?edition=2&x=%22%3E%3Cscript%3E&x="
        value = replace(
            value,
            items=tuple(replace(i, url=url) if i.id == "demo-update-a" else i for i in value.items),
        )
        html = digest.render_digest(value)
        parsed = Parsed(html)
        self.assertIn(url, [attrs.get("href") for tag, attrs in parsed.tags if tag == "a"])
        self.assertIn("?edition=2&amp;x=", html)
        for bad in (
            "javascript:alert(1)",
            "data:text/html,bad",
            'https://example.com/"onmouseover=bad',
            "https://example.com/?token=private-marker",
            "https://example.com.evil.org/news",
        ):
            with self.subTest(url=bad), self.assertRaises(ContractError):
                replace(
                    value,
                    items=tuple(
                        replace(i, url=bad) if i.id == "demo-update-a" else i for i in value.items
                    ),
                )

    def test_claims_are_explicit_for_group_and_alternates_not_inferred(self):
        value = fixture()
        self.assertNotIn("Confirmed by source", digest.render_digest(value))
        value = replace(
            value,
            items=tuple(
                replace(i, claim_status="rumor") if i.id == "demo-update-b" else i
                for i in value.items
            ),
        )
        view = digest.digest_view(value)
        update = next(s for s in view.stories if s.id == "demo-update-group")
        self.assertEqual(update.claim, "Reported")
        self.assertEqual(update.alternatives[0].claim, "Rumor — unconfirmed")
        self.assertIn("Rumor — unconfirmed", digest.render_digest(value))
        confirmed = replace(
            fixture(),
            items=tuple(
                replace(i, claim_status="confirmed") if i.id == "demo-update-a" else i
                for i in fixture().items
            ),
            clusters=tuple(
                replace(c, claim_status="confirmed") if c.id == "demo-update-group" else c
                for c in fixture().clusters
            ),
        )
        self.assertIn("Confirmed by source", digest.render_digest(confirmed))

    def test_unknown_date_uses_only_first_seen_and_does_not_fake_publication(self):
        value = fixture()
        unknown = next(i for i in value.items if i.id == "demo-unknown")
        value = replace(
            value,
            items=tuple(
                replace(i, updated_at=i.first_seen_at - timedelta(days=3)) if i == unknown else i
                for i in value.items
            ),
        )
        story = next(s for s in digest.digest_view(value).stories if s.id == "demo-unknown-group")
        self.assertFalse(story.lead.published)
        self.assertEqual(story.lead.stamp, unknown.first_seen_at)
        html = digest.render_digest(value)
        self.assertIn("Publication time unavailable · First seen", html)
        self.assertNotIn("2025-12-30", html)
        self.assertNotIn("Last checked", html)

    def test_aria_relationships_unique_ids_and_native_disclosure_counts(self):
        parsed = Parsed(digest.render_digest(fixture()))
        ids = [attrs["id"] for _, attrs in parsed.tags if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sum(tag == "h1" for tag, _ in parsed.tags), 1)
        self.assertEqual(sum(tag == "details" for tag, _ in parsed.tags), 1)
        self.assertIn("Other coverage (2)", parsed.text)
        for tag, attrs in parsed.tags:
            if tag == "article":
                self.assertIn(attrs["aria-labelledby"], ids)
                for id in attrs["aria-describedby"].split():
                    self.assertIn(id, ids)
            if tag == "a" and attrs["href"].startswith("https:"):
                self.assertIn("Read at Synthetic Source", attrs["aria-label"])
                self.assertIn("noreferrer", attrs["rel"])

    def test_unavailable_members_are_not_repromoted_or_exposed(self):
        value = fixture("corrected")
        value = replace(
            value,
            items=tuple(
                replace(i, title="private-withdrawn-marker") if i.status == "retracted" else i
                for i in value.items
            ),
        )
        html = digest.render_digest(value)
        self.assertIn("Corrected coverage", html)
        self.assertIn("Unavailable source records not linked: 1", html)
        self.assertNotIn("private-withdrawn-marker", html)
        self.assertNotIn("https://example.com/news/update", html)
        self.assertNotIn("<details", html)
        for status in ("removed", "quarantined", "retracted"):
            with self.subTest(status=status):
                changed = replace(
                    value,
                    items=tuple(
                        replace(i, status=status) if i.id == "demo-update-a" else i
                        for i in value.items
                    ),
                )
                self.assertNotIn("private-withdrawn-marker", digest.render_digest(changed))

    def test_retracted_group_is_omitted_even_with_an_available_lead(self):
        value = fixture()
        value = replace(
            value,
            clusters=tuple(
                replace(c, correction_status="retracted") if c.id == "demo-update-group" else c
                for c in value.clusters
            ),
        )
        html = digest.render_digest(value)
        self.assertNotIn("Fictional console update announced", html)
        self.assertIn("Groups with unavailable or withdrawn coverage not displayed: 1", html)

    def test_all_unavailable_groups_have_no_title_or_link_and_empty_is_neutral(self):
        value = fixture()
        item = replace(value.items[0], status="removed", title="private-removed-marker")
        group = Cluster("withdrawn", (item.id,), None, correction_status="retracted")
        value = replace(value, items=(item,), clusters=(group,))
        html = digest.render_digest(value)
        self.assertNotIn(item.title, html)
        self.assertNotIn(item.url, html)
        self.assertIn("This synthetic fixture has no displayable story groups.", html)
        self.assertIn("not displayed: 1", html)
        self.assertNotIn("No news today", digest.render_digest(fixture("empty")))

    def test_invalid_membership_lead_and_live_inputs_fail_without_echo(self):
        value = fixture()
        duplicated = replace(
            value, clusters=(*value.clusters, replace(value.clusters[0], id="duplicate"))
        )
        for candidate in (
            duplicated,
            replace(value, clusters=()),
            replace(value, kind="live"),
            object(),
        ):
            with self.subTest(type=type(candidate)), self.assertRaises(ContractError) as error:
                digest.render_digest(candidate)
            self.assertLess(len(str(error.exception)), 100)
            self.assertNotIn(value.items[0].title, str(error.exception))
        with self.assertRaises(ContractError):
            replace(
                value,
                items=tuple(
                    replace(i, status="retracted") if i.id == "demo-update-a" else i
                    for i in value.items
                ),
            )

    def test_nonfixture_hosts_and_private_metadata_are_not_published(self):
        value = fixture()
        source = value.sources[0]
        changed_source = replace(
            source,
            site_url="https://publisher.org/",
            feed_url="https://publisher.org/feed",
            allowed_hosts=("publisher.org",),
        )
        changed = replace(value, sources=(changed_source,), items=(), clusters=())
        with self.assertRaisesRegex(ContractError, "reserved fixture hosts required"):
            digest.render_digest(changed)
        value = replace(
            value,
            items=tuple(replace(i, guid="private-guid-marker") for i in value.items),
            sources=tuple(
                replace(s, approval_ref="docs/private-reference-marker.md") for s in value.sources
            ),
        )
        html = digest.render_digest(value)
        self.assertNotIn("private-guid-marker", html)
        self.assertNotIn("private-reference-marker", html)
        checkpoint = PollCheckpoint(
            value.sources[0].id,
            value.observed_at,
            value.observed_at,
            etag="private-etag-marker",
            status="ok",
        )
        self.assertNotIn(
            "private-etag-marker", digest.render_digest(replace(value, checkpoints=(checkpoint,)))
        )

    def test_fifty_card_limit_is_after_classification_not_silent_truncation(self):
        value = fixture()
        base = next(i for i in value.items if i.id == "demo-update-a")
        items = tuple(
            replace(base, id=f"item-{n}", url=f"https://example.com/news/{n}") for n in range(51)
        )
        groups = tuple(
            Cluster(f"group-{n:03}", (item.id,), item.id) for n, item in enumerate(items)
        )
        fifty = replace(value, items=items[:50], clusters=groups[:50])
        self.assertEqual(len(digest.digest_view(fifty).stories), 50)
        unavailable = replace(base, id="old", status="removed")
        fifty_with_omitted = replace(
            fifty,
            items=(*fifty.items, unavailable),
            clusters=(*fifty.clusters, Cluster("old-group", (unavailable.id,), None)),
        )
        self.assertEqual(len(digest.digest_view(fifty_with_omitted).stories), 50)
        self.assertEqual(digest.digest_view(fifty_with_omitted).omitted_groups, 1)
        with self.assertRaisesRegex(ContractError, "eligible card limit"):
            digest.render_digest(replace(value, items=items, clusters=groups))

    def test_html_limit_counts_utf8_bytes_at_exact_boundary(self):
        value = fixture()
        html = digest.render_digest(value)
        size = len(html.encode("utf-8"))
        self.assertGreater(size, len(html))
        with patch.object(digest, "MAX_HTML_BYTES", size):
            self.assertEqual(digest.render_digest(value), html)
        for limit in (size - 1, len(html)):
            with (
                self.subTest(limit=limit),
                patch.object(digest, "MAX_HTML_BYTES", limit),
                self.assertRaisesRegex(ContractError, "HTML byte limit"),
            ):
                digest.render_digest(value)


class FixtureBuildTests(unittest.TestCase):
    def prepare(self, root: Path) -> None:
        (root / "web").mkdir(parents=True)
        (root / "web" / "styles.css").write_bytes((ROOT / "web" / "styles.css").read_bytes())
        views = root / "tests" / "fixtures" / "views"
        views.mkdir(parents=True)
        for case in builder.CASES:
            (views / f"{case}.json").write_bytes(
                (ROOT / "tests" / "fixtures" / "views" / f"{case}.json").read_bytes()
            )

    def test_two_fresh_builds_are_byte_identical_and_existing_output_is_preserved(self):
        outputs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.prepare(root)
                with patch.object(builder, "ROOT", root):
                    output = builder.build_fixture("digest")
                    outputs.append({p.name: p.read_bytes() for p in output.iterdir()})
                    with self.assertRaisesRegex(ContractError, "output exists"):
                        builder.build_fixture("digest")
                    self.assertEqual(
                        outputs[-1], {p.name: p.read_bytes() for p in output.iterdir()}
                    )
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(set(outputs[0]), {"index.html", "styles.css"})

    def test_oversized_stylesheet_or_live_fixture_fails_before_output_creation(self):
        for case in ("stylesheet", "live"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.prepare(root)
                if case == "stylesheet":
                    (root / "web" / "styles.css").write_bytes(b"x" * 65_537)
                else:
                    (root / "tests" / "fixtures" / "views" / "digest.json").write_bytes(
                        replace(fixture(), kind="live").to_json()
                    )
                with patch.object(builder, "ROOT", root), self.assertRaises(ContractError):
                    builder.build_fixture("digest")
                self.assertFalse((root / ".local" / "fixture-sites" / "digest").exists())

    def test_invalid_case_and_symlinked_ancestry_or_destination_are_refused(self):
        for part in (".local", ".local/fixture-sites", ".local/fixture-sites/digest"):
            with self.subTest(part=part), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.prepare(root)
                link = root / part
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(root / "missing-target", target_is_directory=True)
                with patch.object(builder, "ROOT", root), self.assertRaises(ContractError):
                    builder.build_fixture("digest")
                self.assertTrue(link.is_symlink())
                self.assertFalse((root / "missing-target").exists())
        with self.assertRaisesRegex(ContractError, "unknown case"):
            builder.build_fixture("../../private-marker")

    def test_render_and_staging_failures_leave_no_destination_or_partial_files(self):
        for stage in ("render", "write", "rename"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.prepare(root)
                original_write = Path.write_bytes

                def fail_stylesheet(path, content, write=original_write):
                    if path.name == "styles.css":
                        raise OSError("injected second-file failure")
                    return write(path, content)

                if stage == "render":
                    failure = patch.object(
                        builder, "render_digest", side_effect=ContractError("render: rejected")
                    )
                elif stage == "write":
                    failure = patch.object(Path, "write_bytes", new=fail_stylesheet)
                else:
                    failure = patch.object(
                        Path, "rename", side_effect=OSError("injected rename failure")
                    )
                with (
                    patch.object(builder, "ROOT", root),
                    failure,
                    self.assertRaises((ContractError, OSError)),
                ):
                    builder.build_fixture("digest")
                parent = root / ".local" / "fixture-sites"
                self.assertFalse((parent / "digest").exists())
                if parent.exists():
                    self.assertEqual(list(parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
