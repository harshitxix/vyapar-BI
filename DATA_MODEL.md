# Data Model, Database Schema & Source Registry

This document defines the complete PostgreSQL relational schema, vector tables, constraints, relationships, and seed source registry across all phases of the Vyapar Market Intelligence platform.

---

## 1. Core Ingestion Entities (Phase 1)

### 1.1 `sources` Table
Configures active media outlets, trade publications, and API feeds.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | Unique slug/ID (e.g. `et-retail-rss`) |
| `name` | VARCHAR(255) | NOT NULL | Human-readable source name |
| `domain` | VARCHAR(255) | NOT NULL | Base domain (e.g. `economictimes.indiatimes.com`) |
| `source_type` | VARCHAR(32) | NOT NULL | `rss`, `api`, `html`, `playwright` |
| `feed_url` | TEXT | NULLABLE | RSS/Atom feed URL |
| `api_endpoint` | TEXT | NULLABLE | JSON REST API URL |
| `base_url` | TEXT | NOT NULL | Homepage / base web address |
| `business_domains` | JSONB | NOT NULL | List of target domains (`grocery`, `retail`, `fmcg`) |
| `regions` | JSONB | NOT NULL | Target regions (`india`, `global`) |
| `language` | VARCHAR(10) | DEFAULT 'en' | ISO language code |
| `refresh_interval` | INTEGER | DEFAULT 900 | Polling interval in seconds |
| `priority` | INTEGER | DEFAULT 1 | Priority ranking (1 = high) |
| `active` | BOOLEAN | DEFAULT TRUE | Active polling toggle |
| `status` | VARCHAR(32) | DEFAULT 'healthy' | `healthy`, `degraded`, `failed`, `inactive` |
| `last_checked` | TIMESTAMPTZ | NULLABLE | Last poll execution time |
| `last_success` | TIMESTAMPTZ | NULLABLE | Last successful ingestion time |
| `last_failure` | TIMESTAMPTZ | NULLABLE | Last error timestamp |
| `failure_count` | INTEGER | DEFAULT 0 | Consecutive failure count |
| `last_response_time_ms`| INTEGER | DEFAULT 0 | Network latency for health monitoring |
| `last_article_count` | INTEGER | DEFAULT 0 | Articles fetched in last run |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Record update |

---

### 1.2 `articles` Table
Stores raw canonical news stories normalized from all sources.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID or deterministic hash ID |
| `source_id` | VARCHAR(64) | REFERENCES sources(id) ON DELETE CASCADE | Source identifier |
| `source_name` | VARCHAR(255) | NOT NULL | Source name snapshot |
| `source_domain` | VARCHAR(255) | NOT NULL | Source domain snapshot |
| `title` | TEXT | NOT NULL | Clean article title |
| `description` | TEXT | NULLABLE | Clean excerpt / summary description |
| `author` | VARCHAR(255) | NULLABLE | Extracted author name |
| `original_url` | TEXT | NOT NULL | Raw source URL |
| `canonical_url` | TEXT | NOT NULL | Cleaned/normalized URL without tracking tags |
| `canonical_url_hash` | VARCHAR(64) | UNIQUE, NOT NULL, INDEX | SHA256 of canonical URL |
| `normalized_title_hash`| VARCHAR(64) | INDEX | SHA256 of lowercase punctuation-stripped title |
| `fingerprint` | VARCHAR(64) | INDEX | Near-duplicate SimHash token fingerprint |
| `image_url` | TEXT | NULLABLE | Thumbnail / lead image URL |
| `published_at` | TIMESTAMPTZ | NOT NULL, INDEX | UTC published timestamp |
| `fetched_at` | TIMESTAMPTZ | NOT NULL | UTC fetched timestamp |
| `language` | VARCHAR(10) | DEFAULT 'en' | ISO language code |
| `region` | VARCHAR(64) | NOT NULL, INDEX | Primary geographical region |
| `business_domain` | VARCHAR(64) | NOT NULL, INDEX | Primary domain (`grocery`, `retail`, etc.) |
| `category` | VARCHAR(64) | NULLABLE, INDEX | Category/topic |
| `subcategory` | VARCHAR(64) | NULLABLE | Subcategory |
| `content_type` | VARCHAR(32) | DEFAULT 'news' | `news`, `report`, `announcement` |
| `extraction_method` | VARCHAR(32) | NOT NULL | `rss`, `api`, `html`, `playwright` |
| `status` | VARCHAR(32) | DEFAULT 'published', INDEX | `published`, `archived`, `rejected` |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | DB insert timestamp |

