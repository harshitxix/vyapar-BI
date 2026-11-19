import React, { useState } from 'react';
import { View, Text, Image, StyleSheet, TouchableOpacity, Share } from 'react-native';
import { Bookmark, Share2, Sparkles, ThumbsDown, Check } from 'lucide-react-native';
import { Article } from '../types';
import { recordInteraction } from '../api/client';

interface ArticleCardProps {
  article: Article | any;
  onPress: () => void;
  onDismiss?: (articleId: string) => void;
}

const DOMAIN_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  grocery: { bg: 'rgba(6, 78, 59, 0.4)', text: '#34D399', border: '#065F46' },
  retail: { bg: 'rgba(49, 46, 129, 0.4)', text: '#A5B4FC', border: '#3730A3' },
  fmcg: { bg: 'rgba(30, 58, 138, 0.4)', text: '#60A5FA', border: '#1E40AF' },
  technology: { bg: 'rgba(76, 29, 149, 0.4)', text: '#C4B5FD', border: '#5B21B6' },
  fashion: { bg: 'rgba(131, 24, 67, 0.4)', text: '#F472B6', border: '#9D174D' },
  electronics: { bg: 'rgba(3, 105, 161, 0.4)', text: '#38BDF8', border: '#0284C7' },
  restaurants: { bg: 'rgba(180, 83, 9, 0.4)', text: '#FBBF24', border: '#B45309' },
  general_business: { bg: 'rgba(30, 41, 59, 0.5)', text: '#94A3B8', border: '#334155' },
};

