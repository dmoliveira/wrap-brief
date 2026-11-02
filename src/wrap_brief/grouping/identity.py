"""Versioned source-scoped URL identity without network, clock, or persistence."""

from __future__ import annotations

import hashlib
import ipaddress
from urllib.parse import unquote_to_bytes, urlsplit

from wrap_brief.models import ContractError, _identifier, validate_https_url

TRACKING_PARAMETERS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "gclid",
        "dclid",
        "fbclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
    }
)
_NAMESPACE = b"item-v1\0"


def _policy(value: frozenset[str]) -> frozenset[bytes]:
    if type(value) is not frozenset or not value <= TRACKING_PARAMETERS:
        raise ContractError("tracking: reviewed immutable subset required")
    return frozenset(name.encode("ascii") for name in value)


def canonical_url(
    value: object,
    *,
    tracking_parameters: frozenset[str] = TRACKING_PARAMETERS,
) -> str:
    """Canonicalize only known identity-equivalent spelling and reviewed tracking keys."""
    allowed = _policy(tracking_parameters)
    url = validate_https_url(value)
    if "#" in url:
        raise ContractError("url: fragment delimiter prohibited")
    parsed = urlsplit(url)
    host = parsed.hostname.removesuffix(".")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        host = host.encode("idna").decode("ascii").lower()
    else:
        host = f"[{address.compressed}]" if address.version == 6 else str(address)
    # Core permits only the default HTTPS port. No path or query decoding/re-encoding.
    result = "https://" + host + parsed.path
    if "?" in url:
        retained = []
        for segment in parsed.query.split("&"):
            key = segment.partition("=")[0]
            if unquote_to_bytes(key) not in allowed:
                retained.append(segment)
        if retained:
            result += "?" + "&".join(retained)
    return result


def stable_item_id(
    source_id: str,
    url: str,
    guid: str | None = None,
    *,
    tracking_parameters: frozenset[str] = TRACKING_PARAMETERS,
) -> str:
    """URL-first v1 identity. GUID is intentionally provenance-only and never hashed."""
    _identifier(source_id, "source_id")
    canonical = canonical_url(url, tracking_parameters=tracking_parameters)
    payload = _NAMESPACE + source_id.encode("utf-8") + b"\0" + canonical.encode("utf-8")
    return "item-v1-" + hashlib.sha256(payload).hexdigest()
