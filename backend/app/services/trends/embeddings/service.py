import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.models.trend import ArticleEmbedding
from backend.app.services.trends.embeddings.base import BaseEmbeddingProvider
from backend.app.services.trends.embeddings.fastembed_provider import FastEmbedProvider
from backend.app.services.trends.embeddings.mock_provider import MockEmbeddingProvider
from backend.app.services.trends.embeddings.openai_provider import OpenAIEmbeddingProvider
from backend.app.config.settings import settings

logger = logging.getLogger("vyapar.trends.embeddings")


def get_default_embedding_provider() -> BaseEmbeddingProvider:
    """
    Factory function to instantiate the configured embedding provider.
    Priority: FastEmbed (local ONNX, zero-cost) -> MockProvider (if fastembed fails or mock is set) -> OpenAI (if set).
    """
    provider_type = getattr(settings, "EMBEDDING_PROVIDER", "fastembed").lower()
    
    if provider_type == "openai" and getattr(settings, "OPENAI_API_KEY", None):
        return OpenAIEmbeddingProvider()
    elif provider_type == "mock":
        return MockEmbeddingProvider()
    else:
        try:
            return FastEmbedProvider()
        except Exception as e:
            logger.warning(f"FastEmbed initialization failed ({e}), falling back to MockEmbeddingProvider.")
            return MockEmbeddingProvider()


class EmbeddingService:
    """
    Service responsible for converting enriched articles into vector embeddings
    and persisting them to PostgreSQL/pgvector.
    """

    def __init__(self, provider: Optional[BaseEmbeddingProvider] = None):
        self.provider = provider or get_default_embedding_provider()

    @staticmethod
    def format_article_text(article: Article, enrichment: Optional[ArticleEnrichment]) -> str:
        """
        Creates a normalized, semantically rich text representation of an article for embedding.
        """
        parts = [article.title.strip()]
        
        # Summary
        if enrichment and enrichment.summary:
            parts.append(f"Summary: {enrichment.summary.strip()}")
        elif article.description:
            parts.append(f"Summary: {article.description.strip()}")
            
        # Topics
        if enrichment and enrichment.topics:
            topics_str = ", ".join(str(t) for t in enrichment.topics if t)
            if topics_str:
                parts.append(f"Topics: {topics_str}")
                
        # Entities
        if enrichment and enrichment.entities:
            ent_list = []
            for e in enrichment.entities:
                if isinstance(e, dict):
                    name = e.get("name") or e.get("entity")
                    if name:
                        ent_list.append(name)
                elif isinstance(e, str):
                    ent_list.append(e)
            if ent_list:
                parts.append(f"Entities: {', '.join(ent_list[:10])}")
                
        # Category
        category = (enrichment.category if enrichment and enrichment.category else article.category) or "General"
        parts.append(f"Category: {category}")
        
        return "\n".join(parts)

    async def embed_and_store_articles(
        self, db: AsyncSession, articles_with_enrichment: List[Tuple[Article, Optional[ArticleEnrichment]]]
    ) -> List[ArticleEmbedding]:
        """
        Generates and stores embeddings for a list of (Article, ArticleEnrichment) pairs.
        Skips articles that already have an up-to-date embedding with the current model.
        """
        if not articles_with_enrichment:
            return []

        article_ids = [art.id for art, _ in articles_with_enrichment]

        # Check existing embeddings
        stmt = select(ArticleEmbedding).where(ArticleEmbedding.article_id.in_(article_ids))
        res = await db.execute(stmt)
        existing_map = {emb.article_id: emb for emb in res.scalars().all()}

        to_embed_texts = []
        to_process_pairs = []

        for art, enrichment in articles_with_enrichment:
            existing = existing_map.get(art.id)
            if existing and existing.model == self.provider.model_name and existing.version == self.provider.version:
                continue  # Already embedded with current model & version

            text = self.format_article_text(art, enrichment)
            to_embed_texts.append(text)
            to_process_pairs.append((art, text, existing))

        if not to_embed_texts:
            return list(existing_map.values())

        # Generate vectors
        vectors = await self.provider.embed_texts(to_embed_texts)

        results = []
        for (art, text, existing), vec in zip(to_process_pairs, vectors):
            if existing:
                existing.embedding = vec
                existing.embedding_text = text
                existing.model = self.provider.model_name
                existing.version = self.provider.version
                existing.dimension = self.provider.dimension
                existing.updated_at = datetime.now(timezone.utc)
                results.append(existing)
            else:
                new_emb = ArticleEmbedding(
                    id=str(uuid.uuid4()),
                    article_id=art.id,
                    model=self.provider.model_name,
                    version=self.provider.version,
                    dimension=self.provider.dimension,
                    embedding=vec,
                    embedding_text=text,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(new_emb)
                results.append(new_emb)

        await db.flush()
        return results

    async def get_embeddings_for_articles(
        self, db: AsyncSession, article_ids: List[str]
    ) -> Dict[str, List[float]]:
        """
        Retrieves existing embedding vectors for given article IDs.
        """
        if not article_ids:
            return {}

        stmt = select(ArticleEmbedding).where(ArticleEmbedding.article_id.in_(article_ids))
        res = await db.execute(stmt)
        embeddings = res.scalars().all()
        
        return {
            emb.article_id: list(emb.embedding) if emb.embedding is not None else []
            for emb in embeddings
        }
