# Bounded feed HTTP boundary (T03.01)

## Scope and approval

`wrap_brief.ingest.http.fetch_feed(source, checkpoint, *, policy, observed_at, ...)` requests exactly one source. It does not parse XML, activate sources, write state/checkpoints, run a scheduler or publish artifacts. The registry remains empty. All validation uses hand-authored transport cases and fake DNS/sockets; no publisher request is part of tests or delivery evidence.

Fetching requires an enabled, approved `Source` with non-future dated evidence and an explicit `RequestPolicy(reference, reviewed_at, minimum_interval_seconds)`. References must satisfy the public-reference contract. This caller-supplied policy is a reviewed configuration boundary, not inferred permission or an independent proof of licensing. Intervals are positive integer seconds, at most seven days. A source-matching `PollCheckpoint` supplies the previous attempt and validated conditional headers. `checkpoint=None` explicitly represents a first poll; callers must not discard prior attempt state to bypass spacing.

The supplied UTC observation clock determines approval/scheduling checks. Monotonic clock, sleep, jitter and single-hop transport are injectable for deterministic offline tests. Production defaults use monotonic time, sleep and bounded random jitter. Custom transports/clocks are trusted infrastructure, not feed-controlled callbacks. Programmer contract errors fail explicitly rather than becoming fabricated successful polls.

This client is serial: one subprocess/request at a time per call, no concurrent batch API. Callers must serialize per-source polls and enforce the eventual pipeline-wide concurrency ceiling. Production scheduling, private durable attempt/backoff state and source permission activation remain separate gates; this component alone does not satisfy them.

## Destination and TLS boundary

- Strict absolute ASCII HTTPS URLs, port 443, no userinfo, literal fragment delimiter, secret-bearing query keys, controls or unexpected hosts. Meaningful path/query spelling is retained.
- Each redirect is rejoined and revalidated. A literal `#`, including an empty fragment, is rejected before URL joining can erase it. Loops, missing Location and a fourth redirect fail closed.
- The worker resolves a maximum of 32 DNS answers and rejects the whole destination if **any** answer is non-global, multicast, unspecified, IPv4-mapped IPv6, 6to4/Teredo transition space, the Azure platform virtual address, or an unsupported address family. Mixed public/private answers never reach connect. This conservative address policy does not replace source-host approval or a production egress firewall.
- Connect directly to one selected numeric address using `socket.socket.connect`, never a second hostname lookup. Verify the connected peer matches that address. No DNS fallback/re-resolution is performed inside a hop.
- `ssl.create_default_context()` retains normal certificate/hostname verification, with original hostname as TLS SNI and HTTP Host. Certificate failures are not retried. No TLS/host verification bypass exists.
- No environmental proxy handling, cookie jar, credentials or authorization forwarding. A fixed public repository-based bot identity is supplied. Conditional validators never cross a redirect resource boundary, even on the same host.

## Isolation and resource bounds

The default transport invokes the installed trusted worker using `sys.executable -I -m wrap_brief.ingest._http_worker`. Fixed arguments, bounded JSON stdin and a minimal environment exclude inherited credentials, proxies and Python injection variables. Worker stderr is discarded; only fixed failure codes or bounded selected response metadata/body leave the worker.

One worker performs DNS, TCP, TLS, response headers and streaming body. The parent enforces a maximum **15-second hop timeout** within a **60-second overall operation budget**; timeout/cancellation kills and reaps the worker in `finally`. Socket timeouts and monotonic streaming checks are defense-in-depth. OS process creation, kill and reap are not strictly interruptible, so these are not an exact hard return-time guarantee under OS failure. This is timeout isolation, **not an OS filesystem/network sandbox**. Captured stdout is bounded by trusted worker code (≤3,000,000 bytes) and checked again by the parent; `communicate` itself is not a hostile-output limiter.

Body caps are independently **2 MiB encoded HTTP entity bytes** and **2 MiB decoded bytes**. “Encoded” excludes TLS/TCP and HTTP chunk framing; it is not a total-on-wire-byte claim. Accept identity or a single gzip stream only. Incremental gzip output is bounded on every decompress call; overflow, incomplete trailers, malformed data, concatenated members and trailing data fail. The stdlib handles chunk framing; inconsistent content length, duplicate headers and conflicting Transfer-Encoding/Content-Length are rejected. Header metadata is limited to 100 pairs/32,768 characters and bounded name/value lengths after the stdlib's own finite line/count parsing. Non-200 bodies are closed without draining. Only ETag, Last-Modified, Location and Retry-After are returned from the worker; cookie or arbitrary raw headers are not returned.

## Shared retry, redirect and spacing budget

- At most **five total hop attempts**, **three redirects** and **one transient retry** for the complete fetch. Redirects/retries never reset counters or the monotonic deadline.
- Respect reviewed spacing before redirects as well as retries. If a delay cannot fit in the remaining operation budget, return a deferred result instead of requesting early.
- Retry only timeouts/network failures and HTTP 429/500/502/503/504. TLS/destination/header/encoding/size/protocol failures and other statuses do not retry.
- Delay is at least the reviewed interval, one second plus injected jitter in [0,1], and any valid Retry-After numeric delay or aware HTTP date. Do not cap a publisher delay downward.
- A final transient response still preserves its Retry-After after retry/request exhaustion. A finite delay is returned as `retry_after_seconds`; invalid/unrepresentable server delay returns `deferred` with no numeric delay, requiring caller/operator review rather than automatic immediate rescheduling. All callers must persist/honor deferred state and source request policies before another poll.

## Results and state separation

`FetchResult` has fixed statuses `ok`, `not_modified`, `deferred` or `error`, a hop count, a fixed code where applicable, bounded body candidates and optional validated ETag/Last-Modified/backoff. Reprs omit raw fields. Response error text, URLs, arbitrary headers and tracebacks are not emitted by the worker.

HTTP 200 returns bytes for the separate safe parser/normalizer, **not** a successful stored feed checkpoint. HTTP 304 is valid only after sending a conditional request and carries no body; it means unchanged, never an empty feed. The caller retains old records/count/window and prior validators when new values are absent, and commits success metadata only after the appropriate validation/unchanged path. Failures never mutate or erase last-good state. There is no state writer or cross-source orchestration in this API.

## Offline evidence

Tests cover approval and poll spacing with zero transport calls when ineligible; 304/validator boundaries; every redirect/destination; shared retry/backoff exhaustion; mixed/private/multicast/mapped DNS; numeric peer pinning and original TLS SNI/Host; certificate/timeout failures; exact body caps, gzip integrity and framing; header/protocol redaction; worker cancellation/kill/reap; and a real subprocess timeout using a sleeping, network-free child. A real stdlib HTTP parser consumes chunked gzip bytes over fake pinned TLS sockets, not a public service. Installed-wheel smoke starts the isolated worker with invalid bounded input, proving worker packaging without invoking DNS or network. These tests are component evidence, not live-source approval or a production network penetration test.
