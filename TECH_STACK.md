# Vyapar Market Intelligence — Technology Stack Reference

This document provides the canonical technical inventory, dependencies, runtime environments, and architecture boundaries for the Vyapar Market Intelligence platform across all implemented phases.

---

## 1. Backend Stack

| Category | Component | Version | Purpose & Rationale |
|---|---|---|---|
| **Runtime** | Python | 3.12+ | High performance, async support, scientific libraries. |
| **API Framework** | FastAPI | >=0.116.0 | Modern async ASGI framework with Pydantic validation & OpenAPI docs. |
| **Server** | Uvicorn | >=0.35.0 | Async event-loop server for FastAPI. |
| **Database** | PostgreSQL | 16+ | Relational data, ACID integrity, JSONB indexing, and pgvector. |
| **ORM** | SQLAlchemy (Async) | >=2.0.0 | Async connection pooling and declarative relational mapping. |
| **Migrations** | Alembic | >=1.13.0 | Versioned database schema evolution. |
| **Authentication** | PyJWT | >=2.8.0 | Lightweight stateless JWT tokens & user context propagation. |
| **Validation** | Pydantic / Pydantic Settings | >=2.11.0 | Canonical request/response schemas and environment configuration. |
| **Vector Engine** | FastEmbed (ONNX) | >=0.8.0 | Zero-cost local CPU embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions). |
| **Analytics/ML** | Scikit-learn & NumPy | >=1.9.0 | Agglomerative clustering, cosine metrics, and Simpson diversity calculations. |
| **AI LLM Client** | Groq LPU / OpenAI | API | Sub-second JSON inference (`openai/gpt-oss-20b` / `gpt-4o-mini`). |
| **HTTP Client** | HTTPX | >=0.28.0 | Async connection-pooled HTTP client for scraping and webhooks. |
| **Scheduler** | APScheduler | >=3.10.0 | In-process asynchronous task scheduler for background workers. |

---

## 2. Mobile Client Stack

| Category | Component | Version | Purpose & Rationale |
|---|---|---|---|
| **Framework** | React Native | 0.88.1 | Cross-platform native mobile UI engine. |
| **Toolchain** | Expo | SDK 58.0.25 | Standardized build and deployment toolchain with Hermes engine. |
| **Language** | TypeScript | 5.9.3 | Strict type contracts matching backend Pydantic models. |
| **Icons** | Lucide React Native | 0.468.0 | Modern vector iconography. |
| **HTTP Client** | Axios | 1.7.9 | Request interceptors and dynamic base URL resolution across LAN/tunnel. |
| **Development Server**| Metro Bundler | SDK 58 | Bundler with custom reverse-proxy middleware to FastAPI. |

---

## 3. Strict Architectural Boundaries

- **No Redis Dependency**: Background workers and scheduling run efficiently in-process using APScheduler and PostgreSQL connection pools.
- **No External Vector Database**: All embeddings and clustering operate locally via FastEmbed ONNX and PostgreSQL relational models.
- **No Heavy Multi-Agent Frameworks**: LLM inference and enrichment use deterministic, prompt-grounded functions with zero hallucinations.
- **Zero Paid Subscriptions**: Fully reproducible with local open-source models and standard developer environments.
