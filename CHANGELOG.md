# Changelog

All notable changes to the Market Intelligence Feed project will be documented in this file.

## [0.4.0] - 2026-11-18
### Added
- **Phase 4 Personalization Architecture Specification**: Created `USER_PROFILE.md`, `FEED_RANKING.md`, `PERSONALIZATION_ENGINE.md`, and `TECH_STACK.md`.
- **Relational Data Model Expansion**: Defined and implemented 8 SQLAlchemy 2.0 async models (`users`, `user_market_profiles`, `canonical_entities`, `user_entity_follows`, `user_topic_preferences`, `user_feed_preferences`, `user_interaction_events`, `user_learned_preferences`) in `backend/app/models/personalization.py`.
- **Domain & Subdomain Taxonomy**: Created `TaxonomyService` supporting 12 primary retail/business domains, subdomains, suggested onboarding topics, normalization, and domain similarity matrices.
- **Canonical Entity Registry**: Created `EntityFollowService` seeded with 14 Indian business entities (Blinkit, Zepto, Reliance Retail, DMart, etc.), alias matching, article detection, and follow subscriptions.
- **Deterministic 8-Signal Ranking Formulation**: Implemented `ArticleRelevanceService` with mathematically normalized signals ($[0.0, 1.0]$) combining domain match, subdomain, followed topics, followed entities, geographic relevance, trend alignment, article quality, and exponential freshness decay ($\tau = 48\text{h}$).
- **Decoupled Trend Relevance Blending**: Implemented `TrendRelevanceService` preserving Phase 3 market trend strength ($S_{market}$) strictly distinct from individual user relevance ($R_{user}$), blended via $S_{final} = 0.70 \cdot R_{user} + 0.30 \cdot S_{market}$.
- **Diversity & Anti-Fatigue Re-Ranking**: Built `DiversityService` implementing sliding-window source, topic, and entity repetition penalties with high-relevance score exemptions.
- **Adaptive Feedback Engine**: Implemented `FeedbackService` logging immutable interaction audit streams (`click`, `dwell`, `bookmark`, `share`, `not_interested`) and maintaining bounded learned preference scores ($[0.0, 1.0]$) with a 14-day exponential half-life decay towards neutral 0.5.
- **FastAPI Endpoints**:
  - `GET /feed/for-you`: Primary personalized feed blending articles and high-relevance market trends with grounded explainability badges.
  - `GET /feed/following`: Dedicated feed filtered to explicitly followed topics and entities.
  - `GET /trends/for-you`: Market trends re-ranked by user business context.
  - `GET /feed/latest`: Pure reverse-chronological comparison baseline.
  - `GET/POST/PATCH /users/me/market-profile`: Market profile onboarding and updates.
  - `GET/POST/DELETE /users/me/interests`: Followed topic interests management.
  - `GET/POST/DELETE /users/me/followed-entities`: Followed companies and brands management.
  - `GET/PATCH /users/me/feed-preferences`: User bias weights and privacy switches.
  - `POST /users/me/preferences/reset`: One-click reset of learned interaction preferences.
  - `POST /interactions`: User interaction logging and feedback loop dispatch.
- **Mobile Client Integration (React Native Expo)**:
  - Created `OnboardingModal.tsx`: Lightweight 4-step interactive onboarding flow (Business domain, subdomain, location, topics, followed entities).
  - Created `PersonalizationSettingsModal.tsx`: Profile inspection, topic/brand management, tuning sliders (freshness bias, trend bias, geographic bias), adaptive learning toggle, and one-click feedback reset.
  - Enhanced `ArticleCard.tsx`: Grounded explainability badges (`✨ Relevant to your Grocery business • Gurugram`), bookmarking, sharing, and "Not interested" feedback triggers.
  - Refactored `App.tsx`: 4-tab interface (`For You`, `Trends`, `Following`, `Latest`), top profile context bar, and Metro proxy routing.
  - Updated `metro.config.js`: Added reverse-proxy paths for `/users`, `/taxonomy`, `/entities`, and `/interactions`.
- **Quality Benchmarks & Evaluation Suite**:
  - `backend/tests/test_personalization.py`: 8 unit tests covering taxonomy, entities, scoring, freshness decay, diversity re-ranking, and feedback decay (100% pass).
  - `backend/tests/test_personalization_eval.py`: Quality benchmark evaluating 4 distinct personas (Grocery, Fashion, Electronics, Restaurant) proving 0% cross-persona Top-5 feed overlap on identical candidate databases (100% pass).
  - `backend/tests/test_personalization_api.py`: 6 integration tests verifying all FastAPI endpoints (100% pass).

