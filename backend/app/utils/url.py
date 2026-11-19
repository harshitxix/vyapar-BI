import hashlib
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Tracking query parameters to strip
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid",
    "_ga", "_gl", "_hsenc", "_hsmi", "hsCtaTracking", "igshid",
    "ref", "source", "share", "action_object_map", "action_type_map",
    "action_ref_map"
}


def canonicalize_url(url: str) -> str:
    """
    Normalizes a URL by stripping tracking parameters, lowercase domain/scheme,
    and removing fragment identifiers while preserving necessary query params.
    """
    if not url:
        return ""

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return url

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove standard port numbers if explicit
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parsed.path
    if not path:
        path = "/"
    elif len(path) > 1 and path.endswith("/"):
        path = path[:-1]  # Normalize trailing slash

    # Filter out tracking query parameters
    query_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            if k.lower() not in TRACKING_PARAMS:
                query_params.append((k, v))

    # Sort query parameters for consistency
    query_params.sort(key=lambda x: x[0])
    cleaned_query = urlencode(query_params)

    # Reconstruct without fragment
    clean_url = urlunparse((scheme, netloc, path, "", cleaned_query, ""))
    return clean_url


def hash_url(url: str) -> str:
    """Generates SHA-256 hash of the canonicalized URL."""
    canonical = canonicalize_url(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
