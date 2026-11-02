from __future__ import annotations

import gzip
import io
import json
import socket
import ssl
import subprocess
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import MagicMock, patch

from fixtures.support import read_json

from wrap_brief.ingest import _http_worker as worker
from wrap_brief.ingest import http
from wrap_brief.models import ContractError
from wrap_brief.state.snapshot import PollCheckpoint, Snapshot


class Clock:
    def __init__(self):
        self.value = 100.0
        self.delays = []

    def __call__(self):
        return self.value

    def sleep(self, delay):
        self.delays.append(delay)
        self.value += delay


class FeedHttpTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = Snapshot.from_dict(read_json("views/digest.json"))
        self.now = self.snapshot.observed_at
        self.source = replace(
            self.snapshot.sources[0],
            enabled=True,
            approval_status="approved",
            approval_ref="tests/fixtures/README.md",
            reviewed_at=self.now - timedelta(days=1),
        )
        self.policy = http.RequestPolicy("tests/fixtures/README.md", self.now, 1)
        self.clock = Clock()
        self.requests = []

    def fetch(self, sequence, checkpoint=None, **kwargs):
        responses = iter(sequence)

        def transport(request):
            self.requests.append(request)
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return response

        return http.fetch_feed(
            self.source,
            checkpoint,
            policy=kwargs.pop("policy", self.policy),
            observed_at=self.now,
            transport=transport,
            monotonic=self.clock,
            sleep=self.clock.sleep,
            jitter=lambda: 0.5,
            **kwargs,
        )

    def checkpoint(self):
        return PollCheckpoint(
            self.source.id,
            self.now - timedelta(hours=1),
            self.now - timedelta(hours=1),
            etag='W/"synthetic"',
            last_modified="Fri, 02 Jan 2026 11:30:00 GMT",
            status="ok",
        )

    def test_approved_source_success_is_body_candidate_not_state_commit(self):
        result = self.fetch([http.HopResponse(200, (("ETag", '"new"'),), b"<rss/>")])
        self.assertEqual(
            (result.status, result.body, result.etag, result.requests),
            ("ok", b"<rss/>", '"new"', 1),
        )
        self.assertNotIn("<rss", repr(result))
        headers = dict(self.requests[0].headers)
        self.assertEqual(headers["Connection"], "close")
        self.assertIn("WrapBrief/", headers["User-Agent"])
        self.assertNotIn("Authorization", headers)
        self.assertEqual(self.requests[0].timeout, 15)

    def test_approval_disabled_missing_policy_or_future_review_never_transport(self):
        for source in (
            self.snapshot.sources[0],
            replace(self.source, enabled=False),
            replace(self.source, reviewed_at=self.now + timedelta(days=1)),
        ):
            with self.subTest(source=source.enabled), self.assertRaises(ContractError):
                http.fetch_feed(
                    source,
                    None,
                    policy=self.policy,
                    observed_at=self.now,
                    transport=lambda request: self.fail("unauthorized request"),
                )
        for policy in (None, replace(self.policy, reviewed_at=self.now + timedelta(days=1))):
            with self.assertRaises(ContractError):
                http.fetch_feed(
                    self.source,
                    None,
                    policy=policy,
                    observed_at=self.now,
                    transport=lambda request: self.fail("unauthorized request"),
                )

    def test_explicit_poll_interval_checkpoint_matching_and_first_poll(self):
        checkpoint = replace(self.checkpoint(), last_attempt_at=self.now)
        result = self.fetch(
            [], checkpoint, policy=replace(self.policy, minimum_interval_seconds=30)
        )
        self.assertEqual(
            (result.status, result.requests, result.retry_after_seconds), ("deferred", 0, 30)
        )
        self.assertEqual(self.requests, [])
        with self.assertRaises(ContractError):
            self.fetch([], replace(checkpoint, source_id="other"))

    def test_conditional_304_is_unchanged_without_empty_feed_or_state_mutation(self):
        checkpoint = self.checkpoint()
        before = checkpoint.to_dict()
        result = self.fetch([http.HopResponse(304, (("ETag", '"new"'),))], checkpoint)
        self.assertEqual(result.status, "not_modified")
        self.assertIsNone(result.body)
        self.assertEqual(dict(self.requests[0].headers)["If-None-Match"], checkpoint.etag)
        self.assertEqual(checkpoint.to_dict(), before)
        self.assertEqual(self.fetch([http.HopResponse(304)]).code, "unsolicited_304")

    def test_redirects_are_revalidated_and_validators_do_not_cross_resource(self):
        result = self.fetch(
            [
                http.HopResponse(302, (("Location", "/next?edition=2&v="),)),
                http.HopResponse(200, body=b"ok"),
            ],
            self.checkpoint(),
        )
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.requests[-1].url, "https://example.com/next?edition=2&v=")
        self.assertNotIn("If-None-Match", dict(self.requests[-1].headers))
        self.assertEqual(self.clock.delays, [1])
        for location in (
            "http://example.com/feed",
            "https://127.0.0.1/",
            "https://169.254.169.254/latest",
            "https://evil.org/feed",
            "https://example.com/feed#",
            "https://user:password@example.com/feed",
        ):
            with self.subTest(location=location):
                self.requests.clear()
                result = self.fetch([http.HopResponse(302, (("Location", location),))])
                self.assertEqual(result.code, "destination")
                self.assertEqual(len(self.requests), 1)

    def test_redirect_loop_fourth_redirect_and_total_hop_retry_budget(self):
        self.assertEqual(
            self.fetch([http.HopResponse(302, (("Location", self.source.feed_url),))]).code,
            "redirect",
        )
        sequence = [http.HopResponse(302, (("Location", f"/hop{n}"),)) for n in range(4)]
        self.assertEqual(self.fetch(sequence).code, "redirect")
        self.requests.clear()
        result = self.fetch(
            [http.HopResponse(503), *sequence[:3], http.HopResponse(200, body=b"ok")]
        )
        self.assertEqual((result.status, result.requests), ("ok", 5))

    def test_only_one_transient_retry_and_no_early_rate_limit_retry(self):
        result = self.fetch(
            [http.HopResponse(429, (("Retry-After", "30"),)), http.HopResponse(200, body=b"ok")]
        )
        self.assertEqual(result.status, "ok")
        self.assertEqual(self.clock.delays, [30])
        self.assertEqual(self.fetch([http.HopResponse(503), http.HopResponse(503)]).requests, 2)
        self.assertEqual(self.fetch([http.HopResponse(404)]).requests, 1)
        for code in ("tls", "destination", "size", "encoding", "protocol", "headers"):
            self.assertEqual(self.fetch([http.TransportError(code)]).requests, 1)
        self.assertEqual(
            self.fetch([http.TransportError("timeout"), http.HopResponse(200)]).status, "ok"
        )

    def test_retry_after_date_oversized_invalid_and_policy_spacing_defer(self):
        for delay in ("999999999", "bad-date", "Fri, 02 Jan 2026 13:30:00 GMT"):
            with self.subTest(delay=delay):
                self.assertEqual(
                    self.fetch([http.HopResponse(429, (("Retry-After", delay),))]).status,
                    "deferred",
                )
        result = self.fetch(
            [http.HopResponse(503)], policy=replace(self.policy, minimum_interval_seconds=60)
        )
        self.assertEqual(result.status, "deferred")
        self.assertEqual(result.requests, 1)

    def test_total_deadline_injected_clock_and_invalid_transport_are_bounded(self):
        def slow(request):
            self.clock.value += 61
            return http.HopResponse(200)

        result = http.fetch_feed(
            self.source,
            None,
            policy=self.policy,
            observed_at=self.now,
            transport=slow,
            monotonic=self.clock,
            sleep=self.clock.sleep,
        )
        self.assertEqual(result.code, "timeout")
        self.assertEqual(self.fetch([http.HopResponse(True)]).code, "protocol")
        self.assertEqual(
            self.fetch([http.HopResponse(200, (("ETag", "x\r\nprivate-marker"),))]).code, "protocol"
        )
        self.assertNotIn("private-marker", repr(result))

    def test_shared_transport_fixtures_preserve_failure_semantics(self):
        cases = read_json("transport.json")["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                status = case["status"]
                first = (
                    http.TransportError("timeout")
                    if status is None
                    else http.HopResponse(status, tuple(case["headers"].items()))
                )
                result = self.fetch([first, http.HopResponse(503)])
                self.assertIn(result.status, {"error", "not_modified", "deferred"})

    def test_terminal_server_backoff_survives_exhausted_retry_budget(self):
        for status in (429, 503):
            for delay, expected in (
                ("3600", 3600),
                ("Fri, 02 Jan 2026 13:30:00 GMT", 3598.5),
                ("bad-date", None),
            ):
                with self.subTest(status=status, delay=delay):
                    self.clock = Clock()
                    result = self.fetch(
                        [http.HopResponse(503), http.HopResponse(status, (("Retry-After", delay),))]
                    )
                    self.assertEqual((result.status, result.requests), ("deferred", 2))
                    self.assertEqual(result.retry_after_seconds, expected)

    def test_deadline_expiry_preserves_received_numeric_or_invalid_server_delay(self):
        for status in (429, 503):
            for delay, expected in (("3600", 3600), ("bad-date", None)):
                with self.subTest(status=status, delay=delay):
                    self.clock = Clock()

                    def transport(request, status=status, delay=delay):
                        self.clock.value += 60
                        return http.HopResponse(status, (("Retry-After", delay),))

                    result = http.fetch_feed(
                        self.source,
                        None,
                        policy=self.policy,
                        observed_at=self.now,
                        transport=transport,
                        monotonic=self.clock,
                        sleep=self.clock.sleep,
                    )
                    self.assertEqual((result.status, result.requests), ("deferred", 1))
                    self.assertEqual(result.retry_after_seconds, expected)


class WorkerTests(unittest.TestCase):
    def request(self):
        return http.HopRequest(
            "https://example.com/feed?x=1&y=",
            ("example.com",),
            (("User-Agent", http.USER_AGENT),),
            15.0,
        )

    def run_hop(
        self, body=b"<rss/>", headers=(), addresses=None, status=200, peer="8.8.8.8", ssl_error=None
    ):
        response = MagicMock()
        stream = io.BytesIO(body)
        response.read1.side_effect = stream.read1
        response.getheaders.return_value = list(headers)
        response.status = status
        raw = MagicMock()
        raw.getpeername.return_value = (peer, 443)
        context = MagicMock()
        if ssl_error:
            context.wrap_socket.side_effect = ssl_error
        connection = MagicMock()
        connection.getresponse.return_value = response
        answers = addresses or [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with (
            patch.object(worker.socket, "getaddrinfo", return_value=answers) as resolver,
            patch.object(worker.socket, "socket", return_value=raw) as socket_factory,
            patch.object(worker.ssl, "create_default_context", return_value=context),
            patch.object(worker.http.client, "HTTPConnection", return_value=connection),
        ):
            try:
                result = worker.one_hop(self.request())
            finally:
                self.raw, self.context, self.connection, self.response = (
                    raw,
                    context,
                    connection,
                    response,
                )
                self.socket_factory, self.resolver = socket_factory, resolver
        return result

    def test_dns_pinned_socket_peer_tls_sni_and_original_host(self):
        result = self.run_hop()
        self.assertEqual(result.body, b"<rss/>")
        self.raw.connect.assert_called_once_with(("8.8.8.8", 443))
        self.context.wrap_socket.assert_called_once_with(self.raw, server_hostname="example.com")
        self.assertEqual(self.connection.request.call_args.args[:2], ("GET", "/feed?x=1&y="))
        self.assertEqual(self.connection.request.call_args.kwargs["headers"]["Host"], "example.com")
        self.resolver.assert_called_once()
        self.raw.close.assert_called()
        self.connection.close.assert_called()

    def test_every_dns_answer_must_be_public_and_no_connect_on_mixed_answers(self):
        for ip in (
            "127.0.0.1",
            "169.254.169.254",
            "10.0.0.1",
            "::1",
            "fc00::1",
            "224.0.0.1",
            "::ffff:8.8.8.8",
            "2002:7f00:1::",
            "2001:0000:4136:e378:8000:63bf:3fff:fdd2",
            "168.63.129.16",
        ):
            answers = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                (
                    socket.AF_INET6 if ":" in ip else socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    (ip, 443),
                ),
            ]
            with self.subTest(ip=ip), self.assertRaisesRegex(http.TransportError, "destination"):
                self.run_hop(addresses=answers)
            self.socket_factory.assert_not_called()

    def test_peer_mismatch_certificate_failure_and_resources_closed(self):
        with self.assertRaisesRegex(http.TransportError, "destination"):
            self.run_hop(peer="1.1.1.1")
        self.raw.close.assert_called()
        with self.assertRaisesRegex(http.TransportError, "tls"):
            self.run_hop(ssl_error=ssl.SSLCertVerificationError("private-cert-message"))
        self.raw.close.assert_called()

    def test_encoded_and_decoded_caps_identity_exact_plus_one_gzip_bomb(self):
        self.assertEqual(len(self.run_hop(body=b"x" * http.MAX_BODY).body), http.MAX_BODY)
        with self.assertRaisesRegex(http.TransportError, "size"):
            self.run_hop(body=b"x" * (http.MAX_BODY + 1))
        compressed = gzip.compress(b"x" * (http.MAX_BODY + 1))
        with self.assertRaisesRegex(http.TransportError, "size"):
            self.run_hop(body=compressed, headers=(("Content-Encoding", "gzip"),))
        compressed = gzip.compress(b"x" * http.MAX_BODY)
        self.assertEqual(
            len(self.run_hop(body=compressed, headers=(("Content-Encoding", "gzip"),)).body),
            http.MAX_BODY,
        )

    def test_gzip_integrity_truncation_trailing_members_and_encoding(self):
        good = gzip.compress(b"<rss/>")
        for body in (good[:-3], good + b"junk", good + good, b"notgzip"):
            with (
                self.subTest(size=len(body)),
                self.assertRaisesRegex(http.TransportError, "encoding"),
            ):
                self.run_hop(body=body, headers=(("Content-Encoding", "gzip"),))
        for encoding in ("br", "gzip, gzip", "deflate"):
            with self.assertRaisesRegex(http.TransportError, "encoding"):
                self.run_hop(headers=(("Content-Encoding", encoding),))

    def test_framing_header_bounds_and_content_length_mismatch(self):
        cases = (
            (("Content-Length", "6"), ("Content-Length", "6")),
            (("Content-Length", "6"), ("Transfer-Encoding", "chunked")),
            (("Content-Length", "5"),),
            (("Content-Length", "-1"),),
            (("Transfer-Encoding", "gzip"),),
            (("ETag", "x" * 4097),),
        )
        for headers in cases:
            with self.subTest(headers=headers), self.assertRaises(http.TransportError):
                self.run_hop(headers=headers)

    def test_non_success_bodies_never_drained_and_only_selected_metadata_leaves_worker(self):
        result = self.run_hop(
            status=302, headers=(("Location", "/next"), ("Set-Cookie", "private-cookie"))
        )
        self.assertEqual(result.headers, (("location", "/next"),))
        self.response.read1.assert_not_called()
        self.assertNotIn("private-cookie", repr(result))

    def test_dns_header_and_body_timeouts_have_fixed_codes(self):
        with (
            patch.object(worker.socket, "getaddrinfo", side_effect=TimeoutError("private-dns")),
            self.assertRaisesRegex(http.TransportError, "^timeout$"),
        ):
            worker.one_hop(self.request())
        for stage in ("getresponse", "read1"):
            with (
                patch.object(
                    worker.socket,
                    "getaddrinfo",
                    return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
                ),
                patch.object(worker.socket, "socket") as raw,
                patch.object(worker.ssl, "create_default_context"),
                patch.object(worker.http.client, "HTTPConnection") as connection,
            ):
                raw.return_value.getpeername.return_value = ("8.8.8.8", 443)
                if stage == "getresponse":
                    connection.return_value.getresponse.side_effect = TimeoutError("private-header")
                else:
                    response = connection.return_value.getresponse.return_value
                    response.status = 200
                    response.getheaders.return_value = []
                    response.read1.side_effect = TimeoutError("private-body")
                with self.assertRaisesRegex(http.TransportError, "^timeout$"):
                    worker.one_hop(self.request())
                raw.return_value.close.assert_called()

    def test_isolation_timeout_and_cancellation_kill_and_reap_worker(self):
        for failure in (subprocess.TimeoutExpired("worker", 15), KeyboardInterrupt()):
            process = MagicMock()
            process.communicate.side_effect = [failure, (b"", None)]
            process.poll.return_value = None
            with patch.object(http.subprocess, "Popen", return_value=process) as popen:
                with self.assertRaises(
                    http.TransportError
                    if isinstance(failure, subprocess.TimeoutExpired)
                    else KeyboardInterrupt
                ):
                    http.isolated_transport(self.request())
                process.kill.assert_called_once()
                self.assertEqual(process.communicate.call_count, 2)
                args = popen.call_args
                self.assertIn("-I", args.args[0])
                self.assertNotIn("HTTPS_PROXY", args.kwargs["env"])
                self.assertNotIn("GITHUB_TOKEN", args.kwargs["env"])

    def test_protocol_rejects_bad_worker_payloads_without_private_errors(self):
        for output in (
            b"not-json-private-marker",
            json.dumps({"status": 200, "headers": [], "body": "%%%"}).encode(),
            b'{"error":"private-marker"}',
        ):
            process = MagicMock()
            process.communicate.return_value = (output, None)
            process.returncode = 0
            process.poll.return_value = 0
            with (
                patch.object(http.subprocess, "Popen", return_value=process),
                self.assertRaisesRegex(http.TransportError, "^protocol$"),
            ):
                http.isolated_transport(self.request())

    def test_installed_worker_rejects_invalid_input_without_dns(self):
        result = subprocess.run(
            [http.sys.executable, "-I", "-m", "wrap_brief.ingest._http_worker"],
            input=b"{}",
            capture_output=True,
            timeout=5,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout), {"error": "protocol"})
        self.assertEqual(result.stderr, b"")

    def test_actual_process_timeout_terminates_and_reaps_without_network(self):
        original = subprocess.Popen
        processes = []

        def sleeping_worker(*args, **kwargs):
            process = original(
                [http.sys.executable, "-I", "-c", "import time; time.sleep(30)"], **kwargs
            )
            processes.append(process)
            return process

        with (
            patch.object(http.subprocess, "Popen", side_effect=sleeping_worker),
            self.assertRaisesRegex(http.TransportError, "^timeout$"),
        ):
            http.isolated_transport(replace(self.request(), timeout=0.05))
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_real_stdlib_http_parser_chunking_and_gzip_over_fake_pinned_tls_socket(self):
        compressed = gzip.compress(b"<rss/>")
        wire = (
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Encoding: gzip\r\nETag: fixture\r\n\r\n"
            + f"{len(compressed):x}\r\n".encode()
            + compressed
            + b"\r\n0\r\n\r\n"
        )
        raw = MagicMock()
        raw.getpeername.return_value = ("8.8.8.8", 443)
        secured = MagicMock()
        secured.makefile.return_value = io.BytesIO(wire)
        context = MagicMock()
        context.wrap_socket.return_value = secured
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with (
            patch.object(worker.socket, "getaddrinfo", return_value=answers),
            patch.object(worker.socket, "socket", return_value=raw),
            patch.object(worker.ssl, "create_default_context", return_value=context),
        ):
            result = worker.one_hop(self.request())
        self.assertEqual(result.body, b"<rss/>")
        self.assertEqual(result.headers, (("etag", "fixture"),))
        self.assertIn(
            b"Host: example.com", b"".join(call.args[0] for call in secured.sendall.call_args_list)
        )
        raw.close.assert_called()
        secured.close.assert_called()


if __name__ == "__main__":
    unittest.main()
