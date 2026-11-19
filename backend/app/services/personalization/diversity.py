from typing import List, Set
from backend.app.services.personalization.scoring import ScoredArticle
from backend.app.services.personalization.config import (
    PersonalizationConfig,
    DEFAULT_PERSONALIZATION_CONFIG,
)


class DiversityService:
    """
    Applies sliding-window diversity rules to prevent publisher, topic,
    or entity fatigue while preserving top-relevance market intelligence.
    """

    @classmethod
    def apply_diversity_reranking(
        cls,
        scored_articles: List[ScoredArticle],
        config: PersonalizationConfig = DEFAULT_PERSONALIZATION_CONFIG,
    ) -> List[ScoredArticle]:
        """
        Re-ranks a candidate list using a greedy selection algorithm with
        diversity penalties.
        """
        if len(scored_articles) <= 2:
            return sorted(scored_articles, key=lambda a: a.final_score, reverse=True)

        remaining = list(scored_articles)
        ordered: List[ScoredArticle] = []

        window_size = config.diversity_window_size

        while remaining:
            best_idx = -1
            best_penalized_score = -float("inf")

            recent_window = ordered[-window_size:] if ordered else []
            recent_sources = [a.candidate.article.source_id for a in recent_window]
            prev_article = ordered[-1] if ordered else None

            for i, cand in enumerate(remaining):
                score = cand.final_score
                source_id = cand.candidate.article.source_id

                # Exempt extremely high relevance stories (e.g. >= 0.90) from heavy demotion
                if score < config.diversity_high_relevance_exemption:
                    # 1. Source penalty
                    source_occurrences = recent_sources.count(source_id)
                    if source_occurrences > 0:
                        penalty = config.diversity_source_penalty * source_occurrences
                        score *= max(0.2, 1.0 - penalty)

                    # 2. Topic repetition penalty
                    if prev_article and cand.candidate.topics and prev_article.candidate.topics:
                        cand_topics = set(t.lower() for t in cand.candidate.topics)
                        prev_topics = set(t.lower() for t in prev_article.candidate.topics)
                        intersection = cand_topics.intersection(prev_topics)
                        overlap_ratio = len(intersection) / max(1, len(cand_topics))
                        if overlap_ratio >= config.diversity_topic_overlap_threshold:
                            score *= (1.0 - config.diversity_topic_penalty)

                    # 3. Consecutive entity penalty
                    if len(ordered) >= config.diversity_max_consecutive_entity and cand.matched_entities:
                        last_entities = [
                            set(a.matched_entities) for a in ordered[-config.diversity_max_consecutive_entity:]
                        ]
                        cand_entity_set = set(cand.matched_entities)
                        if all(cand_entity_set.intersection(le) for le in last_entities):
                            score *= 0.70

                if score > best_penalized_score:
                    best_penalized_score = score
                    best_idx = i

            selected = remaining.pop(best_idx)
            ordered.append(selected)

        return ordered