function formatTimeAgo(dateString?: string): string {
  if (!dateString) return 'Recent';
  try {
    const diff = (Date.now() - new Date(dateString).getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return 'Recent';
  }
}

export const ArticleCard: React.FC<ArticleCardProps> = ({ article, onPress, onDismiss }) => {
  const [imageError, setImageError] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  const enrichment = article.enrichment;
  const domainKey = (
    enrichment?.primary_domain ||
    article.business_domain ||
    'general_business'
  ).toLowerCase();
  const domainStyle = DOMAIN_COLORS[domainKey] || DOMAIN_COLORS.general_business;

  const score = article.relevance_score ?? enrichment?.relevance_score;
  const relevancePct = score ? Math.round(score * 100) : null;

  // Grounded explanation reason
  const reasons: string[] = article.personalization?.reasons || [];
  const primaryReason = reasons.length > 0 ? reasons[0] : null;

  const handleCardPress = () => {
    recordInteraction({
      event_type: 'article_open',
      article_id: article.id,
      topic_id: enrichment?.topics?.[0],
      entity_id: article.personalization?.matched_entities?.[0],
    });
    onPress();
  };

  const handleToggleSave = () => {
    const nextSaved = !isSaved;
    setIsSaved(nextSaved);
    recordInteraction({
      event_type: nextSaved ? 'article_save' : 'article_dismiss',
      article_id: article.id,
    });
  };

  const handleNotInterested = () => {
    setIsDismissed(true);
    recordInteraction({
      event_type: 'article_not_interested',
      article_id: article.id,
      topic_id: enrichment?.topics?.[0],
    });
    if (onDismiss) {
      onDismiss(article.id);
    }
  };

  const handleShare = async () => {
    try {
      recordInteraction({
        event_type: 'article_share',
        article_id: article.id,
      });
      await Share.share({
        message: `${article.title}\n\nRead more: ${article.canonical_url || article.original_url}`,
      });
    } catch (error) {
      console.error('Share error:', error);
    }
  };

  if (isDismissed) {
    return (
      <View style={styles.dismissedCard}>
        <Text style={styles.dismissedText}>Article hidden • Feed adjusted</Text>
      </View>
    );
  }

  const displayText = enrichment?.summary || article.description;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={handleCardPress}
      activeOpacity={0.85}
    >
      <View style={styles.topRow}>
        <View style={styles.badgeGroup}>
          <View style={[styles.domainBadge, { backgroundColor: domainStyle.bg, borderColor: domainStyle.border }]}>
            <Text style={[styles.domainText, { color: domainStyle.text }]}>
              {domainKey.toUpperCase()}
            </Text>
          </View>

          {relevancePct !== null && (
            <View style={[styles.relevanceBadge, relevancePct >= 75 ? styles.highRelevance : styles.medRelevance]}>
              <Sparkles size={9} color={relevancePct >= 75 ? '#34D399' : '#38BDF8'} />
              <Text style={[styles.relevanceText, { color: relevancePct >= 75 ? '#34D399' : '#38BDF8' }]}>
                {relevancePct}% Match
              </Text>
            </View>
          )}
        </View>

        <View style={styles.sourceMeta}>
          <Text style={styles.sourceName} numberOfLines={1}>
            {article.source_name || article.source_domain}
          </Text>
          <Text style={styles.dot}>•</Text>
          <Text style={styles.timeAgo}>{formatTimeAgo(article.published_at)}</Text>
        </View>
      </View>

      {/* Grounded explanation pill */}
      {primaryReason && (
        <View style={styles.reasonBadge}>
          <Sparkles size={10} color="#F59E0B" />
          <Text style={styles.reasonText} numberOfLines={1}>
            {primaryReason}
          </Text>
        </View>
      )}

      {/* Main Body: Text on left, optional compact thumbnail on right */}
      <View style={styles.bodyRow}>
        <View style={styles.textContent}>
          <Text style={styles.title} numberOfLines={2}>
            {article.title}
          </Text>

          {displayText ? (
            <Text style={styles.snippet} numberOfLines={2}>
              {displayText}
            </Text>
          ) : null}
        </View>

        {article.image_url && !imageError && (
          <Image
            source={{ uri: article.image_url }}
            style={styles.thumbnail}
            resizeMode="cover"
            onError={() => setImageError(true)}
          />
        )}
      </View>

      {/* Topics & Footer Row */}
      <View style={styles.footerRow}>
        <View style={styles.topicsContainer}>
          {enrichment?.topics && enrichment.topics.length > 0 ? (
            enrichment.topics.slice(0, 2).map((topic: string, idx: number) => (
              <View key={idx} style={styles.topicPill}>
                <Text style={styles.topicText}>#{topic}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.readPrompt}>Read intelligence →</Text>
          )}
        </View>

        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={styles.iconHitArea}
            onPress={handleToggleSave}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Bookmark
              size={16}
              color={isSaved ? '#38BDF8' : '#64748B'}
              fill={isSaved ? '#38BDF8' : 'transparent'}
            />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.iconHitArea}
            onPress={handleNotInterested}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <ThumbsDown size={15} color="#64748B" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.iconHitArea}
            onPress={handleShare}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Share2 size={16} color="#64748B" />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#131B2E',
    borderRadius: 12,
    marginHorizontal: 12,
    marginBottom: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#1E293B',
  },
  dismissedCard: {
    backgroundColor: '#0F172A',
    borderRadius: 8,
    marginHorizontal: 12,
    marginBottom: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#1E293B',
    alignItems: 'center',
  },
  dismissedText: {
    color: '#64748B',
    fontSize: 12,
    fontStyle: 'italic',
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  badgeGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  domainBadge: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 5,
    borderWidth: 1,
  },
  domainText: {
    fontSize: 9.5,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  relevanceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 5,
    borderWidth: 1,
  },
  highRelevance: {
    backgroundColor: 'rgba(6, 78, 59, 0.35)',
    borderColor: '#065F46',
  },
  medRelevance: {
    backgroundColor: 'rgba(14, 116, 144, 0.35)',
    borderColor: '#0E7490',
  },
  relevanceText: {
    fontSize: 9.5,
    fontWeight: '700',
  },
  reasonBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    borderColor: 'rgba(245, 158, 11, 0.3)',
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginBottom: 8,
  },
  reasonText: {
    color: '#FCD34D',
    fontSize: 11,
    fontWeight: '600',
    flexShrink: 1,
  },
  sourceMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  sourceName: {
    fontSize: 11,
    color: '#94A3B8',
    fontWeight: '600',
    maxWidth: 110,
  },
  dot: {
    color: '#475569',
    fontSize: 10,
  },
  timeAgo: {
    fontSize: 10.5,
    color: '#64748B',
  },
  bodyRow: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  textContent: {
    flex: 1,
  },
  title: {
    fontSize: 14.5,
    fontWeight: '700',
    color: '#F1F5F9',
    lineHeight: 20,
    marginBottom: 4,
  },
  snippet: {
    fontSize: 12,
    color: '#94A3B8',
    lineHeight: 16.5,
  },
  thumbnail: {
    width: 68,
    height: 68,
    borderRadius: 8,
    backgroundColor: '#0F172A',
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: 'rgba(51, 65, 85, 0.5)',
    paddingTop: 8,
    marginTop: 2,
  },
  topicsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexShrink: 1,
  },
  topicPill: {
    backgroundColor: '#0F172A',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#1E293B',
  },
  topicText: {
    fontSize: 10.5,
    color: '#64748B',
    fontWeight: '600',
  },
  readPrompt: {
    fontSize: 11,
    fontWeight: '600',
    color: '#38BDF8',
  },
  actionButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconHitArea: {
    padding: 2,
  },
});
