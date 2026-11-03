# ADR 0002 — policy copy without invented brand or licensing authority

Date: 2026-11-03. Status: **accepted partial documentation boundary; brand/license/live-contact decisions unresolved**. Tracking: [T01.04 issue #40](https://github.com/dmoliveira/wrap-brief/issues/40).

## Context and bounded evidence

Wrap Brief remains a working name for an independent, unofficial offline Nintendo-news prototype. No copied Nintendo branding/assets or publisher images are introduced. Existing README and contribution guidance expressly defer project licensing; no `LICENSE`/`COPYING` or inbound grant exists in reachable project history. The public maintainer's identity, repository control and an instruction to build the product do not establish every relevant copyright holder's grant authority.

Read-only public metadata on 2026-11-03 reported no detected project license. [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains the distinction between public visibility, platform view/fork terms and adopting an open-source license. This is guidance, not a rights-holder decision. No license text, copyright identity, contributor agreement, metadata declaration or grant is added by this ADR.

A bounded web query, `"Wrap Brief" news newsletter brand`, returned mixed naming/phrase results, not authoritative clearance evidence. No conclusion about absence of conflicts follows. The [WIPO Global Brand Database overview](https://www.wipo.int/en/web/global-brand-database) was reviewed; it describes its coverage and recommends considering national/regional registers. No completed registry search, selected territory/services/class scope, domain availability or domain ownership is asserted. Search-engine results, an available domain or an unofficial disclaimer would not alone establish trademark clearance. No purchase, registration or external contact was performed.

The repository's private vulnerability route is security-only. No confidential non-security editorial/rights route was found, and it must not be invented or silently repurposed. No live host/log-retention configuration exists. [GitHub's privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement), effective April 27, 2026 when reviewed, describes service usage data including IP addresses and cookies; application-level no-tracking is not a promise about GitHub or external websites.

## Decision

Ship [accurate repository-readable policy copy](../../content/policies/README.md) for the **current offline prototype**, including the intended no-tracking pilot constraints. Keep present behavior, future obligations and unavailable reporting facilities explicit. Do not claim an operating pilot, integrated policy navigation, source approval, legal compliance or brand clearance.

Leave `LICENSE`, contribution terms, package licensing metadata, renderer/web assets and deployment untouched. A future license must state its authorized project-code scope and exclude publisher content/trademarks/third-party assets. Existing platform terms are not rewritten. Writing policy text completes only the bounded copy subtask after review; it does not satisfy the parent task or downstream implementation gates.

## Exact remaining decisions

| Gate | Evidence missing | Required next action |
| --- | --- | --- |
| Name/domain/trademark | Intended launch territory/services and domain plan; dated relevant conflict checks and reviewed disposition | Define that scope, perform bounded authoritative/common-law checks as appropriate, then record a supported name decision or rename before launch. Do not infer clearance from a web search. A paid domain is optional, not a prerequisite for writing copy. |
| Project license/contributions | Explicit decision by authorized rights holder(s), authorized code scope and inbound terms | Establish grant authority and record the selected license and contribution terms; only then add exact license text/metadata. No private legal identity or correspondence belongs in Git. |
| Live privacy/editorial contact | Owner-approved suitable confidential non-security channel and actual host/log/retention facts | Establish and verify that route/configuration, update reader notice before launch, and keep sensitive reports out of public issues. No invented SLA, retention period, provider or legal basis. |

T01.04.1/.2 and the parent remain blocked with empty parent completion fields; issue #40 stays open. T02.02 and T06.03 remain dependency-gated. This ADR activates no source, account, domain, hosting, tracking, payment, advertising or disabled future scope. It is not legal advice or a clearance opinion.

## Validation and reversal

Use configured plan/link/publication checks, standalone planning tests, whitespace checks and one focused policy/authority review. `policy-copy-review` concerns the accuracy of this limited copy; `brand-license-review` remains blocked, not a passing label for absent legal decisions. Reversal is a reviewed documentation PR revert; it must not imply that unconfigured channels or ungranted rights became available.