---

### 1.3 `ingestion_runs` Table
Audit logs for periodic ingestion batches.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the run |
| `trigger_type` | VARCHAR(32) | NOT NULL | `scheduled`, `manual` |
| `started_at` | TIMESTAMPTZ | NOT NULL | Run start UTC |
| `finished_at` | TIMESTAMPTZ | NULLABLE | Run finish UTC |
| `status` | VARCHAR(32) | NOT NULL | `running`, `completed`, `failed` |
| `sources_attempted` | INTEGER | DEFAULT 0 | Count of sources polled |
| `sources_succeeded` | INTEGER | DEFAULT 0 | Count of sources succeeded |
| `sources_failed` | INTEGER | DEFAULT 0 | Count of sources failed |
| `articles_discovered` | INTEGER | DEFAULT 0 | Total raw articles parsed |
| `articles_inserted` | INTEGER | DEFAULT 0 | New canonical articles stored |
| `articles_duplicate` | INTEGER | DEFAULT 0 | Duplicate articles rejected |
| `articles_rejected` | INTEGER | DEFAULT 0 | Invalid / irrelevant articles rejected |
| `error_details` | JSONB | NULLABLE | Structured error log summary |

---

## 2. AI Enrichment Entities (Phase 2)

### 2.1 `article_enrichment` Table
Stores LLM-extracted metadata, topic tags, typed entities, and business events.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the enrichment record |
| `article_id` | VARCHAR(64) | REFERENCES articles(id) ON DELETE CASCADE, UNIQUE, NOT NULL | One-to-one link to Article |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'pending', INDEX | `pending`, `processing`, `completed`, `failed`, `skipped` |
| `summary` | TEXT | NULLABLE | Factual 2-4 sentence AI summary |
| `primary_domain` | VARCHAR(64) | NULLABLE, INDEX | Primary business domain classification |
| `secondary_domains`| JSONB | NULLABLE | Secondary domains list |
| `category` | VARCHAR(64) | NULLABLE, INDEX | Main business category |
| `subcategory` | VARCHAR(64) | NULLABLE | Specific subcategory |
| `article_type` | VARCHAR(32) | NULLABLE | `news`, `analysis`, `earnings`, `policy`, `interview` |
| `topics` | JSONB | NULLABLE | Normalized list of topic strings (3-8 topics) |
| `keywords` | JSONB | NULLABLE | Search keywords list |
| `entities` | JSONB | NULLABLE | Typed named entities (`[{"name": "...", "type": "COMPANY"}]`) |
| `events` | JSONB | NULLABLE | Structured events (`[{"type": "...", "description": "..."}]`) |
| `relevance_score` | FLOAT | NULLABLE, INDEX | 0.0 – 1.0 relevance to retail/kirana owners |
| `confidence` | FLOAT | NULLABLE | 0.0 – 1.0 AI classification confidence |
| `model` | VARCHAR(64) | NOT NULL | LLM model used (e.g. `openai/gpt-oss-20b`) |
| `prompt_version` | VARCHAR(32) | NOT NULL | Prompt template version (e.g. `v1.0`) |
| `input_tokens` | INTEGER | DEFAULT 0 | Prompt token count |
| `output_tokens` | INTEGER | DEFAULT 0 | Completion token count |
| `estimated_cost` | FLOAT | DEFAULT 0.0 | Estimated USD cost |
| `latency_ms` | INTEGER | DEFAULT 0 | AI inference latency in milliseconds |
| `attempt_count` | INTEGER | DEFAULT 0 | Number of processing attempts |
| `last_attempt_at` | TIMESTAMPTZ | NULLABLE | Timestamp of last attempt |
| `last_error` | TEXT | NULLABLE | Error message if processing failed |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation UTC |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Record update UTC |

---

## 3. Trend Intelligence & Vector Entities (Phase 3)

### 3.1 `article_embeddings` Table
Stores dense vector representations of articles for semantic clustering.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the embedding |
| `article_id` | VARCHAR(64) | REFERENCES articles(id) ON DELETE CASCADE, UNIQUE, NOT NULL, INDEX | Foreign key to Article |
| `model` | VARCHAR(128) | NOT NULL | Embedding model (e.g. `BAAI/bge-small-en-v1.5`) |
| `version` | VARCHAR(32) | NOT NULL, DEFAULT 'v1' | Embedding pipeline version |
| `dimension` | INTEGER | NOT NULL, DEFAULT 384 | Embedding dimensionality (e.g. 384) |
| `embedding` | JSONB / Vector | NULLABLE | 384-dimensional dense float vector |
| `embedding_text` | TEXT | NULLABLE | Pre-processed semantic text fed to embedding model |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Update timestamp |

