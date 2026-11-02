"""Trusted single-hop transport worker; never invoked automatically or by tests against publishers."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import sys
import time
import zlib
from base64 import b64encode

from wrap_brief.ingest.http import (
    MAX_BODY,
    MAX_PROTOCOL,
    HopRequest,
    HopResponse,
    TransportError,
    _headers,
    destination,
)
from wrap_brief.models import ContractError


def _public(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise TransportError("destination") from None
    if (
        not address.is_global
        or address.is_multicast
        or address.is_unspecified
        or getattr(address, "ipv4_mapped", None)
        or getattr(address, "sixtofour", None)
        or getattr(address, "teredo", None)
        or str(address) == "168.63.129.16"  # Azure platform virtual address, not a publisher.
    ):
        raise TransportError("destination")
    return address


def _decode(response: http.client.HTTPResponse, metadata: dict[str, str], deadline: float) -> bytes:
    encoding = metadata.get("content-encoding", "identity").lower()
    if encoding not in {"gzip", "identity"}:
        raise TransportError("encoding")
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    output = bytearray()
    encoded = 0
    while True:
        if time.monotonic() >= deadline:
            raise TransportError("timeout")
        chunk = response.read1(min(65_536, MAX_BODY + 1 - encoded))
        if not chunk:
            break
        encoded += len(chunk)
        if encoded > MAX_BODY:
            raise TransportError("size")
        if decompressor:
            chunk = decompressor.decompress(chunk, MAX_BODY + 1 - len(output))
            if decompressor.unconsumed_tail:
                raise TransportError("size")
            if decompressor.unused_data:
                raise TransportError("encoding")
        output.extend(chunk)
        if len(output) > MAX_BODY:
            raise TransportError("size")
    if decompressor and not decompressor.eof:
        raise TransportError("encoding")
    length = metadata.get("content-length")
    if length is not None and encoded != int(length):
        raise TransportError("headers")
    return bytes(output)


def one_hop(request: HopRequest) -> HopResponse:
    """One pinned verified HTTPS request, with no redirects/proxies/cookies or automatic retries."""
    connection = raw = secured = None
    try:
        host, target = destination(request.url, request.allowed_hosts)
        outgoing = _headers(request.headers)
        allowed = {
            "user-agent",
            "accept",
            "accept-encoding",
            "connection",
            "if-none-match",
            "if-modified-since",
        }
        if not set(outgoing) <= allowed or not 0 < request.timeout <= 15:
            raise TransportError("protocol")
        deadline = time.monotonic() + request.timeout
        # DNS never occurs again after this validation; numeric socket.connect pins the peer.
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not answers or len(answers) > 32:
            raise TransportError("destination")
        for family, _, _, _, address in answers:
            if family not in {socket.AF_INET, socket.AF_INET6}:
                raise TransportError("destination")
            _public(address[0])
        family, _, _, _, address = answers[0]
        selected = _public(address[0])
        raw = socket.socket(family, socket.SOCK_STREAM)
        raw.settimeout(max(0.001, deadline - time.monotonic()))
        raw.connect(address)
        if _public(raw.getpeername()[0]) != selected:
            raise TransportError("destination")
        context = ssl.create_default_context()
        secured = context.wrap_socket(raw, server_hostname=host)
        connection = http.client.HTTPConnection(host, 443, timeout=request.timeout)
        connection.sock = secured
        connection.request(
            "GET", target, headers={**outgoing, "Host": f"[{host}]" if ":" in host else host}
        )
        response = connection.getresponse()
        pairs = tuple(response.getheaders())
        metadata = _headers(pairs)
        length = metadata.get("content-length")
        transfer = metadata.get("transfer-encoding")
        if length is not None and (
            not length.isascii() or not length.isdecimal() or int(length) > MAX_BODY
        ):
            raise TransportError("size")
        if transfer is not None and (transfer.lower() != "chunked" or length is not None):
            raise TransportError("headers")
        body = _decode(response, metadata, deadline) if response.status == 200 else b""
        selected_headers = tuple(
            (key, value)
            for key, value in metadata.items()
            if key in {"etag", "last-modified", "location", "retry-after"}
        )
        return HopResponse(response.status, selected_headers, body)
    except TransportError:
        raise
    except ssl.SSLError:
        raise TransportError("tls") from None
    except TimeoutError:
        raise TransportError("timeout") from None
    except ContractError:
        raise TransportError("headers") from None
    except zlib.error:
        raise TransportError("encoding") from None
    except (OSError, http.client.HTTPException):
        raise TransportError("network") from None
    finally:
        if connection is not None:
            connection.close()
        if secured is not None:
            secured.close()
        if raw is not None:
            raw.close()


def main() -> None:
    try:
        raw = sys.stdin.buffer.read(16_385)
        if len(raw) > 16_384:
            raise TransportError("protocol")
        data = json.loads(raw)
        if type(data) is not dict or set(data) != {"url", "hosts", "headers", "timeout"}:
            raise TransportError("protocol")
        request = HopRequest(
            data["url"],
            tuple(data["hosts"]),
            tuple(tuple(p) for p in data["headers"]),
            data["timeout"],
        )
        response = one_hop(request)
        output = {
            "status": response.status,
            "headers": response.headers,
            "body": b64encode(response.body).decode("ascii"),
        }
        encoded = json.dumps(output).encode()
        if len(encoded) > MAX_PROTOCOL:
            raise TransportError("protocol")
    except TransportError as error:
        encoded = json.dumps({"error": error.code}).encode()
    except Exception:
        encoded = b'{"error":"protocol"}'
    sys.stdout.buffer.write(encoded)


if __name__ == "__main__":
    main()
