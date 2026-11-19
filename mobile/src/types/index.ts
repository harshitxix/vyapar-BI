export interface NamedEntity {
  name: string;
  type: string;
}

export interface BusinessEvent {
  type: string;
  description: string;
  date?: string | null;
}

export interface ArticleEnrichment {
  id: string;
  article_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
  summary: string | null;
  primary_domain: string | null;
  secondary_domains?: string[] | null;
  category: string | null;
  subcategory: string | null;
  article_type?: string | null;
  topics: string[] | null;
  keywords: string[] | null;
  entities: NamedEntity[] | null;
  events: BusinessEvent[] | null;
  relevance_score: number | null;
  confidence: number | null;
  model: string;
  prompt_version: string;
  latency_ms: number;
}

export interface Article {
  id: string;
  source_id: string;
  source_name: string;
  source_domain: string;
  title: string;
  description: string | null;
  author: string | null;
  original_url: string;
  canonical_url: string;
  image_url: string | null;
  published_at: string;
  fetched_at: string;
  language: string;
  region: string;
  business_domain: string;
  category: string | null;
  subcategory: string | null;
  content_type: string;
  extraction_method: string;
  status: string;
  created_at: string;
  enrichment?: ArticleEnrichment | null;
}

export interface FeedResponse {
  status: string;
  count: number;
  has_more: boolean;
  next_cursor: string | null;
  items: Article[];
}

export interface SourceHealth {
  id: string;
  name: string;
  domain: string;
  status: 'healthy' | 'degraded' | 'failed' | 'inactive';
  failure_count: number;
  last_checked: string | null;
  last_success: string | null;
  last_failure: string | null;
  last_response_time_ms: number | null;
  last_article_count: number;
}

export interface SupportingArticleItem {
  id: string;
  title: string;
  source_name: string;
  published_at: string;
  original_url: string;
  image_url?: string | null;
  similarity_score: number;
}

export interface TrendSummary {
  id: string;
  name: string;
  description: string;
  domain: string;
  region: string;
  category: string;
  status: 'emerging' | 'growing' | 'established' | 'cooling' | 'declining' | 'inactive';
  evidence_grade: 'high' | 'medium' | 'low';
  strength_score: number;
  confidence_score: number;
  momentum_score: number;
  article_count: number;
  source_count: number;
  first_detected_at: string;
  last_updated_at: string;
  representative_topics: string[];
}

export interface TrendDetail extends TrendSummary {
  why_emerging?: string | null;
  key_developments: string[];
  coherence_score: number;
  diversity_score: number;
  representative_entities: string[];
  supporting_articles: SupportingArticleItem[];
}

export interface TrendSnapshot {
  id: string;
  timestamp: string;
  article_count: number;
  source_count: number;
  strength_score: number;
  momentum_score: number;
  status: string;
}

// ==========================================
// Phase 4: Personalization Interfaces
// ==========================================

export interface UserMarketProfile {
  id?: string;
  user_id?: string;
  business_name?: string | null;
  business_domain: string;
  business_subdomain?: string | null;
  business_description?: string | null;
  country?: string;
  state?: string | null;
  city?: string | null;
  preferred_language?: string;
}

export interface TopicInterest {
  id: string;
  user_id: string;
  topic_id: string;
  preference_source: string;
  preference_score: number;
  is_explicit: boolean;
  created_at: string;
}

export interface CanonicalEntity {
  id: string;
  name: string;
  entity_type: string;
  aliases?: string[] | null;
  domain?: string | null;
  is_followed?: boolean;
}

export interface PersonalizationMetadata {
  reasons: string[];
  matched_topics: string[];
  matched_entities: string[];
  signals?: Record<string, number>;
}

export interface PersonalizedFeedItem {
  type: 'article' | 'trend';
  id: string;
  title: string;
  description?: string | null;
  source_id?: string;
  source_name?: string;
  source_domain?: string;
  original_url?: string;
  canonical_url?: string;
  image_url?: string | null;
  published_at?: string;
  business_domain?: string;
  category?: string | null;
  subcategory?: string | null;
  relevance_score?: number | null;
  strength_score?: number;
  user_relevance_score?: number;
  final_score?: number;
  article_count?: number;
  source_count?: number;
  status?: string;
  evidence_grade?: string;
  enrichment?: ArticleEnrichment | null;
  personalization: PersonalizationMetadata;
}

export interface PersonalizedFeedResponse {
  status: string;
  count: number;
  total_candidates?: number;
  has_more: boolean;
  next_cursor: string | null;
  items: PersonalizedFeedItem[];
  diagnostics?: Record<string, any>;
}

export interface FeedPreferences {
  settings: {
    freshness_bias: number;
    trend_bias: number;
    geographic_bias: number;
    followed_entities_bias: number;
    behavioural_personalization_enabled: boolean;
  };
}