---

### 3.2 `trends` Table
Canonical market trends synthesized from verified article clusters.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the trend |
| `name` | VARCHAR(255) | NOT NULL, INDEX | Concise trend headline (e.g. *Rapid Expansion of Quick Commerce Retail*) |
| `description` | TEXT | NOT NULL | Factual 2-3 sentence trend narrative |
| `why_emerging` | TEXT | NULLABLE | Algorithmic detection explanation & momentum rationale |
| `key_developments`| JSONB | NULLABLE | 2-4 factual milestone developments |
| `domain` | VARCHAR(64) | NOT NULL, INDEX | Target sector (`grocery`, `retail`, `tech`, `all`) |
| `region` | VARCHAR(64) | NOT NULL, INDEX | Geographic focus (`india`, `all`) |
| `category` | VARCHAR(64) | NOT NULL, INDEX | Canonical category (`Consumer Trend`, `Retail`, etc.) |
| `status` | VARCHAR(32) | NOT NULL, INDEX | `emerging`, `growing`, `established`, `cooling`, `declining`, `inactive` |
| `evidence_grade` | VARCHAR(16) | NOT NULL, INDEX | `high`, `medium`, `low` |
| `strength_score` | FLOAT | NOT NULL, DEFAULT 0.0, INDEX | Overall weight (0.0 – 1.0) |
| `confidence_score`| FLOAT | NOT NULL, DEFAULT 0.0 | Statistical certainty (0.0 – 1.0) |
| `momentum_score` | FLOAT | NOT NULL, DEFAULT 0.0 | Velocity acceleration (-1.0 to +1.0) |
| `coherence_score`| FLOAT | NOT NULL, DEFAULT 0.0 | Semantic cluster density (0.0 – 1.0) |
| `diversity_score`| FLOAT | NOT NULL, DEFAULT 0.0 | Simpson publisher diversity (0.0 – 1.0) |
| `article_count` | INTEGER | NOT NULL, DEFAULT 0, INDEX | Total supporting articles |
| `source_count` | INTEGER | NOT NULL, DEFAULT 0, INDEX | Independent publishers |
| `representative_topics` | JSONB | NULLABLE | Top cluster topics |
| `representative_entities`| JSONB | NULLABLE | Top named entities |
| `first_detected_at` | TIMESTAMPTZ | NOT NULL, INDEX | Initial discovery timestamp |
| `last_updated_at` | TIMESTAMPTZ | NOT NULL, INDEX | Most recent evidence update |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Update timestamp |

---

### 3.3 `trend_articles` Table
Many-to-many junction linking trends to their supporting article evidence.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the junction record |
| `trend_id` | VARCHAR(64) | REFERENCES trends(id) ON DELETE CASCADE, INDEX | Foreign key to Trend |
| `article_id` | VARCHAR(64) | REFERENCES articles(id) ON DELETE CASCADE, INDEX | Foreign key to Article |
| `similarity_score`| FLOAT | DEFAULT 1.0 | Cosine similarity to cluster centroid |
| `added_at` | TIMESTAMPTZ | DEFAULT NOW() | Association timestamp |

*Unique constraint: `(trend_id, article_id)`.*

---

### 3.4 `trend_snapshots` Table
Time-series snapshots recording trend strength and momentum over time for UI chart visualization.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the snapshot |
| `trend_id` | VARCHAR(64) | REFERENCES trends(id) ON DELETE CASCADE, INDEX | Foreign key to Trend |
| `timestamp` | TIMESTAMPTZ | NOT NULL, INDEX | Snapshot capture time |
| `article_count` | INTEGER | DEFAULT 0 | Article volume at snapshot |
| `source_count` | INTEGER | DEFAULT 0 | Independent publishers at snapshot |
| `strength_score` | FLOAT | DEFAULT 0.0 | Strength score at snapshot |
| `momentum_score` | FLOAT | DEFAULT 0.0 | Momentum score at snapshot |
| `status` | VARCHAR(32) | NOT NULL | Lifecycle state at snapshot |

---

