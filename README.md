# Vyapar BI

A production-grade, AI-powered market intelligence feed and emerging trend detection platform tailored for retail, kirana, grocery, and FMCG businesses in India.

---

## System Architecture

The platform operates on a modular, decoupled, asynchronous pipeline designed for high throughput, zero-hallucination factual synthesis, and low-latency personalized delivery.

```mermaid
graph TD
    subgraph Ingestion [1. Multi-Source Ingestion]
        S1[Economic Times Retail]
        S2[Livemint]
        S3[Inc42]
        S4[Financial Express]
        S5[Business Standard]
        Pipeline[Ingestion Pipeline - APScheduler]
        Dedupe[Deduplication Engine - SHA256 and SimHash]
        
        S1 --> Pipeline
        S2 --> Pipeline
        S3 --> Pipeline
        S4 --> Pipeline
        S5 --> Pipeline
        Pipeline --> Dedupe
    end

    subgraph Storage [Database Layer]
        DB[(PostgreSQL Database)]
    end

    subgraph Enrichment [2. AI Enrichment and Vectorization]
        AIWorker[AI Enrichment Worker - Groq LPU]
        AIOutput[Factual Summaries, Taxonomy, Kirana Score]
        EmbedWorker[Embedding Service - FastEmbed ONNX]
        
        AIWorker --> AIOutput
    end

    subgraph Intelligence [3. Trend Discovery Engine]
        Cluster[Agglomerative Clustering - Noise Filtering]
        Temporal[Temporal Velocity and Momentum]
        Synthesis[Grounded LLM Synthesis]
        
        Cluster --> Temporal
        Temporal --> Synthesis
    end

    subgraph Personalization [4. Personalization and Delivery]
        CandidateGen[Candidate Generation - Top 150]
        Scorer[Deterministic 8-Signal Scoring]
        Diversity[Sliding-Window Diversity Re-Ranking]
        API[FastAPI REST Endpoints]
        Mobile[React Native Mobile App - Expo]
        
        CandidateGen --> Scorer
        Scorer --> Diversity
        Diversity --> API
        API --> Mobile
    end

    Dedupe --> DB
    DB --> AIWorker
    AIOutput --> DB
    DB --> EmbedWorker
    EmbedWorker --> DB
    DB --> Cluster
    Synthesis --> DB
    DB --> CandidateGen
```

---

## Pipeline Flowchart

The detailed data flow from raw feed capture to client-side adaptive presentation is illustrated below:

```mermaid
graph LR
    A[Raw Feeds] --> B[Canonical Normalization]
    B --> C{Is Duplicate?}
    C -->|Yes| D[Discard]
    C -->|No| E[Persist Raw Article]
    E --> F[Async AI Worker - Groq]
    F --> G[Extract Entities and Scores]
    G --> H[FastEmbed Vectorization]
    H --> I[Periodic Trend Run]
    I --> J[Semantic Clusters]
    J --> K[Temporal Scoring]
    K --> L[Personalization Engine]
    L --> M[FastAPI Gateway]
    M --> N[Mobile Client Feed]
```

---

## Phase-Wise Progression and Milestones

The project is developed in structured phases, each delivering verifiable end-to-end functionality backed by automated test suites.

```mermaid
graph LR
    P1[Phase 1: Ingestion Engine<br/>Status: COMPLETED] --> P2[Phase 2: AI Enrichment<br/>Status: COMPLETED]
    P2 --> P3[Phase 3: Trend Intelligence<br/>Status: COMPLETED]
    P3 --> P4[Phase 4: Personalization<br/>Status: COMPLETED]
    P4 --> P5[Phase 5: Real-Time Alerts<br/>Status: PLANNED]
    P5 --> P6[Phase 6: Multi-Tenant Scale<br/>Status: PLANNED]
```

### Phase Progression Summary

| Phase | Milestone Name | Key Deliverables | Status | Test Coverage |
|---|---|---|---|---|
| Phase 1 | Ingestion Engine & Feed Pipeline | RSS/REST/HTML adapters, SHA256 & SimHash deduplication, PostgreSQL storage, APScheduler polling, baseline FastAPI REST API, React Native Expo mobile MVP. | COMPLETED | Automated unit & integration tests passing (100%) |
| Phase 2 | AI Article Enrichment Layer | Groq LPU inference, structured Pydantic schemas, prompt injection protection, Kirana business match scoring (0-100), automated 30s background processor, enriched mobile card UI. | COMPLETED | Golden test suite, schema validation tests passing (100%) |
| Phase 3 | Market Intelligence & Emerging Trends | Local FastEmbed ONNX embeddings, Agglomerative clustering, noise thresholding, temporal momentum detector, grounded synthesis, lifecycle state machine, mobile Trends tab. | COMPLETED | Clustering evaluation, temporal scoring tests passing (100%) |
| Phase 4 | Personalization & Adaptive Feed Engine | 12-domain Kirana taxonomy, canonical entity registry, user market profiles, deterministic 8-signal scoring, freshness decay, sliding-window diversity re-ranking, 14-day feedback decay, explainability badges. | COMPLETED | Persona separation benchmark (0% top-5 overlap), 15/15 tests passing |
| Phase 5 | Real-Time Alerts & Notifications | Breaking trend push notifications, user threshold triggers, daily business digests via WhatsApp/SMS/mobile push. | PLANNED | Pending kickoff |
| Phase 6 | Multi-Tenant Cloud Scale | Distributed Celery/Redis queue, horizontal microservice isolation, multi-region replication, full Prometheus/Grafana observability. | PLANNED | Pending kickoff |

