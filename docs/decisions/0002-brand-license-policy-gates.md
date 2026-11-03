# ADR 0002 — policy copy, code licensing and remaining launch gates

Date: 2026-11-03. Status: **updated: MIT code licensing authorized; brand and live-contact gates remain unresolved**. Tracking: [T01.04 issue #40](https://github.com/dmoliveira/wrap-brief/issues/40).

## Context and bounded evidence

Wrap Brief remains a working name for an independent, unofficial offline Nintendo-news prototype. No copied Nintendo branding/assets or publisher images are introduced. At the initial policy-copy decision, README and contribution guidance deferred project licensing, and no `LICENSE`/`COPYING` or inbound grant existed in reachable project history. The public maintainer's identity, repository control and an instruction to build the product did not establish every relevant copyright holder's grant authority.

Read-only public metadata at that time reported no detected project license. [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains the distinction between public visibility, platform view/fork terms and adopting an open-source license. This is guidance, not a rights-holder decision. The subsequent authorization and implementation are recorded below.

The initial bounded web query, `"Wrap Brief" news newsletter brand`, returned mixed naming/phrase results, not authoritative clearance evidence. No conclusion about absence of conflicts follows. The [WIPO Global Brand Database overview](https://www.wipo.int/en/web/global-brand-database) was reviewed; it describes its coverage and recommends considering national/regional registers. At that initial point no territory/services/class scope or completed registry search had been selected or recorded. Search-engine results, an available domain or an unofficial disclaimer would not alone establish trademark clearance. No purchase, registration or external contact was performed.

The repository's private vulnerability route is security-only. No confidential non-security editorial/rights route was found, and it must not be invented or silently repurposed. No live host/log-retention configuration exists. [GitHub's privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement), effective April 27, 2026 when reviewed, describes service usage data including IP addresses and cookies; application-level no-tracking is not a promise about GitHub or external websites.

## Decision

Ship [accurate repository-readable policy copy](../../content/policies/README.md) for the **current offline prototype**, including the intended no-tracking pilot constraints. Keep present behavior, future obligations and unavailable reporting facilities explicit. Do not claim an operating pilot, integrated policy navigation, source approval, legal compliance or brand clearance.

The original policy-copy slice left `LICENSE`, contribution terms, package metadata, renderer/web assets and deployment untouched. Existing platform terms were not rewritten. Writing policy text completed only the bounded copy subtask after review; it did not satisfy the parent task or downstream implementation gates.

## Subsequent authorized license decision

On 2026-11-03 the user selected MIT for project-owned code and future contributions, explicitly confirming authority from the relevant rights holders. The user separately authorized the public collective notice `Copyright (c) 2026 Wrap Brief contributors` and MIT coverage for project-owned documentation distributed with the code, including the README. The collective notice does not imply copyright assignment. The [license](../../LICENSE) and [contribution guidance](../../CONTRIBUTING.md) implement that decision; contributors must have authority to license their submissions under MIT.

The grant does not itself cover other existing non-distributed documentation or non-code fixtures. It does not relicense publisher content, trademarks, third-party assets or separately licensed dependencies. `defusedxml` is a separately installed dependency under its own license, not vendored project code. The package's MIT metadata is limited to its built distribution archives; their code, README and bundled license are verified separately. This decision is not source permission, brand clearance or legal advice.

The user also selected the United States as the initial territory for name research. A further preliminary web search found [TheWrap](https://www.thewrap.com/about-us/), an entertainment-and-media news publisher with a partially overlapping name. This is a lead for review, not a finding of infringement or a conclusion about its trademark rights.

On 2026-11-03 at 05:44–05:46 UTC, a read-only session used the official [USPTO Trademark Search](https://tmsearch.uspto.gov/) interface. It displayed “No results found” for combined-mark queries `CM:"wrap brief"` and `CM:wrapbrief`, and “62 results” for `CM:"the wrap"`. No status or class filter was deliberately selected, but the interface's default live/dead scope could not be verified; no individual mark's status, goods or services were established. The result count is not a count of conflicts. These limited searches do not replace reviewing relevant results, variant, state and common-law checks or a supported name decision.

At 05:56 UTC the same day, an exploratory registration-data lookup for the **unselected** candidates `wrapbrief.com` and `wrapbrief.net` used the [IANA RDAP bootstrap](https://data.iana.org/rdap/dns.json) to identify Verisign's respective registry endpoints. The `.com` query returned HTTP 200 with a matching domain object; the `.net` query returned HTTP 404 with an empty response. No registrant information was recorded. A 404 is not proof of availability or eligibility to register, and neither result establishes ownership or trademark rights. No domain has been selected or purchased, and no clearance is asserted. See [ICANN's lookup guidance](https://lookup.icann.org/en/faq) for the limits of registration data.

## Exact remaining decisions

| Gate | Evidence missing | Required next action |
| --- | --- | --- |
| Name/domain/trademark | U.S. is the initial territory; a domain plan, relevant official/common-law checks and reviewed disposition remain missing | Define the remaining services/domain scope, complete appropriately scoped checks, then record a supported name decision or rename before launch. Do not infer clearance from a web search. A paid domain is optional. |
| Project license/contributions | MIT grant and public collective notice explicitly authorized as described above | Verify the exact license text, inbound terms and built package metadata; keep external content and independently licensed dependencies separate. No private legal identity or correspondence belongs in Git. |
| Live privacy/editorial contact | Owner-approved suitable confidential non-security channel and actual host/log/retention facts | Establish and verify that route/configuration, update reader notice before launch, and keep sensitive reports out of public issues. No invented SLA, retention period, provider or legal basis. |

T01.04.1 and the parent remain blocked with empty parent completion fields; issue #40 stays open. T02.02 and T06.03 remain dependency-gated. This ADR activates no source, account, domain, hosting, tracking, payment, advertising or disabled future scope. It is not legal advice or a clearance opinion.

## Validation and reversal

Use configured plan/link/publication checks, standalone planning tests, whitespace checks and a focused policy/authority review. The licensing increment additionally verifies lock consistency, build archives and wheel installation. `policy-copy-review` concerns the accuracy of the limited copy; the parent `brand-license-review` remains blocked, not a pass for absent brand evidence. A reviewed revert removes repository files but must not be represented as revoking previously granted MIT rights or as making unconfigured channels or source rights available.
