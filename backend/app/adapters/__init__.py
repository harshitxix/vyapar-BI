from backend.app.adapters.base import BaseSourceAdapter, RawArticle
from backend.app.adapters.rss.adapter import RSSAdapter
from backend.app.adapters.api.adapter import JSONAPIAdapter
from backend.app.adapters.html.adapter import HTMLAdapter


def get_adapter(source_type: str) -> BaseSourceAdapter:
    """Returns the adapter instance corresponding to the source_type."""
    st = source_type.lower().strip()
    if st == "rss":
        return RSSAdapter()
    elif st == "api":
        return JSONAPIAdapter()
    elif st == "html":
        return HTMLAdapter()
    raise ValueError(f"Unsupported source type: {source_type}")


__all__ = [
    "BaseSourceAdapter",
    "RawArticle",
    "RSSAdapter",
    "JSONAPIAdapter",
    "HTMLAdapter",
    "get_adapter"
]
