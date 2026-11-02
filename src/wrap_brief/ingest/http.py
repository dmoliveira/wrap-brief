"""Bounded one-source feed requests. No scheduling, parsing or checkpoint writes."""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import time
from base64 import b64decode
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

from wrap_brief.models import (
    ContractError,
    Source,
    _check,
    _host,
    _reference,
    _text,
    _utc,
    validate_https_url,
)
from wrap_brief.state.snapshot import PollCheckpoint

MAX_BODY = 2_097_152
MAX_PROTOCOL = 3_000_000
MAX_REQUESTS = 5
MAX_REDIRECTS = 3
TOTAL_SECONDS = 60.0
HOP_SECONDS = 15.0
USER_AGENT = "WrapBrief/0.1 (+https://github.com/dmoliveira/wrap-brief)"
ERRORS = frozenset(
    {"destination", "tls", "timeout", "network", "headers", "encoding", "size", "protocol"}
)


@dataclass(frozen=True, slots=True)
class RequestPolicy:
    """Caller-reviewed source request spacing; not a source-approval substitute."""

    reference: str
    reviewed_at: datetime
    minimum_interval_seconds: int

    def __post_init__(self) -> None:
        _reference(self.reference, "request_policy")
        object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        _check(
            type(self.minimum_interval_seconds) is int
            and 1 <= self.minimum_interval_seconds <= 604_800,
            "request_policy",
            "bounded positive request interval required",
        )


@dataclass(frozen=True, slots=True, repr=False)
class HopRequest:
    url: str
    allowed_hosts: tuple[str, ...]
    headers: tuple[tuple[str, str], ...]
    timeout: float


@dataclass(frozen=True, slots=True, repr=False)
class HopResponse:
    status: int
    headers: tuple[tuple[str, str], ...] = ()
    body: bytes = b""


@dataclass(frozen=True, slots=True, repr=False)
class FetchResult:
    status: str
    requests: int
    code: str | None = None
    body: bytes | None = None
    etag: str | None = None
    last_modified: str | None = None
    retry_after_seconds: float | None = None


class TransportError(Exception):
    def __init__(self, code: str):
        self.code = code if code in ERRORS else "protocol"
        super().__init__(self.code)


def destination(url: str, hosts: tuple[str, ...]) -> tuple[str, str]:
    validate_https_url(url)
    _check("#" not in url, "url", "fragment prohibited")
    parsed = urlsplit(url)
    host = _host(parsed.hostname, "url")
    _check(host in hosts, "url", "host outside source allowlist")
    # http.client sends ASCII request targets; Unicode must already be percent-encoded.
    try:
        url.encode("ascii")
    except UnicodeEncodeError:
        raise ContractError("url: ASCII URL required") from None
    target = parsed.path or "/"
    if "?" in url:
        target += "?" + parsed.query
    return host, target


def _headers(pairs: tuple[tuple[str, str], ...]) -> dict[str, str]:
    _check(type(pairs) is tuple and len(pairs) <= 100, "headers", "bounded header pairs required")
    result = {}
    total = 0
    for pair in pairs:
        _check(type(pair) is tuple and len(pair) == 2, "headers", "invalid pair")
        name, value = pair
        _text(name, "header_name", 100)
        _text(value, "header_value", 4096)
        total += len(name) + len(value)
        _check(total <= 32_768, "headers", "header limit")
        name = name.lower()
        _check(name not in result, "headers", "duplicate header")
        result[name] = value
    return result


