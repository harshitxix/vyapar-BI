import pytest
import asyncio
from datetime import datetime, timezone
from backend.app.utils.url import canonicalize_url, hash_url
from backend.app.utils.date import normalize_datetime
from backend.app.utils.dedup import normalize_title, hash_normalized_title, compute_content_fingerprint
from backend.app.utils.relevance import classify_domain
from backend.app.adapters.rss.adapter import RSSAdapter
from backend.app.adapters.base import RawArticle
from backend.app.models.source import Source


def test_url_canonicalization():
    raw_url = "https://Example.COM/news/grocery-inflation?utm_source=twitter&utm_medium=social&id=987#comment-section"
    clean = canonicalize_url(raw_url)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "#comment-section" not in clean
    assert "id=987" in clean
    assert clean.startswith("https://example.com/news/grocery-inflation")

    # Hash should be deterministic
    h1 = hash_url(raw_url)
    h2 = hash_url("https://example.com/news/grocery-inflation?id=987")
    assert h1 == h2


def test_date_normalization():
    # ISO-8601
    dt1 = normalize_datetime("2026-09-28T03:30:00+05:30")
    assert dt1.tzinfo == timezone.utc
    assert dt1.hour == 22 or dt1.day == 27 or dt1.hour == 22

    # RFC-2822
    dt2 = normalize_datetime("Mon, 28 Sep 2026 08:00:00 GMT")
    assert dt2.tzinfo == timezone.utc
    assert dt2.year == 2026

    # None / Empty fallback
    dt3 = normalize_datetime(None)
    assert dt3.tzinfo == timezone.utc


def test_deduplication_hashing():
    t1 = "Reliance Retail announces 500 new stores across India!"
    t2 = "  reliance retail announces 500 new stores across india.  "
    assert hash_normalized_title(t1) == hash_normalized_title(t2)

    fp1 = compute_content_fingerprint(t1, "Reliance plans aggressive expansion.")
    fp2 = compute_content_fingerprint(t2, "Reliance plans aggressive expansion.")
    assert fp1 == fp2


def test_domain_classification():
    d1 = classify_domain("Zepto and Blinkit expand dark stores for 10-minute grocery delivery")
    assert d1 == "grocery"

    d2 = classify_domain("Zara parent Inditex reports booming apparel sales in India")
    assert d2 == "fashion"

    d3 = classify_domain("SaaS startups secure funding for enterprise AI solutions")
    assert d3 == "technology"


def test_rss_normalization_and_validation():
    adapter = RSSAdapter()
    dummy_source = Source(
        id="test-source",
        name="Test Feed",
        domain="test.com",
        source_type="rss",
        base_url="https://test.com",
        business_domains=["retail", "grocery"],
        regions=["india"],
        language="en"
    )

    raw = RawArticle(
        title="FMCG volume growth rebounds in rural India",
        original_url="https://test.com/story?id=123&utm_source=feed",
        description="<p>Rural demand for staples and packaged goods showed 8% growth.</p>",
        author="Retail Bureau",
        published_at_raw="Mon, 28 Sep 2026 10:00:00 GMT"
    )

    canonical = adapter.normalize(raw, dummy_source)
    assert canonical.title == "FMCG volume growth rebounds in rural India"
    assert "utm_source" not in canonical.canonical_url
    assert canonical.business_domain == "grocery"
    assert adapter.validate(canonical) is True

    # Invalid article validation
    invalid_art = canonical.model_copy(update={"title": ""})
    assert adapter.validate(invalid_art) is False
