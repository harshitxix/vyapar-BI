# Market Intelligence Platform — Specifications (Phases 1–3)

This document consolidates the complete specifications, data contracts, and architectural guardrails across all phases of the Vyapar Market Intelligence platform.

---

## 1. Phase 1: Multi-Source Ingestion & Feed Pipeline

### 1.1 Executive Summary
Build a reliable, multi-source market-intelligence ingestion and feed system for small-business owners (grocery, retail, fashion, FMCG, electronics, etc.).

Phase 1 focuses strictly on deterministic data pipelines:
- Configurable source registry
- Pluggable source adapters (API, RSS/Atom, HTTP/HTML, Playwright)
- Canonical article normalization
- URL canonicalization and multi-level deduplication
- Deterministic keyword & domain relevance filtering
- PostgreSQL storage with SQLAlchemy & Alembic
- Async FastAPI REST API (`/feed`, `/articles`, `/sources`, `/ingestion/refresh`, `/health`)
- Background polling scheduler (APScheduler)
- Ingestion run tracking and source health monitoring
- Mobile-first consumer app (React Native / Expo)

### 1.2 Ingestion Pipeline Flow
```text
SOURCE REGISTRY
      ↓
SOURCE SELECTION (Polling due / Manual refresh)
      ↓
FETCH (HTTPX / Feedparser / Playwright with timeouts & retries)
      ↓
PARSE (Format-specific parser)
      ↓
NORMALIZE (Title, description, UTC timestamps, author, image)
      ↓
VALIDATE (Pydantic schema validation)
      ↓
CANONICALIZE URL (Strip UTM / tracking query params)
      ↓
DUPLICATE CHECK (Exact URL/Title hash + Near-duplicate fingerprint)
      ↓
STORE (PostgreSQL transaction)
      ↓
UPDATE SOURCE HEALTH & INGESTION RUN METRICS
```

### 1.3 Core Acceptance Criteria
1. At least 5 active sources configured across relevant domains (retail/grocery/FMCG/business).
2. End-to-end automated polling runs independently per source interval.
3. Manual force-refresh endpoint `POST /ingestion/refresh` triggers asynchronous ingestion cycle.
4. Duplicate articles are detected and rejected.
5. Ingestion failures on one source do not crash the pipeline.
6. Unified `/feed` and `/articles` endpoints return normalized articles with filters (domain, region, category, date).
7. Expo React Native mobile feed displays articles with pull-to-refresh and pagination.
8. Zero LLM dependency for basic ingestion and scraping.

---

## 2. Phase 2: AI Article Understanding & Enrichment Layer

### 2.1 Executive Summary
Phase 2 builds an asynchronous AI enrichment and understanding pipeline on top of Phase 1's clean ingestion engine. It transforms raw article metadata into structured, machine-readable market intelligence stored in PostgreSQL.

**Core Contract**:
> `INGEST ONCE → UNDERSTAND ONCE → STORE STRUCTURED INTELLIGENCE → REUSE EVERYWHERE`

### 2.2 Enrichment Data Contract
For every eligible article, the AI enrichment layer extracts:
1. **Factual Summary**: 2–4 sentence objective summary without speculation or prescriptive business advice.
2. **Business Domain**: Primary and secondary taxonomy classification (`grocery`, `retail`, `fashion`, `technology`, `electronics`, `restaurants`, `manufacturing`, `general_business`, etc.).
3. **Category & Subcategory**: Taxonomy categorization (`Market`, `Consumer`, `Pricing`, `Product Launch`, `Regulation`, `Supply Chain`, `Expansion`, etc.).
4. **Topics**: 3–8 normalized, reusable topics for future trend clustering.
5. **Keywords**: Concise search/filter terms stripped of generic stopwords.
6. **Named Entities**: Extracted entities typed as `COMPANY`, `BRAND`, `PRODUCT`, `PERSON`, `LOCATION`, `ORGANIZATION`, `MARKET`, or `INDUSTRY`.
7. **Key Events**: Discrete business events (`product_launch`, `company_expansion`, `funding`, `regulatory_change`, `price_change`, `market_growth`, etc.) with description and date if known.
8. **Relevance Score**: 0.0 – 1.0 scoring the relevance of the story to retail/kirana/small business owners.
9. **Confidence Estimate**: 0.0 – 1.0 estimate of classification reliability.
10. **Observability & Cost**: Model name, prompt version, input/output tokens, latency (ms), and cost tracking.

### 2.3 Asynchronous Pipeline Architecture
```text
Article Ingested (PostgreSQL)
        ↓
Eligibility Check (status: pending / queued)
        ↓
Content Preparation & Prompt Sanitization (Prompt injection defense)
        ↓
LLM Provider Abstraction (Single unified JSON prompt)
        ↓
Pydantic Schema Validation & Confidence Guard
        ↓
Store in article_enrichment Table (status: completed / failed)
        ↓
Expose in /feed & /articles REST APIs
        ↓
Render enriched metadata in Mobile UI
```

