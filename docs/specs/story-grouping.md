# Conservative offline story grouping, version 1

This heuristic stage groups validated Items, not raw metadata or article bodies. It has no I/O, state writes, new dependency, AI, source activation or quality certification. Real-pair accuracy measurement and manual split/merge overrides remain T05.03 before live release.

## Matching and bounds

Feature extraction uses NFC/casefolded alphanumeric words, unique salient tokens after a fixed stopword list, exact number/version strings, quoted entity phrases, event type and a conservative rumor signal. Event precedence is review → preview → delay → release-date → update → Direct presentation → announcement → business → other. Explicit confirmed input suppresses keyword-only rumor inference; words alone never create confirmation.

All pairs must agree on event type, rumor state, number/version and edition markers, and fall within 48 hours using publication or explicitly labeled first-seen fallback for matching only. Quoted entity phrases must be compatible. Non-identical canonical URLs require at least two salient tokens, a non-generic entity token and Jaccard similarity ≥0.85; unknown-event matches require identical salient sets. Canonical URI equality preserves every query field (no tracking cleanup shortcut) and never bypasses event/claim/time checks. This cannot override a source-specific stricter identity policy.

Deterministic time/ID processing uses complete-link placement: every member must match every other member. No transitive chaining. Inputs are bounded at 10,000 Items/previous clusters/evidence records; a bucket over 100 members fails rather than truncates. A day/event/rumor/numeric/edition index searches adjacent UTC days across the 48-hour boundary.

## Previous groups and IDs

Previous automatic clusters may contain expired members; absent members are ignored. Prior IDs must be unique and a current item cannot belong to multiple prior groups. Different prior groups never merge automatically. A new item compatible with multiple buckets remains a locked singleton instead of arbitrarily bridging groups.

Prior members that become incompatible split. Preserve the old ID for the partition containing its old lead; otherwise select greatest retained overlap, then the lexicographically smallest member tuple. Other/new groups receive deterministic versioned IDs with collision disambiguation; expired prior IDs are not silently recycled in that call. Manual-confidence prior groups are rejected until the separate override adapter is implemented.

## Lead evidence and derived fields

Callers must supply exactly one immutable `LeadEvidence` per current Item. It is trusted reviewed application input, never read from feed text: item ID, primary/original/coverage role, quality 0–100, and public evidence reference required for primary/original. Missing/duplicate/unknown evidence fails; unknown commercial fields are not accepted.

Only active/corrected Items can lead. Relevant primary evidence wins for announcement/release-date/delay/update/Direct events, then original reporting, then coverage; primary evidence is not privileged for reviews/analysis. Quality, known publication, latest timestamp and stable ID break ties. Commercial value never enters this API; editorial quality assessments must remain independent of commercial relationships.

Topic is the classified event type. Confidence is exact for a singleton or compatible common canonical URI, otherwise related. Claim is confirmed only from an eligible confirmed lead, rumor for a rumor/inferred-rumor lead, otherwise reported. With no eligible lead correction status is retracted; otherwise corrected if any retained member is corrected/retracted/removed, else none. All original Items, IDs and links remain unchanged, each in exactly one output group. No source is approved by grouping it.