### 3.5 `trend_analysis_runs` Table
Audit trail of batch trend detection runs.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `run_id` | VARCHAR(64) | PRIMARY KEY | Unique run identifier |
| `started_at` | TIMESTAMPTZ | NOT NULL | Batch start timestamp |
| `finished_at` | TIMESTAMPTZ | NULLABLE | Batch completion timestamp |
| `domain` | VARCHAR(64) | NULLABLE | Filtered domain (or null for all) |
| `region` | VARCHAR(64) | NULLABLE | Filtered region |
| `window_days` | INTEGER | DEFAULT 14 | Recent analysis window |
| `articles_considered` | INTEGER | DEFAULT 0 | Eligible articles analyzed |
| `candidate_clusters` | INTEGER | DEFAULT 0 | Clusters discovered |
| `valid_trends` | INTEGER | DEFAULT 0 | Clusters passing evidence filters |
| `new_trends` | INTEGER | DEFAULT 0 | New trends created |
| `updated_trends` | INTEGER | DEFAULT 0 | Existing trends updated |
| `discarded_clusters` | INTEGER | DEFAULT 0 | Clusters rejected due to noise thresholds |
| `duration_ms` | INTEGER | DEFAULT 0 | Execution time in milliseconds |
| `status` | VARCHAR(32) | NOT NULL | `running`, `completed`, `failed` |
| `error_message` | TEXT | NULLABLE | Error details if failed |

---

## 4. Source Registry & Seed Configurations

### 4.1 Initial Seed Sources

| Source ID | Name | Domain | Type | Target Domains | Region | Refresh (s) | Priority |
|---|---|---|---|---|---|---|---|
| `et-retail-rss` | Economic Times Retail | `retail.economictimes.indiatimes.com` | `rss` | `retail`, `grocery`, `fmcg` | `india` | 600 (10m) | 1 |
| `mint-companies-rss` | Livemint Retail / Industry | `livemint.com` | `rss` | `retail`, `manufacturing`, `business` | `india` | 900 (15m) | 1 |
| `inc42-commerce-rss` | Inc42 Quick Commerce & Retail | `inc42.com` | `rss` | `grocery`, `retail`, `tech` | `india` | 1200 (20m) | 2 |
| `financial-express-retail` | Financial Express Industry | `financialexpress.com` | `rss` | `retail`, `grocery`, `fmcg` | `india` | 900 (15m) | 2 |
| `business-standard-companies` | Business Standard Companies | `business-standard.com` | `rss` | `retail`, `manufacturing`, `business` | `india` | 900 (15m) | 2 |

---

## 5. Personalization & User Context Entities (Phase 4)

### 5.1 `users` Table
Stores registered and anonymous/guest user accounts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of the user |
| `email` | VARCHAR(255) | UNIQUE, NULLABLE | Optional user email |
| `username` | VARCHAR(64) | UNIQUE, NULLABLE | Optional unique username |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active account toggle |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Account update timestamp |

---

### 5.2 `user_market_profiles` Table
Stores the user's business market context and geographical preferences.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of profile |
| `user_id` | VARCHAR(64) | REFERENCES users(id) ON DELETE CASCADE, UNIQUE, NOT NULL, INDEX | One-to-one user reference |
| `business_name` | VARCHAR(255) | NULLABLE | Business or store name |
| `business_domain` | VARCHAR(64) | NOT NULL, INDEX | Primary sector (`grocery`, `fashion`, `retail`, etc.) |
| `business_subdomain`| VARCHAR(64) | NULLABLE | Subdomain (`neighborhood_grocery`, `supermarket`) |
| `business_description`| TEXT | NULLABLE | Brief business summary |
| `country` | VARCHAR(64) | NOT NULL, DEFAULT 'India' | Geographical country market |
| `state` | VARCHAR(64) | NULLABLE | State / province |
| `city` | VARCHAR(64) | NULLABLE, INDEX | City / municipality |
| `preferred_language`| VARCHAR(10) | NOT NULL, DEFAULT 'en' | Content language preference |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Profile creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Profile update timestamp |

---

### 5.3 `canonical_entities` Table
Stores deduplicated canonical brands, companies, and organizations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | Slug / UUID (e.g. `ent_reliance_retail`) |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE, INDEX | Canonical name (e.g. `Reliance Retail`) |
| `entity_type` | VARCHAR(32) | NOT NULL | `COMPANY`, `BRAND`, `ORGANIZATION` |
| `aliases` | JSONB | NULLABLE | Alternate spellings / tickers (e.g. `["D-Mart", "Avenue Supermarts"]`) |
| `domain` | VARCHAR(64) | NULLABLE | Primary industry sector |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