---

### Detailed Phase Breakdown

#### Phase 1: Ingestion Engine and Feed Pipeline (Completed)
- Pluggable source adapter architecture supporting RSS, REST APIs, and HTML scrapers.
- Multi-tier deduplication utilizing canonical URL normalization, SHA256 content hashing, and 64-bit Hamming SimHash for near-duplicate text detection.
- Non-blocking periodic polling managed by APScheduler with per-source scheduling and retry policies.
- Relational schema implemented via SQLAlchemy 2.0 asyncpg and Alembic migrations.
- Mobile client built using React Native and Expo with domain filtering and pull-to-refresh.

#### Phase 2: AI Article Understanding and Enrichment (Completed)
- LLM inference service powered by Groq LPU (Llama 3 / Mixtral) with OpenAI fallback capability.
- Security-first prompt sanitization and strict JSON output validation via Pydantic v2 schemas.
- Automatic extraction of factual 2-4 sentence executive summaries, structured topic taxonomies, named entities (companies, brands, government bodies), and retail relevance scores (0-100).
- Asynchronous batch worker operating independently of ingestion to prevent pipeline bottlenecks.
- Extended mobile cards displaying relevance tags, executive summaries, and entity pills.

#### Phase 3: Market Intelligence and Emerging Trend Engine (Completed)
- On-device local dense vector generation using FastEmbed (MiniLM ONNX) with zero per-token cost and high throughput.
- Agglomerative Hierarchical Clustering with cosine distance thresholding and noise rejection (requiring at least 3 distinct articles across 2 or more independent publishers).
- Temporal dynamics engine tracking article volume acceleration, velocity baselines, and burst momentum.
- Grounded factual synthesis utilizing constrained LLM prompts for hallucination-free trend titles, narratives, and key developments.
- Deterministic trend lifecycle management (`emerging` -> `growing` -> `established` -> `cooling` -> `declining`).
- Dedicated mobile Trends explorer with interactive timeline history and source attribution.

#### Phase 4: Personalized Market Intelligence and Adaptive Feed Engine (Completed)
- Comprehensive Kirana taxonomy covering 12 core domains (kirana grocery, FMCG, quick commerce, dairy, packaging, logistics, agri commodities, retail tech, edible oils, beverages, confectionery, spices) with fine-grained subdomains.
- Canonical entity registry seeding leading Indian brands, FMCG conglomerates, and logistics networks with follow/unfollow functionality.
- Deterministic 8-signal candidate scoring algorithm balancing domain relevance, topic overlap, entity follows, geography, store scale, supplier mentions, general kirana score, and exponential freshness decay (tau = 48 hours).
- Decoupled trend blending merging user profile alignment (70%) with raw market trend velocity (30%).
- Anti-fatigue diversity re-ranking algorithm enforcing sliding-window penalties across identical publishers, topics, and entities.
- Implicit and explicit feedback loop with bounded adjustments and 14-day exponential half-life decay.
- Human-interpretable explainability layer rendering grounded reason badges on feed items.
- Rigorous golden evaluation suite demonstrating 0% cross-persona overlap in top-5 ranked articles among diverse user profiles.

---

## Repository Structure

