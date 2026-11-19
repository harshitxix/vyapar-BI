# System Architecture & Technology Stack

This document details the system design, component architecture, execution models, and technology stack for the Vyapar Market Intelligence platform across all implemented phases.

---

## 1. System Overview

The system is decoupled into modular layers with explicit interface contracts:

```text
┌─────────────────────────────────────────────────────────────┐
│                      Mobile Client                          │
│         (React Native / Expo App — iOS & Android)           │
│         [Tabs: Latest News Feed  |  Market Trends 🔥]        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                         │
│  ┌──────────────────────┬────────────────────────────────┐  │
│  │   Feed & Article API │      Trends & Intelligence API │  │
│  │ (/feed, /articles)   │ (/trends, /trends/{id}, /admin)│  │
│  └──────────┬───────────┴────────────────┬───────────────┘  │
└─────────────┼────────────────────────────┼──────────────────┘
              │                            │
              ▼                            ▼
┌───────────────────────────┐ ┌───────────────────────────────┐
│     Feed Service          │ │   Background Scheduler & Runs │
│ (Ranking & Filter Logic)  │ │      (APScheduler async)      │
└─────────────┬─────────────┘ └────────────┬──────────────────┘
              │                            │
              │         ┌──────────────────┴──────────────────┐
              │         ▼                                     ▼
              │  ┌───────────────┐                     ┌──────────────┐
              │  │IngestionEngine│                     │ TrendEngine  │
              │  └──────┬────────┘                     └──────┬───────┘
              │         │                                     │
              │         ▼                                     ▼
              │  ┌───────────────┐                     ┌──────────────┐
              │  │Source Adapters│                     │Clustering &  │
              │  │(RSS/API/HTML) │                     │Temporal Score│
              │  └──────┬────────┘                     └──────┬───────┘
              │         │                                     │
              │         ▼                                     ▼
              │  ┌───────────────┐                     ┌──────────────┐
              │  │ Deduplication │                     │ Grounded LLM │
              │  │& Normalization│                     │  Synthesis   │
              │  └──────┬────────┘                     └──────┬───────┘
              │         │                                     │
              ▼         ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Storage                       │
│  - Sources, Articles, IngestionRuns, SourceHealth           │
│  - ArticleEnrichment (AI metadata, topics, entities)        │
│  - ArticleEmbeddings, Trends, TrendArticles, TrendSnapshots  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose & Justification | Where Used |
|---|---|---|---|---|
| **Backend Language** | Python | 3.12+ | High performance, rich ecosystem for async ingestion, NLP, and clustering | Entire Backend |
| **API Framework** | FastAPI | >=0.116.0 | High-speed async REST framework, automatic OpenAPI docs, Pydantic validation | `backend/app/api/` |
| **ASGI Server** | Uvicorn | >=0.35.0 | Async server runtime for FastAPI | `backend/app/main.py` |
| **Data Validation** | Pydantic | >=2.11.0 | Strong typing, serialization, and canonical schema validation | `backend/app/schemas/` |
| **ORM & Database** | SQLAlchemy (Async) | >=2.0.0 | Async ORM, connection pooling, and declarative models | `backend/app/database/`, `backend/app/models/` |
| **Database Migrations** | Alembic | >=1.13.0 | Versioned relational schema migrations | `backend/alembic/` |
| **Database Engine** | PostgreSQL | 16+ | ACID-compliant relational storage, JSONB indexing, vector support | Core Storage |
| **Vector Embeddings** | FastEmbed / ONNX | >=0.8.0 | Zero-cost local CPU embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions) | `backend/app/services/trends/embeddings/` |
| **Machine Learning** | Scikit-learn & NumPy | >=1.9.0 | Agglomerative clustering, cosine metrics, and Simpson diversity calculations | `backend/app/services/trends/` |
| **LLM Provider (AI)** | Groq LPU / OpenAI | API | Ultra-fast JSON inference (`openai/gpt-oss-20b`) for enrichment & trend synthesis | `backend/app/services/ai/providers/` |
| **HTTP Client** | HTTPX | >=0.28.0 | Async HTTP client with connection pooling, retries, and timeouts | `backend/app/adapters/`, `api/` |
| **Feed Parser** | feedparser | >=6.0.11 | Standardized parsing for RSS 1.0/2.0 and Atom feeds | `backend/app/adapters/rss/` |
| **HTML Parser** | BeautifulSoup4 / lxml | >=4.12.0 | Static HTML scraping, DOM traversal, and tag stripping | `backend/app/adapters/html/` |
| **Browser Scraper** | Playwright | Async | Headless Chromium for JS-rendered websites (used selectively) | `backend/app/adapters/playwright/` |
| **Background Scheduler** | APScheduler | >=3.10.0 | In-process async scheduler for recurring ingestion, enrichment, and trend jobs | `backend/app/scheduler/` |
| **Mobile Client** | React Native + Expo | SDK 57+ | Cross-platform mobile feed & trend explorer UI | `mobile/` |
| **Mobile Language** | TypeScript | >=5.0.0 | Strict typing across mobile components and API client | `mobile/` |

---

## 3. Ingestion & Adapter Contract

Every ingestion adapter implements the `BaseSourceAdapter` abstract interface:

```python
class BaseSourceAdapter(ABC):
    @abstractmethod
    async def fetch(self, source: SourceConfig) -> RawPayload:
        """Fetch raw content with timeouts, retries, and rate limits."""
        pass

    @abstractmethod
    def parse(self, payload: RawPayload) -> List[RawArticle]:
        """Parse raw content (XML, JSON, HTML) into intermediate structures."""
        pass

    @abstractmethod
    def normalize(self, raw: RawArticle, source: SourceConfig) -> CanonicalArticle:
        """Convert into CanonicalArticle schema with UTC timestamps & clean text."""
        pass

    @abstractmethod
    def validate(self, article: CanonicalArticle) -> bool:
        """Validate required fields and content integrity."""
        pass
