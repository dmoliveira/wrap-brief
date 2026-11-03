# T02.04 — pilot-source feasibility

Reviewed: 2026-11-02. **Current decision: prototype-only go; live-source approval blocked. Approved/enabled sources: zero.** [ADR 0001](../decisions/0001-fixtures-and-private-state.md) explicitly supersedes the former public-Git archive proposal. This is an operational decision, not legal advice or a finding that ordinary linking or every headline reuse is unlawful.

## Intended use

The eventual live design makes daily conditional requests and displays only permitted title/link/source/time fields. No article bodies, descriptions, images, automatic rewriting, ads or paid services are enabled. The initial permanent public state-branch design was rejected. Future live state must be private, deletable and source-retention-aware; public HTML/JSON and deployment artifacts still require approval. Offline M1 uses hand-authored synthetic data only.

## Reviewed candidates

| Candidate | Technical evidence | Permission evidence and unresolved question | Current disposition |
| --- | --- | --- | --- |
| Nintendo Life | [Official RSS endpoint](https://www.nintendolife.com/feeds/latest); bounded HEAD check returned HTTP 200 and RSS content type | [Terms, Copyright section](https://www.nintendolife.com/terms#copyright) limits ordinary reproduction to personal/noncommercial uses and restricts redistribution or storage in another website/retrieval system without express written permission. No project-specific permission or feed-specific exception is recorded. | Not cleared; obtain permission or a documented applicable basis covering the exact metadata/archive use. |
| Gematsu | [Official RSS endpoint](https://www.gematsu.com/feed); bounded HEAD check returned HTTP 200 and RSS content type | A [privacy policy](https://www.gematsu.com/privacy) is available, but it is not a syndication/reuse license. The bounded review did not establish permission for the proposed public output and retention scope. A guessed terms URL returning 404 is not evidence that no terms exist. | Not cleared; locate authoritative reuse terms or obtain publisher clarification. |
| VGC | [Official RSS endpoint](https://www.videogameschronicle.com/feed/); bounded HEAD check returned HTTP 200 and XML content type | The bounded review of the [publisher's public site](https://www.videogameschronicle.com/) and a candidate terms path did not establish a compatible syndication/archive permission. This is an evidence gap, not a blanket prohibition. | Not cleared; locate authoritative reuse terms or obtain publisher clarification. |

Research confirmed feed availability separately from these HEAD checks; neither technical result grants reuse rights. Feeds can contain descriptions/images beyond the intended fields. No feed content was committed, no source registry was enabled, and no scheduled collector exists.

## Decision and implementation boundary

- The three-candidate investigation is complete; **a viable approved live source set is not established**. T02.04 now records a reviewed, explicitly limited synthetic-prototype go. This is not a publisher approval or an accidental no-go-to-live transition.
- T02.01 and M1 may proceed offline under ADR 0001. T02.02 is the blocked live-source gate, and T07.02 cannot collect real data until that approval and private durable persistence are ready.
- Final approval/onboarding still belongs to T02.02. This memo does not enable a publisher or authorize commercial use.
- Public Git file deletion does not erase history. A shorter live retention setting alone cannot satisfy a publisher's erasure/archive restriction.

## Exact next actions

1. Find a viable complementary set with explicit compatible feed/metadata licensing, or obtain publisher clarification/permission. Record a public-safe scope and date; keep correspondence, account details, and private contacts out of Git.
2. Resolve permitted fields, attribution, polling limits, commercial/donation restrictions, private retention/deletion, public HTML/JSON/RSS, deployment artifacts, and owned cache/mirror removal. Approval for a noncommercial pilot does not automatically permit later monetization.
3. T04.02 must prove private/deletable durable persistence before live collection; the ADR removes the public-history requirement, but it does not grant content rights or choose/provision a provider.
4. Re-review source evidence and clear T02.02 before any live collection/publication. Synthetic-only contracts/fixtures may proceed independently; no candidate from this table is enabled by completing the research task.

This review did not exhaust all gaming publishers or licensed press channels. Additional bounded source research is a valid next action; absence of permission in this candidate set is not proof that the whole product is infeasible. Do not send automated approval requests or publish a manual-link workaround without reviewing its actual rights and scope.

A [2026-11-03 policy-only follow-up](CANDIDATE-RIGHTS-2026-11.md) records conditional IGN linking/feed guidance and several Creative Commons candidates with important unresolved endpoint, attribution, retention and commercial limitations. This additional research approves or enables **zero** sources and does not change the prototype-only decision above.