```text
vyapar/
|-- .env.example              # Environment configuration template (sanitized)
|-- .gitignore                # Git ignore rules for secrets, builds, and dependencies
|-- ARCHITECTURE.md           # Deep-dive architecture and component design
|-- CHANGELOG.md              # Versioned release notes across all phases
|-- DATA_MODEL.md             # Complete PostgreSQL schema and entity relationships
|-- FEED_RANKING.md           # Personalization formulas, weights, and diversity logic
|-- PERSONALIZATION_ENGINE.md # Phase 4 personalization engine comprehensive guide
|-- PHASE_SPECS.md            # Technical specifications for Phases 1 through 3
|-- PROJECT_TRACKER.md        # Detailed 52-step milestone execution audit log
|-- TECH_STACK.md             # Technology stack selection rationale
|-- TREND_ENGINE.md           # Trend mathematical models and lifecycle state machine
|-- USER_PROFILE.md           # User profile schema and canonical entity models
|-- alembic.ini               # Database migration configuration
|-- docker-compose.yml        # PostgreSQL container service configuration
|-- pytest.ini                # Pytest runner configuration
|-- backend/
|   |-- alembic/              # Database schema migration revisions
|   |-- app/
|   |   |-- adapters/         # Feed ingestion adapters (RSS, REST, HTML)
|   |   |-- api/              # FastAPI router endpoints (feed, trends, users, admin)
|   |   |-- config/           # Application configuration and environment loading
|   |   |-- database/         # Async database engine and session managers
|   |   |-- models/           # SQLAlchemy ORM models (articles, trends, users, profiles)
|   |   |-- scheduler/        # APScheduler background tasks
|   |   |-- schemas/          # Pydantic validation schemas
|   |   |-- services/         # Core business logic
|   |   |   |-- ai/           # LLM enrichment and prompt guardrails
|   |   |   |-- ingestion/    # Feed polling, deduplication, and pipeline
|   |   |   |-- personalization/ # Candidate generation, scoring, diversity, feedback
|   |   |   `-- trends/       # Embeddings, clustering, temporal math, synthesis
|   |   `-- utils/            # Hashing, text normalization, and date parsers
|   |-- scripts/              # Seed scripts for sources, taxonomy, and entities
|   `-- tests/                # Automated unit, integration, and acceptance tests
`-- mobile/
    |-- App.tsx               # Main mobile client application root
    |-- app.json              # Expo application configuration
    |-- metro.config.js       # Metro bundler reverse proxy configuration
    |-- package.json          # Node dependencies
    `-- src/
        |-- api/              # Axios client and API integration hooks
        |-- components/       # UI components (cards, modals, filters, onboarding)
        `-- types/            # TypeScript type definitions
```

---

## Security and Secret Protection

This repository strictly enforces secret management best practices:
- No sensitive credentials, private keys, or API tokens are tracked in version control.
- Configuration is loaded at runtime via `.env`, which is permanently excluded via `.gitignore`.
- `.env.example` provides a sanitized template with placeholder values for setup.
- If you suspect an API key was previously used in development, immediately rotate it in the provider console before deployment.

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.12+ (configured in virtual environment `.venv`)
- Docker (for local PostgreSQL container)
- Node.js 18+ and npm (for Expo mobile client)
- Groq Cloud API Key (or OpenAI API Key) for AI enrichment and trend synthesis

### 2. Environment Configuration
Create a `.env` file in the project root by copying the template:

```bash
cp .env.example .env
```

Edit `.env` and provide your credentials:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/vyapar_db
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/vyapar_db
GROQ_API_KEY=your_actual_groq_api_key_here
```

### 3. Backend Service Startup
```bash
# Activate virtual environment (Windows PowerShell)
.venv\Scripts\activate

# Start PostgreSQL database container
docker-compose up -d

# Run database migrations / seed data (if initial setup)
python backend/scripts/seed_sources.py
python backend/scripts/seed_taxonomy.py
python backend/scripts/seed_entities.py

# Start FastAPI application server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- Personalized Feed: `http://localhost:8000/feed/for-you`
- Trends Endpoint: `http://localhost:8000/trends`

### 4. Mobile Client Startup (React Native Expo)
```bash
cd mobile
npm install
npm start
```
- Press `w` to run in a web browser.
- Scan the printed QR code using the Expo Go mobile application on Android or iOS.

### 5. Running Automated Tests
```bash
# Run all unit, integration, and golden evaluation tests
.venv\Scripts\pytest backend\tests\ -v
```

---

## Core API Endpoints

| Category | Method | Endpoint | Description |
|---|---|---|---|
| Health | `GET` | `/health` | Service health status and database connectivity |
| Feed | `GET` | `/feed/for-you` | Personalized article feed with explainability reasons |
| Feed | `GET` | `/feed/latest` | Reverse-chronological raw feed with taxonomy filters |
| Feed | `GET` | `/feed/following` | Articles matching user-followed entities |
| Trends | `GET` | `/trends` | Global active market trends with strength and confidence |
| Trends | `GET` | `/trends/for-you` | Context-blended trends tailored to user market profile |
| Trends | `GET` | `/trends/{id}` | Detailed trend metrics, narrative, and source evidence |
| Trends | `GET` | `/trends/{id}/timeline`| Snapshot historical evolution of a specific trend |
| Ingestion | `POST`| `/ingestion/refresh` | Trigger asynchronous manual feed fetch across sources |
| Admin | `POST`| `/admin/trends/rebuild`| Force manual execution of trend clustering pipeline |
| Users | `GET` | `/users/me/market-profile` | Retrieve authenticated user business profile |
| Users | `POST`| `/users/me/market-profile` | Create or update user market profile |
| Users | `GET` | `/taxonomy/domains` | Fetch all 12 domains, subdomains, and suggested topics |
| Users | `GET` | `/entities` | Browse canonical entities registry |
| Feedback | `POST`| `/interactions` | Record user interaction event (view, read, bookmark) |
| Privacy | `POST`| `/users/me/preferences/reset` | Reset learned weights to baseline profile |


Made with efforts by @harshitxix
