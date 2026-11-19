from abc import ABC, abstractmethod
from typing import Any, List, Optional
from pydantic import BaseModel

from backend.app.schemas.article import CanonicalArticle
from backend.app.models.source import Source


class RawArticle(BaseModel):
    title: str
    original_url: str
    description: Optional[str] = None
    author: Optional[str] = None
    published_at_raw: Optional[Any] = None
    image_url: Optional[str] = None
    raw_category: Optional[str] = None
    raw_data: Optional[dict] = None


class BaseSourceAdapter(ABC):
    """
    Abstract interface for all source adapters (RSS, API, HTML, Playwright).
    """

    @abstractmethod
    async def fetch(self, source: Source) -> Any:
        """Fetch raw content from the source endpoint."""
        pass

    @abstractmethod
    def parse(self, payload: Any, source: Source) -> List[RawArticle]:
        """Parse the raw payload into a list of intermediate RawArticle objects."""
        pass

    @abstractmethod
    def normalize(self, raw: RawArticle, source: Source) -> CanonicalArticle:
        """Convert a RawArticle into the standardized CanonicalArticle schema."""
        pass

    @abstractmethod
    def validate(self, article: CanonicalArticle) -> bool:
        """Validate that the canonical article meets all required quality constraints."""
        pass
