import uuid
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urljoin

from backend.app.adapters.base import BaseSourceAdapter, RawArticle
from backend.app.models.source import Source
from backend.app.schemas.article import CanonicalArticle
from backend.app.utils.url import canonicalize_url, hash_url
from backend.app.utils.date import normalize_datetime
from backend.app.utils.dedup import hash_normalized_title, compute_content_fingerprint
from backend.app.utils.relevance import classify_domain


class HTMLAdapter(BaseSourceAdapter):
    """
    Adapter for extracting article listings from static HTML pages using BeautifulSoup.
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 VyaparNewsBot/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    async def fetch(self, source: Source) -> str:
        url = source.feed_url or source.base_url
        if not url:
            raise ValueError(f"Source {source.id} has no URL configured.")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text

    def parse(self, payload: str, source: Source) -> List[RawArticle]:
        soup = BeautifulSoup(payload, "html.parser")
        raw_articles: List[RawArticle] = []

        # Find article elements or headline links
        article_elements = soup.find_all(["article", "div", "li"], class_=lambda c: c and any(k in c.lower() for k in ["article", "story", "news-item", "post", "card"]))
        
        # Fallback to standard <a> links inside headline containers if no semantic articles found
        if not article_elements:
            article_elements = soup.find_all("h2") + soup.find_all("h3")

        seen_links = set()
        for elem in article_elements:
            link_tag = elem.find("a") if elem.name != "a" else elem
            if not link_tag or not link_tag.get("href"):
                continue

            href = link_tag["href"]
            abs_url = urljoin(source.base_url, href)
            if abs_url in seen_links:
                continue
            seen_links.add(abs_url)

            title = link_tag.get_text(strip=True) or elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            desc_tag = elem.find(["p", "span", "div"], class_=lambda c: c and any(k in c.lower() for k in ["desc", "summary", "excerpt", "snippet"]))
            description = desc_tag.get_text(strip=True) if desc_tag else None

            img_tag = elem.find("img")
            img_url = None
            if img_tag and img_tag.get("src"):
                img_url = urljoin(source.base_url, img_tag["src"])

            time_tag = elem.find(["time", "span"], class_=lambda c: c and any(k in c.lower() for k in ["time", "date", "published"]))
            published_raw = time_tag.get("datetime") or time_tag.get_text(strip=True) if time_tag else None

            raw_articles.append(
                RawArticle(
                    title=title,
                    original_url=abs_url,
                    description=description,
                    published_at_raw=published_raw,
                    image_url=img_url,
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
            extraction_method="html",
            status="published"
        )

    def validate(self, article: CanonicalArticle) -> bool:
        if not article.title or len(article.title) < 5:
            return False
        if not article.canonical_url or not article.canonical_url.startswith("http"):
            return False
        if not article.canonical_url_hash:
            return False
        return True
