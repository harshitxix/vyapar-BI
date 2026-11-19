import React from 'react';
import {
  Modal,
  View,
  Text,
  Image,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Linking,
  SafeAreaView,
} from 'react-native';
import {
  X,
  ExternalLink,
  Building2,
  Calendar,
  Globe,
  Sparkles,
  Tag,
  Briefcase,
  Zap,
} from 'lucide-react-native';
import { Article } from '../types';

interface ArticleModalProps {
  article: Article | null;
  visible: boolean;
  onClose: () => void;
}

export const ArticleModal: React.FC<ArticleModalProps> = ({ article, visible, onClose }) => {
  if (!article) return null;

  const handleOpenSource = () => {
    if (article.canonical_url) {
      Linking.openURL(article.canonical_url);
    }
  };

  const enrichment = article.enrichment;
  const relevancePct = enrichment?.relevance_score
    ? Math.round(enrichment.relevance_score * 100)
    : null;

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.container}>
        {/* Header Bar */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <X size={20} color="#F8FAFC" />
          </TouchableOpacity>
          <Text style={styles.headerTitle} numberOfLines={1}>
            {article.source_name}
          </Text>
          <View style={{ width: 36 }} />
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Cover Image */}
          {article.image_url ? (
            <Image
              source={{ uri: article.image_url }}
              style={styles.image}
              resizeMode="cover"
            />
          ) : null}

          <View style={styles.body}>
            {/* Domain & Region tags */}
            <View style={styles.tagRow}>
              <View style={styles.tag}>
                <Text style={styles.tagText}>
                  {(enrichment?.primary_domain || article.business_domain || 'BUSINESS').toUpperCase()}
                </Text>
              </View>
              <View style={styles.tagSecondary}>
                <Globe size={11} color="#38BDF8" />
                <Text style={styles.tagSecondaryText}>{(article.region || 'INDIA').toUpperCase()}</Text>
              </View>
              {relevancePct !== null && (
                <View style={styles.relevanceBadge}>
                  <Sparkles size={11} color="#34D399" />
                  <Text style={styles.relevanceText}>{relevancePct}% Kirana Match</Text>
                </View>
              )}
            </View>

            {/* Title */}
            <Text style={styles.title}>{article.title}</Text>

            {/* Metadata info */}
            <View style={styles.metadataCard}>
              <View style={styles.metaItem}>
                <Building2 size={14} color="#94A3B8" />
                <Text style={styles.metaLabel}>Source:</Text>
                <Text style={styles.metaValue}>{article.source_name}</Text>
              </View>
              <View style={styles.metaItem}>
                <Calendar size={14} color="#94A3B8" />
                <Text style={styles.metaLabel}>Published:</Text>
                <Text style={styles.metaValue}>
                  {new Date(article.published_at).toLocaleString()}
                </Text>
              </View>
              {article.author ? (
                <View style={styles.metaItem}>
                  <Text style={styles.metaLabel}>Author:</Text>
                  <Text style={styles.metaValue}>{article.author}</Text>
                </View>
              ) : null}
            </View>

            {/* AI Executive Summary */}
            {enrichment?.summary && (
              <View style={styles.aiSummarySection}>
                <View style={styles.sectionHeaderRow}>
                  <Zap size={14} color="#38BDF8" />
                  <Text style={styles.sectionHeader}>AI Executive Summary</Text>
                </View>
                <Text style={styles.aiSummaryText}>{enrichment.summary}</Text>
              </View>
            )}

            {/* Topics & Classification */}
            {enrichment?.topics && enrichment.topics.length > 0 && (
              <View style={styles.sectionContainer}>
                <Text style={styles.sectionHeader}>Key Topics</Text>
                <View style={styles.pillsRow}>
                  {enrichment.topics.map((topic, idx) => (
                    <View key={idx} style={styles.topicPill}>
                      <Tag size={10} color="#38BDF8" />
                      <Text style={styles.topicText}>{topic}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Named Entities */}
            {enrichment?.entities && enrichment.entities.length > 0 && (
              <View style={styles.sectionContainer}>
                <Text style={styles.sectionHeader}>Key Entities & Brands</Text>
                <View style={styles.pillsRow}>
                  {enrichment.entities.map((entity, idx) => (
                    <View key={idx} style={styles.entityPill}>
                      <Briefcase size={10} color="#F59E0B" />
                      <Text style={styles.entityName}>{entity.name}</Text>
                      <Text style={styles.entityType}>({entity.type})</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Raw Context / Excerpt */}
            {article.description && article.description !== enrichment?.summary && (
              <View style={styles.sectionContainer}>
                <Text style={styles.sectionHeader}>Article Context</Text>
                <Text style={styles.descriptionText}>{article.description}</Text>
              </View>
            )}

            {/* CTA Button */}
            <TouchableOpacity style={styles.ctaButton} onPress={handleOpenSource} activeOpacity={0.85}>
              <ExternalLink size={18} color="#0F172A" />
              <Text style={styles.ctaButtonText}>Read Original Article</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#1E293B',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '700',
  },
  scrollContent: {
    paddingBottom: 40,
  },
  image: {
    width: '100%',
    height: 220,
    backgroundColor: '#1E293B',
  },
  body: {
    padding: 20,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  tag: {
    backgroundColor: '#38BDF8',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  tagText: {
    color: '#0F172A',
    fontSize: 11,
    fontWeight: '800',
  },
  tagSecondary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#1E293B',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
  },
  tagSecondaryText: {
    color: '#38BDF8',
    fontSize: 11,
    fontWeight: '700',
  },
  relevanceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#064E3B',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  relevanceText: {
    color: '#34D399',
    fontSize: 11,
    fontWeight: '700',
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#F8FAFC',
    lineHeight: 28,
    marginBottom: 16,
  },
  metadataCard: {
    backgroundColor: '#1E293B',
    borderRadius: 10,
    padding: 14,
    gap: 8,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaLabel: {
    color: '#64748B',
    fontSize: 12,
    fontWeight: '600',
  },
  metaValue: {
    color: '#CBD5E1',
    fontSize: 12,
    fontWeight: '500',
    flexShrink: 1,
  },
  aiSummarySection: {
    backgroundColor: '#1E293B',
    borderRadius: 10,
    padding: 16,
    marginBottom: 20,
    borderLeftWidth: 4,
    borderLeftColor: '#38BDF8',
    borderWidth: 1,
    borderColor: '#334155',
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  sectionHeader: {
    fontSize: 13,
    fontWeight: '800',
    color: '#F8FAFC',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  aiSummaryText: {
    fontSize: 14,
    color: '#E2E8F0',
    lineHeight: 22,
  },
  sectionContainer: {
    marginBottom: 20,
  },
  pillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  topicPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#1E293B',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  topicText: {
    fontSize: 12,
    color: '#94A3B8',
    fontWeight: '600',
  },
  entityPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#1E293B',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#475569',
  },
  entityName: {
    fontSize: 12,
    color: '#F8FAFC',
    fontWeight: '600',
  },
  entityType: {
    fontSize: 10,
    color: '#F59E0B',
    fontWeight: '700',
  },
  descriptionText: {
    fontSize: 14,
    color: '#94A3B8',
    lineHeight: 22,
  },
  ctaButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#38BDF8',
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 10,
  },
  ctaButtonText: {
    color: '#0F172A',
    fontSize: 15,
    fontWeight: '800',
  },
});
