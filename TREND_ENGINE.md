# Trend Engine Architecture, Mathematics & Taxonomy

This document is the comprehensive reference for the Vyapar Phase 3 Market-Level Intelligence & Emerging Trend Engine. It details system components, statistical clustering, deterministic scoring formulas, trend taxonomy, and lifecycle state management.

---

## 1. Overview & Operating Principle

The `TrendEngine` transforms individually enriched Phase 2 articles into structured, verified, and continuously tracked **Market Trends**.

**Core Operating Principle**:
> **`ALGORITHMS DETECT → EVIDENCE VERIFIES → LLM EXPLAINS`**

1. **Algorithms Detect**: Vector embeddings, Agglomerative clustering, and temporal velocity metrics detect story clusters without LLM involvement.
2. **Evidence Verifies**: Multi-source diversity, minimum volume, and semantic coherence thresholds eliminate PR noise and unverified rumors.
3. **LLM Explains**: A grounded, zero-hallucination prompt synthesizes a concise title, narrative summary, and key developments strictly from cluster evidence.

---

## 2. Component Hierarchy & Module Map

```text
backend/app/services/trends/
├── __init__.py
├── engine.py                  # Main TrendEngine coordinator
├── candidates.py              # CandidateGenerator (sliding window + topic/entity overlap)
├── embeddings/
│   ├── base.py               # BaseEmbeddingProvider interface
│   ├── fastembed_provider.py # FastEmbed / MiniLM provider (100% local ONNX, 0-cost, 384-dim)
│   ├── openai_provider.py    # OpenAI embedding provider fallback
│   ├── mock_provider.py      # Deterministic token-dense test provider
│   └── service.py            # Article embedding lifecycle & DB persistence
├── similarity.py              # Cosine similarity & vector distance service
├── clustering.py              # Agglomerative clustering & noise rejection
├── temporal.py                # Velocity, acceleration, baseline delta & burst detection
├── scoring.py                 # Deterministic TrendScoringService (Strength, Momentum, Diversity)
├── lifecycle.py               # Deterministic Lifecycle State Machine
├── synthesis.py               # Grounded LLM synthesis (Naming, Narrative, Key Developments)
└── persistence.py             # Trend matching, versioning, snapshots & DB sync
```

---

## 3. End-to-End Processing Pipeline

```text
Phase 2 Enriched Articles
         ↓
1. Canonical Semantic Representation & Vector Embedding (FastEmbed / MiniLM 384-d)
         ↓
2. Candidate Grouping (Time window: 14-day recent vs 45-day baseline, domain & region filter)
         ↓
3. Pairwise Cosine Distance & Agglomerative Clustering (Threshold: 0.38 / Similarity ≥ 0.62)
         ↓
4. Noise & Evidence Rejection (Articles ≥ 3, Sources ≥ 2, Coherence check)
         ↓
5. Temporal Velocity, Acceleration & Growth Rate Calculation
         ↓
6. Deterministic Metric Scoring (Coherence, Simpson's Diversity, Momentum, Strength, Confidence)
         ↓
7. Lifecycle State Assignment (Emerging, Growing, Established, Cooling, Declining, Inactive)
         ↓
8. Grounded LLM Synthesis (Structured JSON title, explanation & key developments)
         ↓
9. Persistence & Incremental Snapshotting (Trends, TrendArticles, TrendSnapshots)
```

---

## 4. Deterministic Scoring & Mathematical Formulas

All trend scores are calculated deterministically using transparent algorithms and normalized to **`0.0 – 1.0`** (or **`0 – 100`** in the UI).

### 4.1 Semantic Coherence ($S_{\text{coherence}}$)
Measures the mean pairwise cosine similarity among all articles in a cluster:
$$S_{\text{coherence}} = \frac{2}{N(N-1)} \sum_{i < j} \cos(\vec{e}_i, \vec{e}_j)$$
*Where $\vec{e}_i$ is the unit-normalized embedding of article $i$, and $N$ is total articles in the cluster.*

### 4.2 Source Diversity ($S_{\text{diversity}}$)
Penalizes clusters dominated by a single publisher and rewards cross-source validation using Simpson's Diversity Index:
$$S_{\text{diversity}} = 1 - \sum_{s \in \text{Sources}} \left( \frac{\text{count}(s)}{N} \right)^2$$
Normalized with a unique-source scale factor $K_{\text{sources}}$:
$$\hat{S}_{\text{diversity}} = \min\left(1.0, \, S_{\text{diversity}} \times \frac{1 + \min(1.0, K_{\text{sources}} / 4.0)}{1.5}\right)$$

### 4.3 Temporal Velocity, Growth & Momentum ($S_{\text{momentum}}$)
Measures the coverage growth rate in the active window ($W_{\text{recent}}$, e.g. 14 days) relative to the baseline historical window ($W_{\text{baseline}}$, e.g. previous 45 days):

$$\text{Velocity}_{\text{recent}} = \frac{N_{\text{recent}}}{\text{Days}(W_{\text{recent}})}$$
$$\text{Velocity}_{\text{baseline}} = \frac{N_{\text{baseline}}}{\text{Days}(W_{\text{baseline}})}$$
$$\text{Growth Rate } (G) = \frac{\text{Velocity}_{\text{recent}} - \text{Velocity}_{\text{baseline}}}{\text{Velocity}_{\text{baseline}} + 0.1}$$
$$\text{Burst Score } (Z) = \frac{\text{Velocity}_{\text{recent}} - \text{Velocity}_{\text{baseline}}}{\sqrt{\text{Velocity}_{\text{baseline}} + 0.5}}$$