## [0.3.0] - 2026-10-04
### Added
- **Phase 3 Trend Intelligence Engine**: Created dedicated `TrendEngine` pipeline following `ALGORITHMS DETECT → EVIDENCE VERIFIES → LLM EXPLAINS`.
- **Pluggable Vector Embeddings**: Created `BaseEmbeddingProvider` with `FastEmbedProvider` (local ONNX, 0-cost, 384 dimensions), `OpenAIEmbeddingProvider`, and `MockEmbeddingProvider`.
- **Relational & Vector Data Model**: Added `ArticleEmbedding`, `Trend`, `TrendArticle`, `TrendSnapshot`, and `TrendAnalysisRun` SQLAlchemy models with historical snapshot tracking.
- **Semantic Clustering & Noise Filter**: Built `ClusteringService` using Agglomerative Clustering with cosine distance, rejecting isolated stories and single-source noise.
- **Temporal Velocity & Burst Detection**: Built `TemporalAnalysisService` measuring recent 14-day velocity vs 45-day historical baseline, acceleration, and Poisson burst $Z$-score.
- **Deterministic Trend Scoring**: Built `TrendScoringService` computing Simpson's source diversity index, semantic coherence, momentum, normalized Strength (0-100), and Confidence.
- **Deterministic Lifecycle Engine**: Built `TrendLifecycleService` implementing rule-based state transitions (`emerging`, `growing`, `established`, `cooling`, `declining`, `inactive`).
- **Grounded LLM Trend Synthesis**: Built `TrendSynthesisService` with anti-hallucination guardrails and heuristic fallback for trend naming and key developments without business-specific advice.
- **Trend Persistence & Timeline Snapshots**: Built `TrendPersistenceService` with topic overlap matching across runs and snapshot history.
- **Trend REST APIs**: Created `GET /trends`, `GET /trends/emerging`, `GET /trends/growing`, `GET /trends/{id}`, `GET /trends/{id}/timeline`, and `POST /admin/trends/rebuild`.
- **Mobile Trends Feed UI**: Created React Native `TrendCard` and `TrendModal` components with tab switcher between `Latest News` and `Market Trends 🔥`.
- **Testing & Quality Benchmarks**: Added `backend/tests/test_trends.py` and `backend/tests/test_acceptance_phase3.py` (18/18 total test cases passing).

## [0.2.0] - 2026-10-04
### Added
- **AI Provider Abstraction Layer**: Built `BaseLLMProvider`, `GroqProvider` (using ultra-fast LPU inference), `OpenAIProvider`, and `MockLLMProvider` (`backend/app/services/ai/providers/`).
- **Prompt Isolation & Anti-Injection**: Versioned prompt template (`v1.0`) with structured JSON schema enforcement, retail/kirana relevance scoring (0.0-1.0), topic tags, entity types, and prompt injection defense.
- **Article Enrichment Database Schema**: Created `ArticleEnrichment` SQLAlchemy model in PostgreSQL (`article_enrichment` table) with indexing on status, relevance score, domain, and foreign key link to `articles`.
- **Enrichment Orchestration Service**: Built `EnrichmentService` (`backend/app/services/ai/enrichment_service.py`) with automatic retry bounds, token and latency metrics tracking, and error isolation.
- **Asynchronous Enrichment Worker**: Integrated background batch worker into APScheduler (`backend/app/scheduler/manager.py`) running every 30s to process pending articles without blocking feed queries.
- **Admin Reprocessing & Observability APIs**: Created `/admin/ai/reprocess/{id}`, `/admin/ai/reprocess-batch`, and `/admin/ai/status` endpoints.
- **Feed & Article AI Serialization**: Eagerly loaded `ArticleEnrichment` in `GET /feed` and `GET /articles` endpoints.
- **Mobile AI UI Components**: Enhanced `ArticleCard` and `ArticleModal` in React Native to render AI summaries, Kirana Match % meters, topic pills, and named entity badges.
- **Phase 2 Acceptance Tests**: 11/11 tests passing with live Groq inference and mock regression testing.

## [0.1.0] - 2026-09-28
### Added
- Phase 1 system specifications (`PHASE_1_SPEC.md`).
- System architecture & adapter contracts (`ARCHITECTURE.md`).
- Technology stack lock (`TECH_STACK.md`).
- Relational schema and canonical article model specification (`DATA_MODEL.md`).
- Source registry specification and seed list (`SOURCE_REGISTRY.md`).
- Active project tracker (`PROJECT_TRACKER.md`).
- Docker Compose configuration for PostgreSQL 16 Alpine (`docker-compose.yml`).
- Async SQLAlchemy ORM models (`Source`, `Article`, `IngestionRun`) and Alembic migration environment.
- Canonical article Pydantic schema and validation.
- Normalization utilities (URL tracking parameter cleaner, UTC datetime normalizer, title hasher, SimHash fingerprint).
- RSS, JSON REST API, and HTML scraping adapters (`backend/app/adapters/`).
- Multi-source ingestion pipeline executed across 6 seed sources in one cycle.
- Background asynchronous polling scheduler with APScheduler (`backend/app/scheduler/manager.py`).
- Non-blocking manual force-refresh endpoint `POST /ingestion/refresh`.
- High-performance `/feed` and `/articles` REST API endpoints with domain filters, cursor pagination, and search.
- Mobile client built with React Native, Expo, and TypeScript (`mobile/App.tsx`).
- Unit and acceptance test suite with pytest passing 100% (`backend/tests/test_acceptance_phase1.py`).