def isolated_transport(request: HopRequest) -> HopResponse:
    """Run trusted installed worker. Timeout isolation, not an OS sandbox."""
    payload = json.dumps(
        {
            "url": request.url,
            "hosts": request.allowed_hosts,
            "headers": request.headers,
            "timeout": request.timeout,
        }
    ).encode()
    if len(payload) > 16_384:
        raise TransportError("protocol")
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ}
    environment.update({"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-m", "wrap_brief.ingest._http_worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
        try:
            output, _ = process.communicate(payload, timeout=request.timeout)
        except subprocess.TimeoutExpired:
            raise TransportError("timeout") from None
        if process.returncode != 0 or len(output) > MAX_PROTOCOL:
            raise TransportError("protocol")
        data = json.loads(output)
        if type(data) is not dict:
            raise TransportError("protocol")
        if set(data) == {"error"}:
            raise TransportError(data["error"] if type(data["error"]) is str else "protocol")
        if set(data) != {"status", "headers", "body"} or type(data["body"]) is not str:
            raise TransportError("protocol")
        headers = tuple(tuple(pair) for pair in data["headers"])
        body = b64decode(data["body"], validate=True)
        _check(
            type(data["status"]) is int and 100 <= data["status"] <= 599,
            "response",
            "invalid status",
        )
        _headers(headers)
        _check(len(body) <= MAX_BODY, "response", "body limit")
        return HopResponse(data["status"], headers, body)
    except TransportError:
        raise
    except (OSError, ValueError, TypeError, KeyError):
        raise TransportError("protocol") from None
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.communicate()


def _retry_after(value: str | None, now: datetime) -> float:
    if value is None:
        return 0.0
    try:
        if value.isascii() and value.isdecimal():
            return float(int(value))
        parsed = parsedate_to_datetime(value)
        return max(0.0, (_utc(parsed, "retry_after") - now).total_seconds())
    except (ValueError, TypeError, OverflowError):
        # Invalid server delay is not permission to retry immediately.
        return math.inf


def fetch_feed(
    source: Source,
    checkpoint: PollCheckpoint | None,
    *,
    policy: RequestPolicy,
    observed_at: datetime,
    transport: Callable[[HopRequest], HopResponse] = isolated_transport,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> FetchResult:
    """Fetch one approved source serially; return candidates, never commit successful state."""
    _check(
        type(source) is Source and type(policy) is RequestPolicy,
        "fetch",
        "validated source and policy required",
    )
    now = _utc(observed_at, "observed_at")
    _check(
        source.enabled
        and source.approval_status == "approved"
        and source.reviewed_at <= now
        and policy.reviewed_at <= now,
        "fetch",
        "dated source approval and request policy required",
    )
    _check(
        checkpoint is None
        or (type(checkpoint) is PollCheckpoint and checkpoint.source_id == source.id),
        "fetch",
        "matching checkpoint required",
    )
    if checkpoint is not None:
        wait = policy.minimum_interval_seconds - (now - checkpoint.last_attempt_at).total_seconds()
        if wait > 0:
            return FetchResult("deferred", 0, "poll_interval", retry_after_seconds=wait)
    url = source.feed_url
    destination(url, source.allowed_hosts)
    conditional = []
    if checkpoint is not None and checkpoint.last_success_at is not None:
        if checkpoint.etag is not None:
            conditional.append(("If-None-Match", checkpoint.etag))
        if checkpoint.last_modified is not None:
            conditional.append(("If-Modified-Since", checkpoint.last_modified))
    start = monotonic()
    deadline = start + TOTAL_SECONDS
    calls = redirects = retries = 0
    last_request = None
    visited = {url}
    while calls < MAX_REQUESTS:
        remaining = deadline - monotonic()
        if remaining <= 0:
            return FetchResult("error", calls, "timeout")
        if last_request is not None:
            spacing = policy.minimum_interval_seconds - (monotonic() - last_request)
            if spacing > 0:
                if spacing >= remaining:
                    return FetchResult(
                        "deferred", calls, "poll_interval", retry_after_seconds=spacing
                    )
                sleep(spacing)
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return FetchResult("error", calls, "timeout")
        headers = (
            ("User-Agent", USER_AGENT),
            ("Accept", "application/rss+xml, application/atom+xml, application/xml"),
            ("Accept-Encoding", "gzip"),
            ("Connection", "close"),
            *conditional,
        )
        calls += 1
        last_request = monotonic()
        try:
            response = transport(
                HopRequest(url, source.allowed_hosts, headers, min(HOP_SECONDS, remaining))
            )
            _check(
                type(response) is HopResponse
                and type(response.status) is int
                and 100 <= response.status <= 599,
                "response",
                "invalid response",
            )
            metadata = _headers(response.headers)
            _check(
                type(response.body) is bytes and len(response.body) <= MAX_BODY,
                "response",
                "body limit",
            )
        except TransportError as error:
            if error.code not in {"timeout", "network"}:
                return FetchResult("error", calls, error.code)
            response = None
            metadata = {}
            failure = error.code
        except ContractError:
            return FetchResult("error", calls, "protocol")
        server_delay = (
            _retry_after(metadata.get("retry-after"), now + timedelta(seconds=monotonic() - start))
            if response is not None and response.status in {429, 500, 502, 503, 504}
            else 0.0
        )
        if monotonic() >= deadline:
            if server_delay > 0:
                return FetchResult(
                    "deferred",
                    calls,
                    "rate_limit" if response.status == 429 else "http_status",
                    retry_after_seconds=max(policy.minimum_interval_seconds, server_delay)
                    if math.isfinite(server_delay)
                    else None,
                )
            return FetchResult("error", calls, "timeout")
        if response is not None:
            if response.status in {301, 302, 303, 307, 308}:
                location = metadata.get("location")
                if location is None or redirects >= MAX_REDIRECTS:
                    return FetchResult("error", calls, "redirect")
                if "#" in location:
                    return FetchResult("error", calls, "destination")
                try:
                    next_url = urljoin(url, location)
                    destination(next_url, source.allowed_hosts)
                except (ContractError, ValueError):
                    return FetchResult("error", calls, "destination")
                if next_url in visited:
                    return FetchResult("error", calls, "redirect")
                visited.add(next_url)
                url = next_url
                conditional = []  # Validators never cross a redirect resource boundary.
                redirects += 1
                continue
            if response.status in {200, 304}:
                if response.status == 304 and (not conditional or response.body):
                    return FetchResult("error", calls, "unsolicited_304")
                try:
                    for key, limit in (("etag", 512), ("last-modified", 128)):
                        if key in metadata:
                            _text(metadata[key], "validator", limit)
                except ContractError:
                    return FetchResult("error", calls, "headers")
                return FetchResult(
                    "ok" if response.status == 200 else "not_modified",
                    calls,
                    body=response.body if response.status == 200 else None,
                    etag=metadata.get("etag"),
                    last_modified=metadata.get("last-modified"),
                )
            if response.status not in {429, 500, 502, 503, 504}:
                return FetchResult("error", calls, "http_status")
            failure = "rate_limit" if response.status == 429 else "http_status"
        if retries or calls >= MAX_REQUESTS:
            if server_delay > 0:
                return FetchResult(
                    "deferred",
                    calls,
                    failure,
                    retry_after_seconds=max(policy.minimum_interval_seconds, server_delay)
                    if math.isfinite(server_delay)
                    else None,
                )
            return FetchResult("error", calls, failure)
        random_part = jitter()
        _check(
            type(random_part) in {int, float}
            and math.isfinite(random_part)
            and 0 <= random_part <= 1,
            "jitter",
            "bounded jitter required",
        )
        delay = max(
            policy.minimum_interval_seconds,
            1 + random_part,
            server_delay,
        )
        if delay >= deadline - monotonic():
            return FetchResult(
                "deferred",
                calls,
                failure,
                retry_after_seconds=delay if math.isfinite(delay) else None,
            )
        sleep(delay)
        retries += 1
    return FetchResult("error", calls, "request_budget")