```

---

## 4. Multi-Level Deduplication Strategy

1. **Level 1 (Exact Match)**:
   - `canonical_url_hash`: SHA256 of cleaned canonical URL (stripped of UTM parameters, session tokens, trailing hashes).
   - `normalized_title_hash`: SHA256 of lowercase, punctuation-stripped, whitespace-collapsed title.
2. **Level 2 (Near-Duplicate Fingerprint)**:
   - SimHash / N-gram token fingerprint on title + first 200 characters of description.
   - Low confidence matches are preserved rather than falsely merged.

---

## 5. Scheduling & Execution Model

The system runs three asynchronous recurring jobs managed by `SchedulerManager` (`APScheduler`):
1. **Source Polling Worker**: Evaluates due sources according to each source's configured `refresh_interval` (default: 600s – 1200s).
2. **AI Enrichment Worker**: Runs every 30 seconds to process pending articles in non-blocking batches.
3. **Trend Detection Worker**: Runs every 30 minutes to cluster active articles, compute temporal velocity, calculate strength scores, and synthesize new/updated market trends.

Manual force-refreshes (`POST /ingestion/refresh` and `POST /admin/trends/rebuild`) spawn background tasks that execute immediately without blocking API consumers.

---

## 6. Personalization & Adaptive Feed Engine (Phase 4)

Phase 4 introduces a dedicated Personalization and Ranking subsystem decoupled from ingestion and clustering:

```text
               Authenticated User Context
                           │
                           ▼
                 User Market Profile
         (Business Domain, Location, Interests, Follows)
                           │
                           ▼
              Candidate Generation Service
       (Indexed DB queries for recent & matching articles)
                           │
                           ▼
              Article Relevance Scoring
          (Deterministic 8-signal linear scoring)
                           │
                           ▼
               Trend Relevance Scoring
   (Combines Phase 3 Market Strength with Phase 4 User Relevance)
                           │
                           ▼
               Diversity & Anti-Fatigue Filter
          (Sliding-window penalties for sources & topics)
                           │
                           ▼
                 Explainability Layer
         (Generates factual reasons from winning signals)
                           │
                           ▼
        Personalized "For You" Feed & Market Sections
```

### Key Architectural Invariants
1. **Separation of Trend Strength vs. User Relevance**: Phase 3 determines how strong a trend is globally. Phase 4 determines how relevant that trend is to an individual user.
2. **Determinism**: Given the same user profile and article candidates, the ranking engine produces a 100% deterministic ordering.
3. **Graceful Fallback**: If personalization fails or a user skips onboarding, the chronological feed is returned seamlessly.
4. **Resilient Mobile Bridge**: Routes all mobile requests through the Metro reverse proxy on port 8081, ensuring complete compatibility over Wi-Fi and tunnels.
