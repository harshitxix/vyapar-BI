import re
import uuid
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Any, List, Optional

from backend.app.adapters.base import BaseSourceAdapter, RawArticle
from backend.app.models.source import Source
from backend.app.schemas.article import CanonicalArticle
from backend.app.utils.url import canonicalize_url, hash_url
from backend.app.utils.date import normalize_datetime
from backend.app.utils.dedup import hash_normalized_title, compute_content_fingerprint
from backend.app.utils.relevance import classify_domain


class RSSAdapter(BaseSourceAdapter):
    """
    Standard RSS 2.0 / Atom feed adapter.
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 VyaparNewsBot/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }

    async def fetch(self, source: Source) -> str:
        """Fetches raw RSS feed text using async HTTP."""
        url = source.feed_url or source.base_url
        if not url:
            raise ValueError(f"Source {source.id} has no feed_url or base_url configured.")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text

    def parse(self, payload: str, source: Source) -> List[RawArticle]:
        """Parses raw RSS XML payload into RawArticle instances."""
        feed = feedparser.parse(payload)
        raw_articles: List[RawArticle] = []

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            # Summary/Description extraction & HTML stripping
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            clean_description = None
            extracted_image = None

            if raw_summary:
                soup = BeautifulSoup(raw_summary, "html.parser")
                # Check for image inside summary HTML
                img_tag = soup.find("img")
                if img_tag and img_tag.get("src"):
                    extracted_image = img_tag["src"]
                clean_description = soup.get_text(separator=" ", strip=True)

            # Check media enclosures or media:content for images
            if not extracted_image and "media_content" in entry:
                for media in entry.media_content:
                    if media.get("medium") == "image" or "image" in media.get("type", ""):
                        extracted_image = media.get("url")
                        break

            if not extracted_image and "enclosures" in entry:
                for enc in entry.enclosures:
                    if "image" in enc.get("type", ""):
                        extracted_image = enc.get("href")
                        break

            author = entry.get("author") or entry.get("creator") or None
            published_raw = entry.get("published") or entry.get("pubDate") or entry.get("updated")
            category = None
            if "tags" in entry and entry.tags:
                category = entry.tags[0].get("term")

            raw_articles.append(
                RawArticle(
                    title=title,
                    original_url=link,
                    description=clean_description,
                    author=author,
                    published_at_raw=published_raw,
                    image_url=extracted_image,
                    raw_category=category,
                )
            )

        return raw_articles

    def normalize(self, raw: RawArticle, source: Source) -> CanonicalArticle:
        """Converts RawArticle into CanonicalArticle standard schema."""
        canonical_url = canonicalize_url(raw.original_url)
        url_hash = hash_url(canonical_url)
        title_hash = hash_normalized_title(raw.title)
        fingerprint = compute_content_fingerprint(raw.title, raw.description)
        published_dt = normalize_datetime(raw.published_at_raw)
        fetched_dt = datetime.now(timezone.utc)

        # Region fallback
        region = source.regions[0] if (source.regions and len(source.regions) > 0) else "india"

        # Domain classification
        domain = classify_domain(raw.title, raw.description, source.business_domains)

        return CanonicalArticle(
            id=str(uuid.uuid4()),
            source_id=source.id,
            source_name=source.name,
            source_domain=source.domain,
            title=raw.title,
            description=raw.description,
            author=raw.author,
            original_url=raw.original_url,
            canonical_url=canonical_url,
            canonical_url_hash=url_hash,
            normalized_title_hash=title_hash,
            fingerprint=fingerprint,
            image_url=raw.image_url,
            published_at=published_dt,
            fetched_at=fetched_dt,
            language=source.language or "en",
            region=region,
            business_domain=domain,
            category=raw.raw_category,
            content_type="news",
            extraction_method="rss",
            status="published"
        )

    def validate(self, article: CanonicalArticle) -> bool:
        """Validates canonical article quality."""
        if not article.title or len(article.title) < 3:
            return False
        if not article.canonical_url or not article.canonical_url.startswith("http"):
            return False
        if not article.canonical_url_hash:
            return False
        return True
