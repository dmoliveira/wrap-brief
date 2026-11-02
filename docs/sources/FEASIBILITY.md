# T02.04 — pilot-source feasibility

Reviewed: 2026-11-02. **Gate: blocked for the proposed public feed-metadata archive. Approved/enabled sources: zero.** This is an operational decision under the project's source policy, not legal advice or a finding that ordinary linking or every headline reuse is unlawful.

## Intended use

Daily conditional requests; display a permitted title, canonical link, publisher, and timestamp. No article bodies, descriptions, images, automatic rewriting, ads, or paid services. The proposed state branch retains complete normalized metadata, with a 90-day live window but effectively permanent public Git history. That archival distinction must be included in source approval.

## Reviewed candidates

| Candidate | Technical evidence | Permission evidence and unresolved question | Current disposition |
| --- | --- | --- | --- |
| Nintendo Life | [Official RSS endpoint](https://www.nintendolife.com/feeds/latest); bounded HEAD check returned HTTP 200 and RSS content type | [Terms, Copyright section](https://www.nintendolife.com/terms#copyright) limits ordinary reproduction to personal/noncommercial uses and restricts redistribution or storage in another website/retrieval system without express written permission. No project-specific permission or feed-specific exception is recorded. | Not cleared; obtain permission or a documented applicable basis covering the exact metadata/archive use. |
| Gematsu | [Official RSS endpoint](https://www.gematsu.com/feed); bounded HEAD check returned HTTP 200 and RSS content type | A [privacy policy](https://www.gematsu.com/privacy) is available, but it is not a syndication/reuse license. The bounded review did not establish permission for the proposed republication and permanent public history. A guessed terms URL returning 404 is not evidence that no terms exist. | Not cleared; locate authoritative reuse terms or obtain publisher clarification. |
| VGC | [Official RSS endpoint](https://www.videogameschronicle.com/feed/); bounded HEAD check returned HTTP 200 and XML content type | The bounded review of the [publisher's public site](https://www.videogameschronicle.com/) and a candidate terms path did not establish a compatible syndication/archive permission. This is an evidence gap, not a blanket prohibition. | Not cleared; locate authoritative reuse terms or obtain publisher clarification. |

Research confirmed feed availability separately from these HEAD checks; neither technical result grants reuse rights. Feeds can contain descriptions/images beyond the intended fields. No feed content was committed, no source registry was enabled, and no scheduled collector exists.

## Decision and implementation boundary

- The three-candidate inventory is complete; **a viable approved source set is not established**. T02.04 remains blocked, not done. A written no-go report must not accidentally unlock downstream contracts/prototype tasks.
- T01.02's independent Python foundation is implemented. T02.01 and dependent data/UI work remain behind the existing feasibility gate; this report does not silently lower it.
- Final approval/onboarding still belongs to T02.02. This memo does not enable a publisher or authorize commercial use.
- Public Git file deletion does not erase history. A shorter live retention setting alone cannot satisfy a publisher's erasure/archive restriction.

## Exact next actions

1. Find a viable complementary set with explicit compatible feed/metadata licensing, or obtain publisher clarification/permission. Record a public-safe scope and date; keep correspondence, account details, and private contacts out of Git.
2. Resolve permitted fields, attribution, polling limits, commercial/donation restrictions, retention, removal, and **public Git-history permanence**. Approval for a noncommercial pilot does not automatically permit later monetization.
3. If otherwise suitable sources cannot permit permanent public history, review a different state-storage design **before collection**. Introduce a focused MVP blocker-resolution task if needed; do not prematurely activate the post-launch migration roadmap.
4. Re-review this gate against the actual evidence. Only then mark T02.04 done, begin dependent contracts/fixtures, and complete final source approval before live collection.

This review did not exhaust all gaming publishers or licensed press channels. Additional bounded source research is a valid next action; absence of permission in this candidate set is not proof that the whole product is infeasible. Do not send automated approval requests or publish a manual-link workaround without reviewing its actual rights and scope.
