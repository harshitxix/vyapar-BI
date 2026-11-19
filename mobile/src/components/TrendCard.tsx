import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { TrendSummary } from '../types';
import { Flame, Zap, Compass, TrendingDown, Layers, Newspaper, ArrowUpRight } from 'lucide-react-native';

interface TrendCardProps {
  trend: TrendSummary;
  onPress: () => void;
}

export const TrendCard: React.FC<TrendCardProps> = ({ trend, onPress }) => {
  const getStatusBadge = () => {
    switch (trend.status) {
      case 'emerging':
        return { label: 'Emerging', color: '#38BDF8', bg: 'rgba(56, 189, 248, 0.12)', icon: <Zap size={11} color="#38BDF8" /> };
      case 'growing':
        return { label: 'Growing ↑', color: '#F97316', bg: 'rgba(249, 115, 22, 0.14)', icon: <Flame size={11} color="#F97316" /> };
      case 'established':
        return { label: 'Established', color: '#10B981', bg: 'rgba(16, 185, 129, 0.12)', icon: <Compass size={11} color="#10B981" /> };
      case 'cooling':
      case 'declining':
        return { label: 'Cooling 📉', color: '#94A3B8', bg: 'rgba(148, 163, 184, 0.12)', icon: <TrendingDown size={11} color="#94A3B8" /> };
      default:
        return { label: trend.status, color: '#A855F7', bg: 'rgba(168, 85, 247, 0.12)', icon: null };
    }
  };

  const status = getStatusBadge();
  const strengthPercent = Math.round((trend.strength_score || 0) * 100);

  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.82}
      onPress={onPress}
    >
      {/* Header Badges */}
      <View style={styles.topRow}>
        <View style={styles.badgeGroup}>
          <View style={[styles.statusBadge, { backgroundColor: status.bg }]}>
            {status.icon}
            <Text style={[styles.statusText, { color: status.color }]}>{status.label}</Text>
          </View>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{trend.category || 'Consumer Trend'}</Text>
          </View>
        </View>

        {/* Strength Score Indicator */}
        <View style={styles.scoreContainer}>
          <Text style={styles.scoreLabel}>Strength</Text>
          <Text style={styles.scoreValue}>{strengthPercent}</Text>
          <Text style={styles.scoreMax}>/100</Text>
        </View>
      </View>

      {/* Trend Name */}
      <Text style={styles.title} numberOfLines={2}>
        {trend.name}
      </Text>

      {/* Short Summary Description */}
      <Text style={styles.description} numberOfLines={3}>
        {trend.description}
      </Text>

      {/* Representative Topics Pills */}
      {trend.representative_topics && trend.representative_topics.length > 0 && (
        <View style={styles.topicRow}>
          {trend.representative_topics.slice(0, 3).map((topic, i) => (
            <View key={i} style={styles.topicPill}>
              <Text style={styles.topicText}>#{topic}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Footer Metrics */}
      <View style={styles.footer}>
        <View style={styles.evidenceStats}>
          <View style={styles.statItem}>
            <Newspaper size={12} color="#64748B" />
            <Text style={styles.statText}>{trend.article_count} articles</Text>
          </View>
          <Text style={styles.statDot}>•</Text>
          <View style={styles.statItem}>
            <Layers size={12} color="#64748B" />
            <Text style={styles.statText}>{trend.source_count} sources</Text>
          </View>
        </View>

        <View style={styles.exploreLink}>
          <Text style={styles.exploreText}>View Evidence</Text>
          <ArrowUpRight size={13} color="#38BDF8" />
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#111827',
    borderRadius: 12,
    padding: 14,
    marginHorizontal: 12,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#1F2937',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  badgeGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3.5,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  categoryBadge: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 7,
    paddingVertical: 3.5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
  },
  categoryText: {
    color: '#94A3B8',
    fontSize: 10.5,
    fontWeight: '600',
  },
  scoreContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.2)',
    gap: 2,
  },
  scoreLabel: {
    color: '#64748B',
    fontSize: 10,
    fontWeight: '600',
    marginRight: 2,
  },
  scoreValue: {
    color: '#38BDF8',
    fontSize: 13,
    fontWeight: '800',
  },
  scoreMax: {
    color: '#64748B',
    fontSize: 9.5,
    fontWeight: '600',
  },
  title: {
    fontSize: 15.5,
    fontWeight: '700',
    color: '#F9FAFB',
    lineHeight: 21,
    marginBottom: 6,
  },
  description: {
    fontSize: 12.5,
    color: '#94A3B8',
    lineHeight: 18,
    marginBottom: 10,
  },
  topicRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 5,
    marginBottom: 10,
  },
  topicPill: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 7,
    paddingVertical: 2.5,
    borderRadius: 4,
  },
  topicText: {
    color: '#7DD3FC',
    fontSize: 11,
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#1F2937',
  },
  evidenceStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    color: '#64748B',
    fontSize: 11,
    fontWeight: '600',
  },
  statDot: {
    color: '#475569',
    fontSize: 10,
  },
  exploreLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  exploreText: {
    color: '#38BDF8',
    fontSize: 11.5,
    fontWeight: '700',
  },
});
