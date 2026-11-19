# Personalization Engine Architecture Specification (Phase 4)

This document specifies the software architecture, modular services, feedback loops, explainability layer, and API contracts for the Phase 4 Personalization Engine.

---

## 1. High-Level Architecture

The Personalization Engine operates as an independent service layer downstream from Phase 1 (Ingestion), Phase 2 (AI Enrichment), and Phase 3 (Trend Detection):

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Layer                                 │
│  ┌───────────────────────┬──────────────────────┬───────────────────┐  │
│  │ /users/me/market-prof │ /feed/for-you        │ /interactions     │  │
│  │ /users/me/interests   │ /feed/following      │ /users/me/feed-   │  │
│  │ /users/me/followed-ent│ /trends/for-you      │  preferences      │  │
│  └───────────┬───────────┴──────────┬───────────┴───────────┬───────┘  │
└──────────────┼──────────────────────┼───────────────────────┼──────────┘
               │                      │                       │
               ▼                      ▼                       ▼
┌──────────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│  UserProfileService &    │ │CandidateGenerator│ │  FeedbackService &   │
│  EntityFollowService     │ │(Indexed SQL sets)│ │  InteractionLogger   │
└──────────────┬───────────┘ └────────┬─────────┘ └───────────┬──────────┘
               │                      │                       │
               ▼                      ▼                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Personalization Ranking Engine                       │
│  ┌──────────────────────┬──────────────────────┬────────────────────┐  │
│  │ArticleRelevanceServ  │ TrendRelevanceServ   │ DiversityService   │  │
│  │(8-signal scoring)    │ (User vs Market sep) │ (MMR / Anti-fatig) │  │
│  └──────────────────────┴──────────────────────┴────────────────────┘  │
│                                     │                                  │
│                                     ▼                                  │
│                         ExplainabilityService                          │
│               (Human-readable, factual reasons from signals)            │
└─────────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Personalized Feed Response                         │
│       - Ranked Articles & Trends with Explanations & Pagination        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Separation & Responsibilities

1. **`UserProfileService`**: Manages CRUD operations for user market profiles, language preferences, and business location context.
2. **`InterestService`**: Manages topic subscriptions, taxonomy normalization, and interest priority weights.
3. **`EntityFollowService`**: Manages canonical entity lookup and user follow relationships.
4. **`CandidateGenerationService`**: Executes fast, indexed PostgreSQL queries retrieving candidate articles and trends matching domain, topics, entities, or location within a configurable time window (default 14 days).
5. **`ArticleRelevanceService`**: Computes deterministic 8-signal article scores ($0.0 - 1.0$) using configurable weights.
6. **`TrendRelevanceService`**: Combines Phase 3 global trend strength with Phase 4 user-specific market relevance.
7. **`DiversityService`**: Applies sliding-window penalties to prevent publisher and topic concentration.
8. **`ExplainabilityService`**: Generates grounded, human-readable explanations based on the highest-scoring signals.
9. **`FeedbackService`**: Ingests interaction events (`article_open`, `article_save`, `article_dismiss`, `article_not_interested`) and computes bounded preference adjustments.

---

## 3. Feedback Loop & Implicit/Explicit Signals

```text
User Action            Signal Type     Weight / Effect
---------------------  ------------    ---------------------------------------
Save article           Explicit (+3)   +0.15 to matching topics & entities
Follow topic           Explicit (+5)   +0.30 immediate priority boost
Not interested         Explicit (-4)   -0.25 to dominant topic, suppresses story
Dismiss / hide         Explicit (-2)   -0.10 to matching topic
Open article           Implicit (+1)   +0.03 to matching topics (weak positive)
View article (scroll)  Implicit (0)    Recorded for impressions, 0 score change
```

- **Bounds**: Learned preference scores are strictly clamped to $[0.0, 1.0]$.
- **Decay**: Inferred preferences decay towards baseline ($0.5$) with a 14-day half-life to prevent early actions from permanently distorting the feed.
- **Privacy & Reset**: Users can view all inferred weights and reset them instantly via `POST /users/me/preferences/reset`.

---

## 4. Explainable Personalization

Every personalized item includes human-readable reasons derived strictly from the active signals that triggered its rank:

| Trigger Condition | Generated Reason |
|---|---|
| Domain Match ($S_1 \ge 0.8$) | *"Relevant to your [grocery/retail] business"* |
| Topic Overlap ($S_2 \ge 0.5$) | *"Matches your interest in [Quick Commerce, FMCG]"* |
| Followed Entity ($S_3 \ge 0.5$) | *"Related to a company you follow ([Blinkit, DMart])"* |
| Local Geo Match ($S_4 \ge 0.8$) | *"Trending in your market ([Gurugram, Haryana])"* |
| Active Market Trend ($S_6 \ge 0.6$)| *"Part of emerging market trend: [Rapid Expansion of Quick Commerce]"* |

Raw mathematical values (weights, internal floating-point values) are never shown to the end-user, but remain accessible to admins in debug mode.

---

## 5. Resilience & Fallback Guarantees

If the Personalization Engine encounters any database timeouts or missing profile data:
1. **Never throw a 500 error on the home feed**.
2. **Graceful Fallback**: Automatically deliver the general chronological feed (`/feed/latest`) filtered by the user's primary domain if known, or all domains.
3. Ingestion, AI enrichment, and Trend clustering continue running completely uninterrupted.
