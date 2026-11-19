import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch,
  ActivityIndicator,
  Alert,
} from 'react-native';
import {
  X,
  Sliders,
  RotateCcw,
  Sparkles,
  MapPin,
  Tag,
  Building,
  Check,
  ChevronRight,
} from 'lucide-react-native';
import {
  fetchUserProfile,
  fetchUserInterests,
  removeUserInterest,
  addUserInterest,
  fetchFollowedEntities,
  fetchEntities,
  followEntity,
  unfollowEntity,
  fetchFeedPreferences,
  updateFeedPreferences,
  resetLearnedPreferences,
} from '../api/client';

interface PersonalizationSettingsModalProps {
  visible: boolean;
  onClose: () => void;
  onPreferencesUpdated: () => void;
  onOpenOnboarding: () => void;
}

export const PersonalizationSettingsModal: React.FC<PersonalizationSettingsModalProps> = ({
  visible,
  onClose,
  onPreferencesUpdated,
  onOpenOnboarding,
}) => {
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<any>(null);
  const [interests, setInterests] = useState<any[]>([]);
  const [followedEntities, setFollowedEntities] = useState<any[]>([]);
  const [allEntities, setAllEntities] = useState<any[]>([]);

  // Feed preferences
  const [freshnessBias, setFreshnessBias] = useState<number>(1.0);
  const [trendBias, setTrendBias] = useState<number>(1.0);
  const [geoBias, setGeoBias] = useState<number>(1.0);
  const [behaviouralEnabled, setBehaviouralEnabled] = useState<boolean>(true);

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (visible) {
      loadSettings();
    }
  }, [visible]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [prof, userInt, followed, allEnt, feedPref] = await Promise.all([
        fetchUserProfile(),
        fetchUserInterests(),
        fetchFollowedEntities(),
        fetchEntities(),
        fetchFeedPreferences(),
      ]);

      setProfile(prof);
      setInterests(userInt);
      setFollowedEntities(followed);
      setAllEntities(allEnt);

      if (feedPref) {
        setFreshnessBias(feedPref.freshness_bias ?? 1.0);
        setTrendBias(feedPref.trend_bias ?? 1.0);
        setGeoBias(feedPref.geographic_bias ?? 1.0);
        setBehaviouralEnabled(feedPref.behavioural_personalization_enabled ?? true);
      }
    } catch (err) {
      console.error('Failed to load personalization settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSavePreferences = async () => {
    try {
      setSaving(true);
      await updateFeedPreferences({
        freshness_bias: freshnessBias,
        trend_bias: trendBias,
        geographic_bias: geoBias,
        behavioural_personalization_enabled: behaviouralEnabled,
      });
      onPreferencesUpdated();
      onClose();
    } catch (err) {
      console.error('Failed to save feed preferences:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveInterest = async (topicId: string) => {
    try {
      await removeUserInterest(topicId);
      setInterests(interests.filter((i) => i.topic_id !== topicId));
      onPreferencesUpdated();
    } catch (err) {
      console.error('Failed to remove topic:', err);
    }
  };

  const handleToggleFollow = async (entId: string, isFollowed: boolean) => {
    try {
      if (isFollowed) {
        await unfollowEntity(entId);
        setFollowedEntities(followedEntities.filter((e) => e.id !== entId));
      } else {
        await followEntity(entId);
        const target = allEntities.find((e) => e.id === entId);
        if (target) {
          setFollowedEntities([...followedEntities, target]);
        }
      }
      onPreferencesUpdated();
    } catch (err) {
      console.error('Failed to toggle entity follow:', err);
    }
  };

  const handleResetPreferences = async () => {
    try {
      await resetLearnedPreferences();
      Alert.alert(
        'Learned Preferences Reset',
        'All interaction-derived preferences have been reset. Your explicit business domain and chosen topics remain intact.'
      );
      onPreferencesUpdated();
    } catch (err) {
      console.error('Failed to reset learned preferences:', err);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Sliders size={20} color="#38BDF8" />
              <Text style={styles.headerTitle}>Personalization Settings</Text>
            </View>
            <TouchableOpacity onPress={onClose} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <X size={20} color="#94A3B8" />
            </TouchableOpacity>
          </View>

          {loading ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color="#38BDF8" />
              <Text style={styles.loadingText}>Loading settings...</Text>
            </View>
          ) : (
            <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
              {/* Profile Card */}
              <View style={styles.section}>
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionTitle}>Business Market Profile</Text>
                  <TouchableOpacity
                    style={styles.editProfileBtn}
                    onPress={() => {
                      onClose();
                      onOpenOnboarding();
                    }}
                  >
                    <Text style={styles.editProfileBtnText}>Edit Profile</Text>
                    <ChevronRight size={14} color="#38BDF8" />
                  </TouchableOpacity>
                </View>

                <View style={styles.profileCard}>
                  <Text style={styles.profileDomain}>
                    {profile?.business_domain?.toUpperCase() || 'GENERAL'}
                  </Text>
                  {profile?.business_subdomain && (
                    <Text style={styles.profileSubdomain}>
                      Subdomain: {profile.business_subdomain}
                    </Text>
                  )}
                  {profile?.city && (
                    <View style={styles.locationRow}>
                      <MapPin size={13} color="#94A3B8" />
                      <Text style={styles.locationText}>
                        {profile.city}, {profile.state || 'India'}
                      </Text>
                    </View>
                  )}
                </View>
              </View>

              {/* Followed Topics */}
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Topics of Interest</Text>
                <Text style={styles.sectionSubtitle}>Tap to remove topics from your priority feed</Text>

                <View style={styles.chipRow}>
                  {interests.length > 0 ? (
                    interests.map((it) => (
                      <TouchableOpacity
                        key={it.id}
                        style={styles.topicChip}
                        onPress={() => handleRemoveInterest(it.topic_id)}
                      >
                        <Text style={styles.topicChipText}>#{it.topic_id}</Text>
                        <X size={12} color="#EF4444" />
                      </TouchableOpacity>
                    ))
                  ) : (
                    <Text style={styles.emptyNotice}>No followed topics yet</Text>
                  )}
                </View>
              </View>

              {/* Followed Companies */}
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Companies & Brands Followed</Text>
                <View style={styles.entityList}>
                  {allEntities.map((ent) => {
                    const isFollowed = followedEntities.some((fe) => fe.id === ent.id);
                    return (
                      <View key={ent.id} style={styles.entityRow}>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.entityName}>{ent.name}</Text>
                          <Text style={styles.entityType}>{ent.domain || 'Retail'}</Text>
                        </View>
                        <TouchableOpacity
                          style={[styles.followBtn, isFollowed && styles.followBtnActive]}
                          onPress={() => handleToggleFollow(ent.id, isFollowed)}
                        >
                          <Text style={[styles.followBtnText, isFollowed && styles.followBtnTextActive]}>
                            {isFollowed ? 'Following' : '+ Follow'}
                          </Text>
                        </TouchableOpacity>
                      </View>
                    );
                  })}
                </View>
              </View>

              {/* Feed Tuning Knobs */}
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Feed Tuning Controls</Text>

                {/* Behavioral switch */}
                <View style={styles.preferenceRow}>
                  <View style={{ flex: 1, paddingRight: 10 }}>
                    <Text style={styles.prefLabel}>Adaptive Learning</Text>
                    <Text style={styles.prefDesc}>
                      Refine feed relevance from read time and interactions
                    </Text>
                  </View>
                  <Switch
                    value={behaviouralEnabled}
                    onValueChange={setBehaviouralEnabled}
                    trackColor={{ false: '#334155', true: '#0284C7' }}
                    thumbColor={behaviouralEnabled ? '#38BDF8' : '#94A3B8'}
                  />
                </View>

                {/* Freshness Bias */}
                <View style={styles.stepperRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.prefLabel}>Freshness Priority</Text>
                    <Text style={styles.prefDesc}>
                      {freshnessBias > 1.0 ? 'High (favors breaking news)' : 'Balanced'}
                    </Text>
                  </View>
                  <View style={styles.stepperControls}>
                    <TouchableOpacity
                      style={styles.stepBtn}
                      onPress={() => setFreshnessBias(Math.max(0.5, freshnessBias - 0.25))}
                    >
                      <Text style={styles.stepBtnText}>-</Text>
                    </TouchableOpacity>
                    <Text style={styles.stepVal}>{freshnessBias.toFixed(2)}x</Text>
                    <TouchableOpacity
                      style={styles.stepBtn}
                      onPress={() => setFreshnessBias(Math.min(2.0, freshnessBias + 0.25))}
                    >
                      <Text style={styles.stepBtnText}>+</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Trend Priority */}
                <View style={styles.stepperRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.prefLabel}>Market Trends Alignment</Text>
                    <Text style={styles.prefDesc}>Weight towards emerging sector shifts</Text>
                  </View>
                  <View style={styles.stepperControls}>
                    <TouchableOpacity
                      style={styles.stepBtn}
                      onPress={() => setTrendBias(Math.max(0.5, trendBias - 0.25))}
                    >
                      <Text style={styles.stepBtnText}>-</Text>
                    </TouchableOpacity>
                    <Text style={styles.stepVal}>{trendBias.toFixed(2)}x</Text>
                    <TouchableOpacity
                      style={styles.stepBtn}
                      onPress={() => setTrendBias(Math.min(2.0, trendBias + 0.25))}
                    >
                      <Text style={styles.stepBtnText}>+</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Geographic Priority */}
                <View style={styles.stepperRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.prefLabel}>Geographic Proximity</Text>
                    <Text style={styles.prefDesc}>Weight towards local city/state developments</Text>
                  </View>
                  <View style={styles.stepperControls}>
                    <TouchableOpacity
                      style={styles.stepBtn}
                      onPress={() => setGeoBias(Math.max(0.5, geoBias - 0.25))}
                    >
                      <Text style={styles.stepBtnText}>-</Text>
                    </TouchableOpacity>
                    <Text style={styles.stepVal}>{geoBias.toFixed(2)}x</Text>
                    <TouchableOpacity
                      style={styles.stepBtn}
                      onPress={() => setGeoBias(Math.min(2.0, geoBias + 0.25))}
                    >
                      <Text style={styles.stepBtnText}>+</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </View>

              {/* Reset Section */}
              <View style={styles.resetSection}>
                <TouchableOpacity style={styles.resetBtn} onPress={handleResetPreferences}>
                  <RotateCcw size={15} color="#EF4444" />
                  <Text style={styles.resetBtnText}>Reset Learned Feedback</Text>
                </TouchableOpacity>
                <Text style={styles.resetDesc}>
                  Clears implicit behavioral learning scores without removing your domain profile.
                </Text>
              </View>
            </ScrollView>
          )}

          {/* Footer Save */}
          <View style={styles.footer}>
            <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.saveBtn}
              onPress={handleSavePreferences}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator size="small" color="#0F172A" />
              ) : (
                <Text style={styles.saveBtnText}>Apply Settings</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#0F172A',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '90%',
    minHeight: '75%',
    borderWidth: 1,
    borderColor: '#1E293B',
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerTitle: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: '700',
  },
  loadingBox: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  loadingText: {
    color: '#94A3B8',
    marginTop: 12,
    fontSize: 14,
  },
  content: {
    flex: 1,
  },
  contentInner: {
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  section: {
    marginBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
    paddingBottom: 16,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  sectionTitle: {
    color: '#F8FAFC',
    fontSize: 15,
    fontWeight: '700',
  },
  sectionSubtitle: {
    color: '#64748B',
    fontSize: 12,
    marginBottom: 10,
  },
  editProfileBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  editProfileBtnText: {
    color: '#38BDF8',
    fontSize: 12,
    fontWeight: '600',
  },
  profileCard: {
    backgroundColor: '#1E293B',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  profileDomain: {
    color: '#38BDF8',
    fontSize: 15,
    fontWeight: '800',
  },
  profileSubdomain: {
    color: '#94A3B8',
    fontSize: 12,
    marginTop: 2,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 6,
  },
  locationText: {
    color: '#CBD5E1',
    fontSize: 12,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  topicChip: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1,
    borderColor: '#334155',
  },
  topicChipText: {
    color: '#CBD5E1',
    fontSize: 12,
    fontWeight: '600',
  },
  emptyNotice: {
    color: '#64748B',
    fontSize: 12,
    fontStyle: 'italic',
  },
  entityList: {
    gap: 8,
  },
  entityRow: {
    backgroundColor: '#1E293B',
    borderRadius: 8,
    padding: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  entityName: {
    color: '#F8FAFC',
    fontSize: 13,
    fontWeight: '700',
  },
  entityType: {
    color: '#64748B',
    fontSize: 11,
    textTransform: 'uppercase',
  },
  followBtn: {
    backgroundColor: '#0F172A',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#475569',
  },
  followBtnActive: {
    backgroundColor: '#38BDF8',
    borderColor: '#38BDF8',
  },
  followBtnText: {
    color: '#94A3B8',
    fontSize: 11,
    fontWeight: '700',
  },
  followBtnTextActive: {
    color: '#0F172A',
  },
  preferenceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  prefLabel: {
    color: '#F8FAFC',
    fontSize: 13,
    fontWeight: '600',
  },
  prefDesc: {
    color: '#64748B',
    fontSize: 11,
    marginTop: 2,
  },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
  },
  stepperControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#1E293B',
    borderRadius: 8,
    padding: 4,
  },
  stepBtn: {
    width: 28,
    height: 28,
    backgroundColor: '#334155',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBtnText: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: '700',
  },
  stepVal: {
    color: '#38BDF8',
    fontSize: 13,
    fontWeight: '700',
    minWidth: 42,
    textAlign: 'center',
  },
  resetSection: {
    marginTop: 10,
    alignItems: 'center',
  },
  resetBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  resetBtnText: {
    color: '#EF4444',
    fontSize: 13,
    fontWeight: '600',
  },
  resetDesc: {
    color: '#64748B',
    fontSize: 11,
    textAlign: 'center',
    marginTop: 6,
    paddingHorizontal: 20,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
  },
  cancelBtn: {
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  cancelBtnText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '600',
  },
  saveBtn: {
    backgroundColor: '#38BDF8',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  saveBtnText: {
    color: '#0F172A',
    fontSize: 14,
    fontWeight: '700',
  },
});
