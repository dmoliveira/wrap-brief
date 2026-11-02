from __future__ import annotations

import socket
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fixtures.support import read_json

from wrap_brief.config import SourceRegistry
from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.models import Cluster, ContractError, Item
from wrap_brief.state.local import LocalState
from wrap_brief.state.snapshot import Snapshot

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)
SOURCES = SourceRegistry.from_dict(read_json("sources.json")).sources
DOMAINS = {"demo-a": "example.com", "demo-b": "example.org", "demo-c": "example.net"}


def item(id, title="Fictional console update announced", source="demo-a", **changes):
    values = dict(
        id=id,
        source_id=source,
        title=title,
        url="https://" + DOMAINS[source] + "/news/" + id,
        first_seen_at=NOW,
        last_seen_at=NOW,
        published_at=NOW,
    )
    values.update(changes)
    return Item(**values)


def evidence(items, **overrides):
    return tuple(overrides.get(i.id, LeadEvidence(i.id)) for i in items)


def groups(items, previous=(), policies=None):
    return group_items(
        items,
        SOURCES,
        previous_clusters=previous,
        lead_evidence=evidence(items) if policies is None else policies,
    )


class StoryTests(unittest.TestCase):
    def test_lead_quality_known_time_recency_and_id_ties_are_isolated(self):
        cases = [
            (
                (item("a"), item("b", published_at=NOW - timedelta(hours=1))),
                (LeadEvidence("a", quality=10), LeadEvidence("b", quality=20)),
                "b",
            ),
            (
                (
                    item(
                        "a",
                        published_at=None,
                        first_seen_at=NOW + timedelta(hours=1),
                        last_seen_at=NOW + timedelta(hours=1),
                    ),
                    item("b", published_at=NOW - timedelta(hours=1)),
                ),
                (LeadEvidence("a"), LeadEvidence("b")),
                "b",
            ),
            (
                (item("a"), item("b", published_at=NOW + timedelta(minutes=1))),
                (LeadEvidence("a"), LeadEvidence("b")),
                "b",
            ),
            ((item("b"), item("a")), (LeadEvidence("b"), LeadEvidence("a")), "a"),
        ]
        for items, policies, expected in cases:
            with self.subTest(expected=expected, items=[i.id for i in items]):
                self.assertEqual(groups(items, policies=policies)[0].lead_id, expected)

    def test_missing_prior_lead_split_prefers_overlap_then_lexical_members(self):
        previous = (Cluster("prior", ("expired-lead", "a", "b", "c"), "expired-lead"),)
        items = (item("a", "Fictional console review"), item("b"), item("c", source="demo-c"))
        result = groups(items, previous)
        self.assertEqual(next(g for g in result if g.id == "prior").member_ids, ("b", "c"))
        tied = (Cluster("prior", ("expired-lead", "a", "b"), "expired-lead"),)
        items = (
            item("b", published_at=NOW - timedelta(hours=1)),
            item("a", "Fictional console review"),
        )
        result = groups(items, tied)
        self.assertEqual(next(g for g in result if g.id == "prior").member_ids, ("a",))

    def test_grouped_complete_snapshot_can_commit_reload_and_regroup_stably(self):
        value = Snapshot.from_dict(read_json("views/digest.json"))
        auto = group_items(value.items, value.sources, lead_evidence=evidence(value.items))
        complete = replace(value, clusters=auto)
        with tempfile.TemporaryDirectory() as directory:
            state = LocalState(Path(directory) / "synthetic.sqlite3")
            state.commit(complete, expected_revision=0)
            restored = state.load().snapshot
        regrouped = group_items(
            restored.items,
            restored.sources,
            lead_evidence=evidence(restored.items),
            previous_clusters=restored.clusters,
        )
        self.assertEqual(regrouped, auto)
        self.assertEqual(complete, restored)

    def test_exact_uri_shortcut_cannot_override_source_specific_query_identity(self):
        a = item(
            "resource-a", "Fictional update", url="https://example.com/a?utm_source=resource-one"
        )
        b = item(
            "resource-b", "Fictional update", url="https://example.com/a?utm_source=resource-two"
        )
        self.assertEqual(len(groups((a, b))), 2)

    def test_related_coverage_has_all_sources_and_deterministic_partition(self):
        items = tuple(item("update-" + suffix, source="demo-" + suffix) for suffix in "abc")
        before = [i.to_dict() for i in items]
        result = groups(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(set(result[0].member_ids), {i.id for i in items})
        self.assertEqual(result, groups(tuple(reversed(items))))
        self.assertEqual([i.to_dict() for i in items], before)
        self.assertEqual(result[0].confidence, "related")
        self.assertEqual(result[0].topic, "update")

    def test_reviews_previews_release_updates_and_delays_remain_distinct(self):
        titles = [
            "Fictional Hero review",
            "Fictional Hero preview",
            "Fictional Hero release date announced",
            "Fictional Hero update announced",
            "Fictional Hero delayed",
        ]
        result = groups(tuple(item("event-" + str(n), title) for n, title in enumerate(titles)))
        self.assertEqual(len(result), len(titles))

    def test_direct_multi_announcements_and_quoted_games_do_not_collapse(self):
        titles = [
            '"Fictional Hero" announced at Direct',
            '"Fictional World" announced at Direct',
            "Fictional Direct presentation scheduled",
            '"Fictional Hero Two" announced at Direct',
        ]
        self.assertEqual(
            len(groups(tuple(item("direct-" + str(n), title) for n, title in enumerate(titles)))), 4
        )
        same = (
            item("quoted", '"Fictional Hero" announced'),
            item("plain", "Fictional Hero announced", source="demo-b"),
        )
        self.assertEqual(len(groups(same)), 1)

    def test_numbers_patch_versions_and_editions_are_protected(self):
        for a, b in (
            ("Fictional Hero 2 announced", "Fictional Hero 3 announced"),
            ("Fictional console update 1.2.3", "Fictional console update 1.2.4"),
            ("Fictional Hero deluxe announced", "Fictional Hero standard announced"),
        ):
            with self.subTest(a=a):
                self.assertEqual(len(groups((item("a", a), item("b", b)))), 2)

    def test_rumor_and_confirmation_are_separate_and_never_inferred_confirmed(self):
        rumors = (
            item("rumor-a", "Fictional Hero rumor announced"),
            item("rumor-b", "Fictional Hero rumor announced", source="demo-b"),
        )
        self.assertEqual(groups(rumors)[0].claim_status, "rumor")
        confirmed = item(
            "confirmed", "Fictional Hero rumor announced", source="demo-c", claim_status="confirmed"
        )
        self.assertEqual(len(groups((*rumors, confirmed))), 2)
        self.assertEqual(
            groups((item("official", "Fictional official console update"),))[0].claim_status,
            "reported",
        )

    def test_window_boundary_and_unknown_date_fallback_are_explicit(self):
        a = item("a", published_at=None)
        b = item(
            "b",
            published_at=None,
            first_seen_at=NOW + timedelta(hours=48),
            last_seen_at=NOW + timedelta(hours=48),
        )
        self.assertEqual(len(groups((a, b))), 1)
        c = replace(
            b,
            id="c",
            first_seen_at=b.first_seen_at + timedelta(microseconds=1),
            last_seen_at=b.last_seen_at + timedelta(microseconds=1),
        )
        self.assertEqual(len(groups((a, c))), 2)
        self.assertIsNone(a.published_at)

    def test_complete_link_does_not_chain_weak_endpoints(self):
        base = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        a = item("a", base + " announced")
        b = item("b", base + " lambda announced", published_at=NOW + timedelta(minutes=1))
        c = item("c", base + " lambda mu announced", published_at=NOW + timedelta(minutes=2))
        result = groups((a, b, c))
        self.assertEqual(len(result), 2)
        self.assertFalse(any({"a", "c"} <= set(group.member_ids) for group in result))

    def test_generic_or_uncertain_titles_do_not_merge(self):
        self.assertEqual(
            len(
                groups(
                    (item("a", "Nintendo Direct announced"), item("b", "Nintendo Direct announced"))
                )
            ),
            2,
        )
        self.assertEqual(
            len(
                groups(
                    (
                        item("a", "Fictional Hero price revealed"),
                        item("b", "Fictional Hero release date revealed"),
                    )
                )
            ),
            2,
        )

    def test_previous_ids_survive_new_earlier_coverage_and_lead_change(self):
        original = (item("b", source="demo-b"), item("c", source="demo-c"))
        previous = groups(original)
        new = item("a", source="demo-a", published_at=NOW - timedelta(hours=1))
        current = (new, *original)
        policies = evidence(
            current, a=LeadEvidence("a", "primary", 50, "https://example.com/evidence")
        )
        result = groups(current, previous, policies)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, previous[0].id)
        self.assertEqual(result[0].lead_id, "a")

    def test_ambiguous_bridge_does_not_merge_prior_groups(self):
        base = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        a = item("a", base + " announced")
        c = item("c", base + " lambda mu announced")
        previous = (Cluster("prior-a", ("a",), "a"), Cluster("prior-c", ("c",), "c"))
        b = item("b", base + " lambda announced")
        result = groups((a, b, c), previous)
        self.assertEqual(len(result), 3)
        self.assertTrue(any(group.member_ids == ("b",) for group in result))
        self.assertEqual(
            {g.id for g in result if g.id.startswith("prior-")}, {"prior-a", "prior-c"}
        )

    def test_prior_split_keeps_old_lead_partition_and_expiry_is_normal(self):
        a, b = item("a"), item("b", source="demo-b")
        previous = groups((a, b))
        old_lead = previous[0].lead_id
        changed = tuple(
            replace(i, title="Fictional console review") if i.id == old_lead else i for i in (a, b)
        )
        split = groups(changed, previous)
        self.assertEqual(len(split), 2)
        self.assertEqual(next(g.id for g in split if old_lead in g.member_ids), previous[0].id)
        retained = groups((a,), previous)
        self.assertEqual(retained[0].id, previous[0].id)

    def test_expired_id_collision_gets_deterministic_new_id(self):
        a = item("a")
        first = groups((a,))[0]
        expired = Cluster(first.id, ("expired",), "expired")
        new = groups((a,), (expired,))[0]
        self.assertNotEqual(new.id, expired.id)
        self.assertEqual(new, groups((a,), (expired,))[0])

    def test_invalid_previous_membership_and_manual_overrides_are_not_silently_applied(self):
        a = item("a")
        invalid = [
            (Cluster("same", ("a",), "a"), Cluster("same", ("a",), "a")),
            (Cluster("one", ("a",), "a"), Cluster("two", ("a",), "a")),
            (Cluster("manual", ("a",), "a", confidence="manual", override_ref="docs/override.md"),),
        ]
        for previous in invalid:
            with self.assertRaises(ContractError):
                groups((a,), previous)

    def test_primary_original_quality_and_dates_have_transparent_priority(self):
        items = (item("a"), item("b", source="demo-b"), item("c", source="demo-c"))
        policies = evidence(
            items,
            a=LeadEvidence("a", "coverage", 100),
            b=LeadEvidence("b", "original", 10, "https://example.org/proof"),
            c=LeadEvidence("c", "primary", 0, "https://example.net/proof"),
        )
        self.assertEqual(groups(items, policies=policies)[0].lead_id, "c")
        reviews = tuple(replace(i, title="Fictional console review") for i in items)
        self.assertEqual(groups(reviews, policies=policies)[0].lead_id, "b")

    def test_unavailable_members_never_lead_and_corrections_are_visible(self):
        a = item("a", status="retracted")
        b = item("b", source="demo-b", status="corrected")
        result = groups((a, b))[0]
        self.assertEqual(result.lead_id, "b")
        self.assertEqual(result.correction_status, "corrected")
        withdrawn = groups((a, replace(b, status="removed")))[0]
        self.assertIsNone(withdrawn.lead_id)
        self.assertEqual(withdrawn.correction_status, "retracted")

    def test_evidence_is_complete_bounded_and_cannot_accept_commerce(self):
        a = item("a")
        for policies in ((), (LeadEvidence("a"), LeadEvidence("a")), (LeadEvidence("unknown"),)):
            with self.assertRaises(ContractError):
                groups((a,), policies=policies)
        for values in (
            ("primary", 0, None),
            ("other", 0, None),
            ("coverage", True, None),
            ("coverage", 101, None),
            ("primary", 1, "../private"),
        ):
            with self.assertRaises(ContractError):
                LeadEvidence("a", *values)
        with self.assertRaises(TypeError):
            LeadEvidence("a", commission=100)

    def test_input_and_member_overflow_fail_without_truncating(self):
        many = tuple(item("entry-" + str(n)) for n in range(101))
        with self.assertRaises(ContractError):
            groups(many)
        with self.assertRaises(ContractError):
            group_items((item("a"),) * 10001, SOURCES, lead_evidence=())

    def test_fixture_partition_is_offline_complete_and_items_unchanged(self):
        value = read_json("views/digest.json")
        items = tuple(Item.from_dict(v) for v in value["items"])
        before = [i.to_dict() for i in items]
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")):
            result = groups(items)
        flattened = [id for group in result for id in group.member_ids]
        self.assertCountEqual(flattened, [i.id for i in items])
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(before, [i.to_dict() for i in items])
        self.assertEqual(len(result), 3)
        self.assertEqual(groups(()), ())


if __name__ == "__main__":
    unittest.main()
