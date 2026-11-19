# Feed Ranking & Relevance Scoring Specification (Phase 4)

This document specifies the mathematical formulas, scoring components, decay functions, and diversity re-ranking algorithms powering the Phase 4 Personalized Market Feed Engine.

---

## 1. Article Relevance Scoring Formula

Every candidate article retrieved for a user is scored using a deterministic linear combination of 8 signals:

$$\text{Personalized Score} = \sum_{i=1}^{8} W_i \cdot S_i$$

Normalized strictly to the range $[0.0, 1.0]$.

### Configurable Weights & Signals

| Index | Component ($S_i$) | Default Weight ($W_i$) | Description & Formula |
|---|---|---|---|
| **$S_1$** | **Domain Relevance** | **0.20** | Exact match with user's primary domain = 1.0; secondary domain = 0.6; related domain = 0.3; unrelated = 0.0. |
| **$S_2$** | **Topic Match** | **0.20** | Jaccard overlap between user's followed topics and article's enriched topics: $\frac{\|T_{user} \cap T_{article}\|}{\|T_{user} \cup T_{article}\|}$, boosted by explicit topic scores. |
| **$S_3$** | **Entity Match** | **0.15** | Proportion of user-followed canonical entities mentioned in the article enrichment: $\min\left(1.0, \sum_{e \in E_{user} \cap E_{article}} 0.5\right)$. |
| **$S_4$** | **Geographic Relevance** | **0.10** | City match = 1.0; State match = 0.8; Country match = 0.5; Global relevant = 0.4; Unspecified = 0.2. |
| **$S_5$** | **Intrinsic Quality** | **0.10** | Phase 2 article relevance score ($0.0 - 1.0$) reflecting factual depth and business relevance. |
| **$S_6$** | **Trend Association** | **0.10** | If article is linked to an active Phase 3 trend: $\max_{\text{trend}} (\text{trend.strength\_score} \cdot \text{trend.user\_relevance})$. Unlinked = 0.0. |
| **$S_7$** | **Freshness Score** | **0.10** | Exponential decay based on article publication timestamp (not fetch time): $\exp(-\Delta t / \tau)$. |
| **$S_8$** | **User Preference Signal**| **0.05** | Learned implicit interaction adjustment score from user interaction history ($0.0 - 1.0$, default 0.5 neutral). |

$$\sum_{i=1}^{8} W_i = 0.20 + 0.20 + 0.15 + 0.10 + 0.10 + 0.10 + 0.10 + 0.05 = 1.00$$

---

## 2. Freshness Decay Function

Freshness prioritizes timely intelligence without prematurely suppressing active multi-day developments:

$$\text{Freshness}(\Delta t) = \exp\left(-\frac{\Delta t}{\tau}\right)$$

Where:
- $\Delta t$: Age of article in hours, calculated as $(\text{now}_{\text{UTC}} - \text{published\_at}_{\text{UTC}})$.
- $\tau$: Configurable half-life decay constant (Default: $\tau = 48\text{ hours}$).

### Expected Decay Schedule
- $0\text{ hours (breaking)}$: $1.00$
- $12\text{ hours}$: $\exp(-12/48) = 0.78$
- $24\text{ hours (1 day)}$: $\exp(-24/48) = 0.61$
- $48\text{ hours (2 days)}$: $\exp(-48/48) = 0.37$
- $72\text{ hours (3 days)}$: $\exp(-72/48) = 0.22$
- $7\text{ days (168 hours)}$: $\exp(-168/48) = 0.03$

Articles associated with an ongoing, active Phase 3 trend retain relevance via the **Trend Association ($S_6$)** component even as freshness decays.

---

## 3. Trend Relevance Scoring (Strict Separation from Trend Strength)

> **CRITICAL ARCHITECTURAL BOUNDARY**:
> - **Phase 3 Trend Strength** ($S_{market} \in [0.0, 1.0]$): Global statistical metric based on volume, acceleration, and Simpson publisher diversity.
> - **Phase 4 Trend Relevance** ($R_{user} \in [0.0, 1.0]$): How pertinent that trend is to this specific user's domain, location, followed topics, and entities.

A trend can be globally strong (e.g. *Semiconductor Fab Policies*) but completely irrelevant to a Kirana owner. Conversely, a local trend (e.g. *Regional Wheat Price Spike*) may have moderate global strength but maximum user relevance.

### Trend User Relevance Formula:
$$R_{user} = 0.40 \cdot \text{DomainMatch} + 0.30 \cdot \text{TopicMatch} + 0.20 \cdot \text{EntityMatch} + 0.10 \cdot \text{GeoMatch}$$

### Final Personalized Trend Score:
$$S_{trend\_final} = \alpha \cdot R_{user} + (1 - \alpha) \cdot S_{market}$$

*(Default $\alpha = 0.70$ ensures user relevance dominates while retaining high-evidence market signals).*

---

## 4. Diversity & Anti-Fatigue Re-Ranking

To prevent consecutive repetitive stories from the same publisher, entity, or topic, a deterministic sliding-window re-ranking penalty is applied:

### Diversity Rules:
1. **Source Clustering Penalty**: If candidate $j$ shares the same `source_id` as an item already placed within the last $k=3$ positions in the feed, apply a penalty:
   $$Score_{penalized} = Score \cdot (1 - 0.25 \cdot \text{count\_in\_window})$$
2. **Topic Repetition Penalty**: If candidate $j$ shares $>75\%$ identical topics with the immediately preceding article, demote by $20\%$ unless total candidate score exceeds $0.85$.
3. **Entity Clustering Penalty**: No more than 2 consecutive articles primarily highlighting the same single company.
4. **Preservation of High Relevance**: Any article with raw score $\ge 0.90$ is exempt from heavy demotions to avoid suppressing critical breaking news.

---

## 5. Candidate Generation & Query Performance

Scoring is never computed against the entire database on every API request. Candidates are pre-filtered via indexed PostgreSQL queries:

```sql
SELECT a.id, a.published_at, ae.primary_domain, ae.relevance_score, ae.topics, ae.entities
FROM articles a
JOIN article_enrichment ae ON a.id = ae.article_id
WHERE a.status = 'published'
  AND a.published_at >= NOW() - INTERVAL '14 days'
  AND (
    ae.primary_domain = :user_domain
    OR ae.primary_domain = 'general_business'
    OR ae.topics && :user_topics_array
    OR ae.entities @> :user_entities_json
  )
ORDER BY a.published_at DESC
LIMIT 150;
```

Candidate set (typically 50–150 articles) is then scored, diversity-adjusted, and sliced in Python memory within $<30\text{ms}$.
