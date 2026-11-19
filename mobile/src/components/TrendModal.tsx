import React, { useEffect, useState } from 'react';
import {
  Modal,
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Linking,
  ActivityIndicator,
} from 'react-native';
import { TrendDetail, TrendSummary } from '../types';
import { fetchTrendDetail } from '../api/client';
import {
  X,
  ExternalLink,
  Flame,
  Zap,
  Compass,
  TrendingDown,
  ShieldCheck,
  CheckCircle2,
  Newspaper,
  Layers,
  Sparkles,
} from 'lucide-react-native';

interface TrendModalProps {
  trendSummary: TrendSummary | null;
  visible: boolean;
  onClose: () => void;
}

export const TrendModal: React.FC<TrendModalProps> = ({
  trendSummary,
  visible,
  onClose,
}) => {
  const [detail, setDetail] = useState<TrendDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (visible && trendSummary) {
      setLoading(true);
      fetchTrendDetail(trendSummary.id)
        .then((data) => setDetail(data))
        .catch((err) => console.error('Failed to load trend detail:', err))
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [visible, trendSummary]);

  if (!trendSummary) return null;

  const getStatusBadge = () => {
    switch (trendSummary.status) {
      case 'emerging':
        return { label: 'Emerging', color: '#38BDF8', bg: 'rgba(56, 189, 248, 0.15)', icon: <Zap size={13} color="#38BDF8" /> };
      case 'growing':
        return { label: 'Growing ↑', color: '#F97316', bg: 'rgba(249, 115, 22, 0.18)', icon: <Flame size={13} color="#F97316" /> };
      case 'established':
        return { label: 'Established', color: '#10B981', bg: 'rgba(16, 185, 129, 0.15)', icon: <Compass size={13} color="#10B981" /> };
      case 'cooling':
      case 'declining':
        return { label: 'Cooling 📉', color: '#94A3B8', bg: 'rgba(148, 163, 184, 0.15)', icon: <TrendingDown size={13} color="#94A3B8" /> };
      default:
        return { label: trendSummary.status, color: '#A855F7', bg: 'rgba(168, 85, 247, 0.15)', icon: null };
    }
  };

  const status = getStatusBadge();
  const strengthPercent = Math.round((trendSummary.strength_score || 0) * 100);

  const openUrl = (url: string) => {
    if (url) {
      Linking.openURL(url).catch((err) => console.error('Failed to open URL:', err));
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContainer}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <View style={[styles.statusBadge, { backgroundColor: status.bg }]}>
                {status.icon}
                <Text style={[styles.statusText, { color: status.color }]}>{status.label}</Text>
              </View>
              <View style={styles.categoryBadge}>
                <Text style={styles.categoryText}>{trendSummary.category}</Text>
              </View>
            </View>

            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <X size={18} color="#94A3B8" />
            </TouchableOpacity>
          </View>

          {loading ? (
            <View style={styles.loaderContainer}>
              <ActivityIndicator size="large" color="#38BDF8" />
              <Text style={styles.loadingText}>Analyzing Trend Intelligence & Evidence...</Text>
            </View>
          ) : (
            <ScrollView
              style={styles.scrollContent}
              contentContainerStyle={styles.scrollInner}
              showsVerticalScrollIndicator={false}
            >
              {/* Trend Title */}
              <Text style={styles.trendTitle}>{detail?.name || trendSummary.name}</Text>

              {/* Metrics Grid */}
              <View style={styles.metricsGrid}>
                <View style={styles.metricCard}>
                  <Text style={styles.metricLabel}>Trend Strength</Text>
                  <Text style={styles.metricValue}>{strengthPercent}/100</Text>
                </View>

                <View style={styles.metricCard}>
                  <Text style={styles.metricLabel}>Evidence Grade</Text>
                  <View style={styles.gradeRow}>
                    <ShieldCheck size={13} color="#34D399" />
                    <Text style={styles.gradeValue}>{(trendSummary.evidence_grade || 'medium').toUpperCase()}</Text>
                  </View>
                </View>

                <View style={styles.metricCard}>
                  <Text style={styles.metricLabel}>Supporting Data</Text>
                  <Text style={styles.metricValue}>
                    {trendSummary.article_count} <Text style={styles.metricUnit}>stories</Text>
                  </Text>
                </View>
              </View>

              {/* What is happening? */}
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>What is Happening?</Text>
                <Text style={styles.bodyText}>
                  {detail?.description || trendSummary.description}
                </Text>
              </View>

              {/* Why the system detected it */}
              {(detail?.why_emerging || trendSummary.description) && (
                <View style={styles.detectionCard}>
                  <View style={styles.detectionHeader}>
                    <Sparkles size={14} color="#38BDF8" />
                    <Text style={styles.detectionTitle}>Why the System Detected This</Text>
                  </View>
                  <Text style={styles.detectionText}>
                    {detail?.why_emerging ||
                      `Detected based on statistical clustering across ${trendSummary.article_count} articles and ${trendSummary.source_count} independent publishers in the ${trendSummary.domain} sector.`}
                  </Text>
                </View>
              )}

              {/* Key Developments */}
              {detail?.key_developments && detail.key_developments.length > 0 && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>Key Factual Developments</Text>
                  <View style={styles.developmentsList}>
                    {detail.key_developments.map((dev, idx) => (
                      <View key={idx} style={styles.developmentItem}>
                        <CheckCircle2 size={14} color="#34D399" style={styles.checkIcon} />
                        <Text style={styles.developmentText}>{dev}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}

              {/* Key Topics & Entities */}
              {((detail?.representative_topics && detail.representative_topics.length > 0) ||
                (detail?.representative_entities && detail.representative_entities.length > 0)) && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>Market Entities & Facets</Text>
                  <View style={styles.pillsContainer}>
                    {detail?.representative_topics?.map((topic, i) => (
                      <View key={`t-${i}`} style={styles.topicPill}>
                        <Text style={styles.topicPillText}>#{topic}</Text>
                      </View>
                    ))}
                    {detail?.representative_entities?.map((ent, i) => (
                      <View key={`e-${i}`} style={styles.entityPill}>
                        <Text style={styles.entityPillText}>{ent}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}

              {/* Supporting Articles Evidence */}
              {detail?.supporting_articles && detail.supporting_articles.length > 0 && (
                <View style={styles.section}>
                  <View style={styles.supportingHeader}>
                    <Text style={styles.sectionTitle}>Supporting Articles Evidence</Text>
                    <Text style={styles.supportingCount}>
                      {detail.supporting_articles.length} verified sources
                    </Text>
                  </View>

                  <View style={styles.articlesList}>
                    {detail.supporting_articles.map((art) => (
                      <TouchableOpacity
                        key={art.id}
                        style={styles.articleItem}
                        onPress={() => openUrl(art.original_url)}
                      >
                        <View style={styles.articleItemLeft}>
                          <Text style={styles.articleItemSource}>{art.source_name}</Text>
                          <Text style={styles.articleItemTitle} numberOfLines={2}>
                            {art.title}
                          </Text>
                        </View>
                        <ExternalLink size={14} color="#38BDF8" style={styles.linkIcon} />
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.78)',
    justifyContent: 'flex-end',
  },
  modalContainer: {
    backgroundColor: '#0F172A',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    height: '88%',
    borderTopWidth: 1,
    borderColor: '#334155',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11.5,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  categoryBadge: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  categoryText: {
    color: '#94A3B8',
    fontSize: 11,
    fontWeight: '600',
  },
  closeButton: {
    backgroundColor: '#1E293B',
    padding: 6,
    borderRadius: 18,
  },
  loaderContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '600',
  },
  scrollContent: {
    flex: 1,
  },
  scrollInner: {
    padding: 16,
    paddingBottom: 40,
  },
  trendTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#F8FAFC',
    lineHeight: 26,
    marginBottom: 14,
  },
  metricsGrid: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  metricCard: {
    flex: 1,
    backgroundColor: '#1E293B',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  metricLabel: {
    color: '#64748B',
    fontSize: 10,
    fontWeight: '600',
    marginBottom: 4,
  },
  metricValue: {
    color: '#F1F5F9',
    fontSize: 14,
    fontWeight: '800',
  },
  metricUnit: {
    color: '#64748B',
    fontSize: 11,
    fontWeight: '500',
  },
  gradeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  gradeValue: {
    color: '#34D399',
    fontSize: 13,
    fontWeight: '800',
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 13.5,
    fontWeight: '700',
    color: '#E2E8F0',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  bodyText: {
    fontSize: 13.5,
    color: '#CBD5E1',
    lineHeight: 20,
  },
  detectionCard: {
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.25)',
    marginBottom: 16,
  },
  detectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  detectionTitle: {
    color: '#38BDF8',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  detectionText: {
    color: '#93C5FD',
    fontSize: 12.5,
    lineHeight: 18,
  },
  developmentsList: {
    gap: 8,
  },
  developmentItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: '#1E293B',
    padding: 10,
    borderRadius: 8,
  },
  checkIcon: {
    marginTop: 2,
  },
  developmentText: {
    flex: 1,
    color: '#E2E8F0',
    fontSize: 12.5,
    lineHeight: 18,
  },
  pillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  topicPill: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  topicPillText: {
    color: '#38BDF8',
    fontSize: 11.5,
    fontWeight: '600',
  },
  entityPill: {
    backgroundColor: '#0F172A',
    borderColor: '#334155',
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  entityPillText: {
    color: '#E2E8F0',
    fontSize: 11.5,
    fontWeight: '500',
  },
  supportingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  supportingCount: {
    color: '#64748B',
    fontSize: 11.5,
    fontWeight: '600',
  },
  articlesList: {
    gap: 6,
  },
  articleItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1E293B',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  articleItemLeft: {
    flex: 1,
    paddingRight: 8,
  },
  articleItemSource: {
    color: '#38BDF8',
    fontSize: 10.5,
    fontWeight: '700',
    marginBottom: 2,
  },
  articleItemTitle: {
    color: '#F1F5F9',
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '500',
  },
  linkIcon: {
    marginLeft: 4,
  },
});
