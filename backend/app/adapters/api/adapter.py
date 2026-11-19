import uuid
import httpx
from datetime import datetime, timezone
from typing import Any, List, Optional

from backend.app.adapters.base import BaseSourceAdapter, RawArticle
from backend.app.models.source import Source
from backend.app.schemas.article import CanonicalArticle
from backend.app.utils.url import canonicalize_url, hash_url
from backend.app.utils.date import normalize_datetime
from backend.app.utils.dedup import hash_normalized_title, compute_content_fingerprint
from backend.app.utils.relevance import classify_domain


class JSONAPIAdapter(BaseSourceAdapter):
    """
    Adapter for JSON REST API endpoints that return structured article lists.
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VyaparNewsBot/1.0",
            "Accept": "application/json"
        }

    async def fetch(self, source: Source) -> Any:
        url = source.api_endpoint or source.base_url
        if not url:
            raise ValueError(f"Source {source.id} has no api_endpoint configured.")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def parse(self, payload: Any, source: Source) -> List[RawArticle]:
        raw_articles: List[RawArticle] = []
        items = []

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            # Look for common list keys
            for key in ["articles", "items", "data", "posts", "results", "news"]:
                if key in payload and isinstance(payload[key], list):
                    items = payload[key]
                    break

        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("headline") or ""
            link = item.get("url") or item.get("link") or item.get("original_url") or ""
            if not title or not link:
                continue

            desc = item.get("description") or item.get("summary") or item.get("excerpt")
            author = item.get("author") or item.get("byline")
            pub_raw = item.get("published_at") or item.get("pubDate") or item.get("date")
            img = item.get("image_url") or item.get("urlToImage") or item.get("image")
            cat = item.get("category") or item.get("tag")

            raw_articles.append(
                RawArticle(
                    title=title.strip(),
                    original_url=link.strip(),
                    description=desc.strip() if desc else None,
                    author=author.strip() if author else None,
                    published_at_raw=pub_raw,
                    image_url=img,
                    raw_category=cat,
                    raw_data=item
                )
            )

        return raw_articles

    def normalize(self, raw: RawArticle, source: Source) -> CanonicalArticle:
        canonical_url = canonicalize_url(raw.original_url)
        url_hash = hash_url(canonical_url)
        title_hash = hash_normalized_title(raw.title)
        fingerprint = compute_content_fingerprint(raw.title, raw.description)
        published_dt = normalize_datetime(raw.published_at_raw)
        fetched_dt = datetime.now(timezone.utc)

        region = source.regions[0] if (source.regions and len(source.regions) > 0) else "india"
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
            extraction_method="api",
            status="published"
        )

    def validate(self, article: CanonicalArticle) -> bool:
        if not article.title or len(article.title) < 3:
            return False
        if not article.canonical_url or not article.canonical_url.startswith("http"):
            return False
        if not article.canonical_url_hash:
            return False
        return True