---

### 5.4 `user_entity_follows` Table
Junction linking users to followed canonical entities.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of follow record |
| `user_id` | VARCHAR(64) | REFERENCES users(id) ON DELETE CASCADE, INDEX | User reference |
| `entity_id` | VARCHAR(64) | REFERENCES canonical_entities(id) ON DELETE CASCADE, INDEX | Entity reference |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Follow timestamp |

*Unique constraint: `(user_id, entity_id)`.*

---

### 5.5 `user_topic_preferences` Table
Tracks user interests across extracted topics.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of preference |
| `user_id` | VARCHAR(64) | REFERENCES users(id) ON DELETE CASCADE, INDEX | User reference |
| `topic_id` | VARCHAR(128) | NOT NULL, INDEX | Normalized topic slug (e.g. `fmcg`, `quick commerce`) |
| `preference_source` | VARCHAR(32) | NOT NULL, DEFAULT 'manual' | `onboarding`, `manual`, `inferred` |
| `preference_score` | FLOAT | NOT NULL, DEFAULT 1.0 | Weight in $[0.0, 1.0]$ |
| `is_explicit` | BOOLEAN | NOT NULL, DEFAULT TRUE | True if selected by user directly |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Update timestamp |

*Unique constraint: `(user_id, topic_id)`.*

---

### 5.6 `user_feed_preferences` Table
User-configurable ranking weights and personalization knobs.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of settings record |
| `user_id` | VARCHAR(64) | REFERENCES users(id) ON DELETE CASCADE, UNIQUE, NOT NULL | User reference |
| `settings` | JSONB | NOT NULL | Config knobs (`freshness_bias`, `trend_bias`, `local_bias`, `enabled`) |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

---

### 5.7 `user_interaction_events` Table
Audit stream of user interactions for implicit feedback calculation.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of event |
| `user_id` | VARCHAR(64) | REFERENCES users(id) ON DELETE CASCADE, INDEX | User reference |
| `event_type` | VARCHAR(32) | NOT NULL, INDEX | `article_open`, `article_save`, `article_dismiss`, `not_interested`, etc. |
| `article_id` | VARCHAR(64) | REFERENCES articles(id) ON DELETE SET NULL, NULLABLE, INDEX | Referenced article |
| `trend_id` | VARCHAR(64) | REFERENCES trends(id) ON DELETE SET NULL, NULLABLE | Referenced trend |
| `topic_id` | VARCHAR(128) | NULLABLE | Associated topic |
| `entity_id` | VARCHAR(64) | REFERENCES canonical_entities(id) ON DELETE SET NULL, NULLABLE | Associated entity |
| `session_id` | VARCHAR(64) | NULLABLE | Client session identifier |
| `source_screen` | VARCHAR(64) | NOT NULL, DEFAULT 'for_you' | Screen where event originated |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW(), INDEX | Event timestamp |

---

### 5.8 `user_learned_preferences` Table
Aggregated, bounded preference weights calculated from user interactions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(64) | PRIMARY KEY | UUID of learned preference |
| `user_id` | VARCHAR(64) | REFERENCES users(id) ON DELETE CASCADE, INDEX | User reference |
| `preference_type` | VARCHAR(32) | NOT NULL | `topic`, `entity`, `domain`, `category` |
| `target_id` | VARCHAR(128) | NOT NULL, INDEX | Topic slug or Entity ID |
| `preference_score` | FLOAT | NOT NULL, DEFAULT 0.5 | Bounded learned weight in $[0.0, 1.0]$ |
| `evidence_count` | INTEGER | NOT NULL, DEFAULT 1 | Count of supporting interactions |
| `last_interaction_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Timestamp of most recent interaction |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Update timestamp |

*Unique constraint: `(user_id, preference_type, target_id)`.*

### 4.2 Seed Source Configuration JSON
```json
[
  {
    "id": "et-retail-rss",
    "name": "ET Retail News",
    "domain": "retail.economictimes.indiatimes.com",
    "base_url": "https://retail.economictimes.indiatimes.com",
    "source_type": "rss",
    "feed_url": "https://retail.economictimes.indiatimes.com/rss/topstories",
    "api_endpoint": null,
    "business_domains": ["retail", "grocery", "fmcg"],
    "regions": ["india"],
    "language": "en",
    "refresh_interval": 600,
    "priority": 1,
    "active": true
  }
]
```