Normalized Momentum (bounded between $-1.0$ and $+1.0$ via $\tanh$):
$$S_{\text{momentum}} = \tanh(0.5 \cdot G + 0.3 \cdot Z)$$

### 4.4 Trend Strength Score ($S_{\text{strength}}$)
Represents overall market weight, calculated as a weighted composite:
$$S_{\text{strength}} = 0.30 \cdot S_{\text{coherence}} + 0.30 \cdot \left(\frac{S_{\text{momentum}} + 1}{2}\right) + 0.25 \cdot \hat{S}_{\text{diversity}} + 0.15 \cdot S_{\text{volume}}$$
*Where $S_{\text{volume}} = \min\left(1.0, \, \frac{\ln(1 + N)}{\ln(21)}\right)$.*

### 4.5 Trend Confidence Score ($S_{\text{confidence}}$)
Reflects certainty that the cluster represents a genuine recurring market pattern:
$$S_{\text{confidence}} = 0.40 \cdot S_{\text{coherence}} + 0.35 \cdot \hat{S}_{\text{diversity}} + 0.25 \cdot \min\left(1.0, \, \frac{N}{8}\right)$$

---

## 5. Trend Taxonomy & Canonical Categories

Every detected trend is assigned a canonical category grounded in retail and consumer commerce:

| Category | Description & Scope |
|---|---|
| **`Consumer Trend`** | Shifts in consumer buying habits, dietary preferences, health focus, brand loyalty, or spending patterns. |
| **`Product Trend`** | Category innovation, new SKU launches, packaging changes, ingredient reformulations. |
| **`Technology & Quick Commerce`** | 10-minute delivery, dark stores, retail tech, POS systems, AI in supply chain. |
| **`Pricing & Inflation`** | Commodity price changes, wholesale price hikes, discount wars, margin pressures. |
| **`Regulation & Policy`** | GST updates, local trade policies, import/export duties, food safety (FSSAI) norms. |
| **`Retail & Distribution`** | General trade, modern trade, kirana digitization, distributor margins. |
| **`Supply Chain & Logistics`** | Cold storage, warehousing, transport rates, agricultural yields. |
| **`Expansion & Investment`** | Store network rollout, funding rounds, acquisitions, factory capacity additions. |
| **`Competition & Market Share`** | Rivalry between major FMCG brands, local vs national players. |

---

## 6. Lifecycle State Machine & Evidence Grades

### 6.1 Lifecycle States
A trend transitions deterministically based on temporal volume, growth rate, and persistence:

| Lifecycle State | Deterministic Transition Rules |
|---|---|
| **`emerging`** | Low baseline ($N_{\text{baseline}} \le 1$), positive acceleration ($G \ge 0.40$ or $Z \ge 1.0$), newly detected. |
| **`growing`** | Strong sustained momentum ($S_{\text{momentum}} \ge 0.20$), positive growth ($G \ge 0.15$). |
| **`established`** | Persistent presence across history ($N_{\text{baseline}} \ge 3$), stable velocity ($|G| < 0.25$), persistence $\ge 7$ days. |
| **`cooling`** | Slowing growth rate ($-0.45 \le G < -0.15$) but still retains active articles. |
| **`declining`** | Sharp sustained drop in coverage ($G < -0.45$). |
| **`inactive`** | Dropped below viable activity ($N < 2$). |

### 6.2 Evidence Quality Grades
Displayed to users to convey evidence strength:
- **`HIGH`**: Strength $\ge 70/100$, Confidence $\ge 65/100$, and $\ge 3$ independent publishers.
- **`MEDIUM`**: Strength $\ge 40/100$ and $\ge 2$ independent publishers.
- **`LOW`**: Minimum clustering threshold met ($3$ articles, $2$ sources), early signal.

---

## 7. Grounded LLM Synthesis & Persistence Strategy

### 7.1 Strict Anti-Hallucination Guardrails
The synthesis prompt strictly prohibits hallucination and prescriptive advice:
1. **Evidence-Grounded**: Uses only factual entities, quotes, numbers, and dates present in the clustered articles.
2. **No Business Recommendations**: Adheres strictly to describing macro market developments (no inventory/pricing advice).
3. **Structured Output**: Generates valid JSON with `trend_name`, `trend_description`, `why_emerging`, `key_developments`, and `category`.
4. **Heuristic Fallback**: If the LLM provider fails or hits rate limits, an algorithmic fallback synthesizes trend titles from top topics and entities without crashing.

### 7.2 Persistence, Matching & Snapshots
- **Centroid & Topic Matching**: Clusters from subsequent runs are compared against active trends using Jaccard topic similarity and vector cosine distance. If match score $\ge 0.55$, the existing trend is updated; otherwise, a new trend is created.
- **Timeline Snapshots**: Every run appends a record to `trend_snapshots` (`timestamp`, `article_count`, `source_count`, `strength_score`, `momentum_score`, `status`), enabling trend trajectory visualization in the mobile app.