### 2.4 Non-Blocking & Failure Isolation Guarantees
- Ingestion runs continuously even if the LLM provider is down.
- Feed API queries database directly; zero LLM calls during feed load.
- Failed enrichment attempts retry with exponential backoff up to 3 times, then mark as `failed`.
- Admin reprocessing endpoints allow manual or batch re-enrichment.

---

## 3. Phase 3: Market-Level Intelligence & Emerging Trend Engine

### 3.1 Executive Summary
Phase 3 transforms individually enriched Phase 2 articles into **Market-Level Intelligence**. It continuously detects, measures, verifies, tracks, and explains emerging market trends across retail, FMCG, grocery, and consumer technology sectors in India.

**Core Contract**:
> `ALGORITHMS DETECT → EVIDENCE VERIFIES → LLM EXPLAINS → PERSIST & TRACK OVER TIME`

### 3.2 Core Architecture Pipeline
```text
Phase 2 Enriched Articles (PostgreSQL)
        ↓
Normalized Semantic Text & Metadata
        ↓
Embedding Generation (pgvector / FastEmbed / MiniLM ONNX)
        ↓
Candidate Trend Grouping (Topics, Entities, Domains, Windows)
        ↓
Semantic Similarity & Vector Clustering (Cosine / Agglomerative / HDBSCAN)
        ↓
Noise Rejection & Minimum Evidence Filters (Articles ≥ 3, Sources ≥ 2, Coherence)
        ↓
Temporal Analysis (Velocity, Acceleration, Burst vs Baseline)
        ↓
Deterministic Scoring & Lifecycle State (Emerging, Growing, Established, Cooling, Declining)
        ↓
LLM Grounded Synthesis (Name, Narrative, Why Emerging — Zero Hallucination)
        ↓
Persistent Trend Storage & Versioned Snapshots (trends, trend_articles, trend_snapshots)
        ↓
REST APIs (/trends, /trends/{id}, /trends/timeline, /admin/trends)
        ↓
Mobile Trends Feed & Interactive Trend Intelligence Reader
```

### 3.3 Strict Architectural Guardrails
1. **Algorithms Detect, LLM Explains**: Trend discovery is purely statistical and algorithmic. The LLM is invoked only to synthesize human-readable descriptions of mathematically verified clusters.
2. **Deterministic Quality & Evidence**:
   - Minimum supporting articles: $\ge 3$.
   - Minimum independent sources: $\ge 2$.
   - Minimum semantic coherence threshold.
   - Rejects isolated PR blasts or single-publisher spam.
3. **No Business Recommendations in Phase 3**: Focuses exclusively on market intelligence (describing macro patterns, not prescribing inventory/sales advice).
4. **Non-Blocking Execution**: Trend computation runs as an incremental background task (every 15–30 min) without delaying feed queries or ingestion.

### 3.4 Phase 3 Milestones & Deliverables
| Milestone | Description |
|---|---|
| **Step 21** | System Specifications & Trend Engine Architecture (`TREND_ENGINE.md`, `PHASE_SPECS.md`) |
| **Step 22** | Database Layer: `article_embeddings`, `trends`, `trend_articles`, `trend_snapshots`, `trend_analysis_runs` |
| **Step 23** | Embedding Service & Provider Abstraction (`BaseEmbeddingProvider`, FastEmbed/MiniLM, OpenAI, Mock) |
| **Step 24** | Similarity & Clustering Service (Cosine distance, Agglomerative clustering, Noise isolation) |
| **Step 25** | Temporal Analysis & Momentum Burst Detector (Daily/weekly velocity, acceleration, baseline delta) |
| **Step 26** | Deterministic Trend Scoring & Lifecycle State Machine (`emerging`, `growing`, `established`, `cooling`, `declining`) |
| **Step 27** | LLM Grounded Trend Synthesis (Evidence-only prompts, zero hallucination, naming & description) |
| **Step 28** | Trend Persistence, Incremental Updates & Snapshot History |
| **Step 29** | Trend REST APIs (`GET /trends`, `GET /trends/{id}`, `GET /trends/timeline`, `POST /admin/trends/rebuild`) |
| **Step 30** | Mobile Trends Client & Interactive Trend Cards |
| **Step 31** | Golden Trend Test Benchmark & Quality Validation Suite |
| **Step 32** | End-to-End Acceptance Verification & Documentation Lock |

---

## 4. Future Phases Roadmap (Out of Scope for Phase 3)

The following capabilities belong to subsequent phases:
- **Phase 4: Actionable Business Insights & Advisory**: Tailored inventory recommendations, pricing sensitivity analysis, SKU demand forecasting, and store-type personalized notifications.
- **Phase 5: Merchant Conversational Co-pilot**: Multi-turn dialogue agent with domain memory, supplier intelligence, and WhatsApp merchant integration.

