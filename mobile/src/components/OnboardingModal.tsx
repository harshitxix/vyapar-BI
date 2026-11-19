import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import {
  X,
  Check,
  ChevronRight,
  ChevronLeft,
  Store,
  MapPin,
  Tag,
  Building,
  Sparkles,
} from 'lucide-react-native';
import {
  fetchTaxonomyDomains,
  fetchEntities,
  saveUserProfile,
  addUserInterest,
  followEntity,
} from '../api/client';

interface OnboardingModalProps {
  visible: boolean;
  onClose: () => void;
  onComplete: () => void;
}

const COMMON_CITIES = [
  { city: 'Gurugram', state: 'Haryana' },
  { city: 'Mumbai', state: 'Maharashtra' },
  { city: 'Bengaluru', state: 'Karnataka' },
  { city: 'Delhi', state: 'Delhi' },
  { city: 'Hyderabad', state: 'Telangana' },
  { city: 'Pune', state: 'Maharashtra' },
  { city: 'Ahmedabad', state: 'Gujarat' },
  { city: 'Jaipur', state: 'Rajasthan' },
];

export const OnboardingModal: React.FC<OnboardingModalProps> = ({
  visible,
  onClose,
  onComplete,
}) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Taxonomy & Entities state
  const [domains, setDomains] = useState<any[]>([]);
  const [availableEntities, setAvailableEntities] = useState<any[]>([]);

  // User selections
  const [selectedDomain, setSelectedDomain] = useState<string>('grocery');
  const [selectedSubdomain, setSelectedSubdomain] = useState<string>('');
  const [businessName, setBusinessName] = useState<string>('');
  const [city, setCity] = useState<string>('Gurugram');
  const [state, setState] = useState<string>('Haryana');
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [customTopic, setCustomTopic] = useState<string>('');
  const [selectedEntityIds, setSelectedEntityIds] = useState<string[]>([]);

  useEffect(() => {
    if (visible) {
      loadTaxonomyAndEntities();
    }
  }, [visible]);

  const loadTaxonomyAndEntities = async () => {
    try {
      setLoading(true);
      const [domList, entList] = await Promise.all([
        fetchTaxonomyDomains(),
        fetchEntities(),
      ]);
      setDomains(domList);
      setAvailableEntities(entList);

      // Default topics for grocery
      const groceryDomain = domList.find((d: any) => d.id === 'grocery');
      if (groceryDomain && groceryDomain.suggested_topics) {
        setSelectedTopics(groceryDomain.suggested_topics.slice(0, 3));
      }
    } catch (err) {
      console.error('Failed to load onboarding taxonomy:', err);
    } finally {
      setLoading(false);
    }
  };

  const currentDomainData = domains.find((d) => d.id === selectedDomain);

  const handleDomainSelect = (domainId: string) => {
    setSelectedDomain(domainId);
    setSelectedSubdomain('');
    const dData = domains.find((d) => d.id === domainId);
    if (dData && dData.suggested_topics) {
      setSelectedTopics(dData.suggested_topics.slice(0, 3));
    }
  };

  const toggleTopic = (topic: string) => {
    if (selectedTopics.includes(topic)) {
      setSelectedTopics(selectedTopics.filter((t) => t !== topic));
    } else {
      setSelectedTopics([...selectedTopics, topic]);
    }
  };

  const handleAddCustomTopic = () => {
    if (customTopic.trim() && !selectedTopics.includes(customTopic.trim())) {
      setSelectedTopics([...selectedTopics, customTopic.trim()]);
      setCustomTopic('');
    }
  };

  const toggleEntity = (entityId: string) => {
    if (selectedEntityIds.includes(entityId)) {
      setSelectedEntityIds(selectedEntityIds.filter((id) => id !== entityId));
    } else {
      setSelectedEntityIds([...selectedEntityIds, entityId]);
    }
  };

  const handleFinishOnboarding = async () => {
    try {
      setSubmitting(true);
      // 1. Save Market Profile
      await saveUserProfile({
        business_name: businessName.trim() || undefined,
        business_domain: selectedDomain,
        business_subdomain: selectedSubdomain || undefined,
        country: 'India',
        state: state.trim() || undefined,
        city: city.trim() || undefined,
        preferred_language: 'English',
      });

      // 2. Save Topics
      for (const topic of selectedTopics) {
        await addUserInterest(topic, 1.0);
      }

      // 3. Follow Entities
      for (const entId of selectedEntityIds) {
        await followEntity(entId);
      }

      onComplete();
    } catch (err) {
      console.error('Failed to save onboarding selections:', err);
      onComplete();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Sparkles size={20} color="#38BDF8" />
              <Text style={styles.headerTitle}>Personalize Your Market Feed</Text>
            </View>
            <TouchableOpacity onPress={onClose} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <X size={20} color="#94A3B8" />
            </TouchableOpacity>
          </View>

          {/* Progress Indicator */}
          <View style={styles.progressBarRow}>
            {[1, 2, 3, 4].map((stepIdx) => (
              <View
                key={stepIdx}
                style={[
                  styles.progressSegment,
                  step >= stepIdx ? styles.progressActive : styles.progressInactive,
                ]}
              />
            ))}
          </View>

          {loading ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color="#38BDF8" />
              <Text style={styles.loadingText}>Loading business taxonomy...</Text>
            </View>
          ) : (
            <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
              {/* Step 1: Business Domain & Subdomain */}
              {step === 1 && (
                <View>
                  <Text style={styles.stepTitle}>Select Your Business Domain</Text>
                  <Text style={styles.stepSubtitle}>
                    Which industry context do you want your feed to monitor?
                  </Text>

                  <View style={styles.domainGrid}>
                    {domains.map((d) => {
                      const isSelected = selectedDomain === d.id;
                      return (
                        <TouchableOpacity
                          key={d.id}
                          style={[styles.domainCard, isSelected && styles.domainCardActive]}
                          onPress={() => handleDomainSelect(d.id)}
                        >
                          <Text style={[styles.domainName, isSelected && styles.domainNameActive]}>
                            {d.display_name}
                          </Text>
                          {isSelected && <Check size={16} color="#38BDF8" />}
                        </TouchableOpacity>
                      );
                    })}
                  </View>

                  {/* Subdomain selector */}
                  {currentDomainData?.subdomains && currentDomainData.subdomains.length > 0 && (
                    <View style={styles.subdomainSection}>
                      <Text style={styles.sectionLabel}>Select Specific Subdomain (Optional)</Text>
                      <View style={styles.chipRow}>
                        {currentDomainData.subdomains.map((sub: any) => {
                          const isSubSelected = selectedSubdomain === sub.id;
                          return (
                            <TouchableOpacity
                              key={sub.id}
                              style={[styles.chip, isSubSelected && styles.chipActive]}
                              onPress={() =>
                                setSelectedSubdomain(isSubSelected ? '' : sub.id)
                              }
                            >
                              <Text style={[styles.chipText, isSubSelected && styles.chipTextActive]}>
                                {sub.name}
                              </Text>
                            </TouchableOpacity>
                          );
                        })}
                      </View>
                    </View>
                  )}
                </View>
              )}

              {/* Step 2: Location & Business Info */}
              {step === 2 && (
                <View>
                  <Text style={styles.stepTitle}>Your Geographical Market</Text>
                  <Text style={styles.stepSubtitle}>
                    Prioritize news, mandi prices, and local retail developments near you.
                  </Text>

                  <Text style={styles.sectionLabel}>Quick Pick City</Text>
                  <View style={styles.chipRow}>
                    {COMMON_CITIES.map((c) => {
                      const isCitySelected = city === c.city;
                      return (
                        <TouchableOpacity
                          key={c.city}
                          style={[styles.chip, isCitySelected && styles.chipActive]}
                          onPress={() => {
                            setCity(c.city);
                            setState(c.state);
                          }}
                        >
                          <Text style={[styles.chipText, isCitySelected && styles.chipTextActive]}>
                            {c.city}
                          </Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.inputLabel}>City</Text>
                    <TextInput
                      style={styles.textInput}
                      value={city}
                      onChangeText={setCity}
                      placeholder="e.g. Gurugram, Jaipur"
                      placeholderTextColor="#64748B"
                    />
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.inputLabel}>State</Text>
                    <TextInput
                      style={styles.textInput}
                      value={state}
                      onChangeText={setState}
                      placeholder="e.g. Haryana, Rajasthan"
                      placeholderTextColor="#64748B"
                    />
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.inputLabel}>Business Name (Optional)</Text>
                    <TextInput
                      style={styles.textInput}
                      value={businessName}
                      onChangeText={setBusinessName}
                      placeholder="e.g. Shri Krishna Provision Store"
                      placeholderTextColor="#64748B"
                    />
                  </View>
                </View>
              )}

              {/* Step 3: Topics of Interest */}
              {step === 3 && (
                <View>
                  <Text style={styles.stepTitle}>Topics You Care About</Text>
                  <Text style={styles.stepSubtitle}>
                    Select topics related to {currentDomainData?.display_name || selectedDomain}.
                  </Text>

                  <View style={styles.chipRow}>
                    {currentDomainData?.suggested_topics?.map((topic: string) => {
                      const isTopicSelected = selectedTopics.includes(topic);
                      return (
                        <TouchableOpacity
                          key={topic}
                          style={[styles.chip, isTopicSelected && styles.chipActive]}
                          onPress={() => toggleTopic(topic)}
                        >
                          <Text style={[styles.chipText, isTopicSelected && styles.chipTextActive]}>
                            #{topic}
                          </Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>

                  <View style={styles.customTopicRow}>
                    <TextInput
                      style={[styles.textInput, { flex: 1 }]}
                      value={customTopic}
                      onChangeText={setCustomTopic}
                      placeholder="Add custom topic..."
                      placeholderTextColor="#64748B"
                      onSubmitEditing={handleAddCustomTopic}
                    />
                    <TouchableOpacity
                      style={styles.addTopicBtn}
                      onPress={handleAddCustomTopic}
                    >
                      <Text style={styles.addTopicBtnText}>Add</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}

              {/* Step 4: Follow Companies & Brands */}
              {step === 4 && (
                <View>
                  <Text style={styles.stepTitle}>Follow Key Companies & Brands</Text>
                  <Text style={styles.stepSubtitle}>
                    Get highlighted market moves and announcements for companies you track.
                  </Text>

                  <View style={styles.entityList}>
                    {availableEntities.map((ent) => {
                      const isFollowed = selectedEntityIds.includes(ent.id);
                      return (
                        <TouchableOpacity
                          key={ent.id}
                          style={[styles.entityItem, isFollowed && styles.entityItemActive]}
                          onPress={() => toggleEntity(ent.id)}
                        >
                          <View style={styles.entityInfo}>
                            <Text style={styles.entityName}>{ent.name}</Text>
                            <Text style={styles.entityType}>
                              {ent.domain?.toUpperCase() || 'RETAIL'} • {ent.entity_type}
                            </Text>
                          </View>
                          <View
                            style={[
                              styles.followBtn,
                              isFollowed && styles.followBtnActive,
                            ]}
                          >
                            <Text
                              style={[
                                styles.followBtnText,
                                isFollowed && styles.followBtnTextActive,
                              ]}
                            >
                              {isFollowed ? 'Following' : '+ Follow'}
                            </Text>
                          </View>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </View>
              )}
            </ScrollView>
          )}

          {/* Footer Controls */}
          <View style={styles.footer}>
            {step > 1 ? (
              <TouchableOpacity
                style={styles.backBtn}
                onPress={() => setStep(step - 1)}
                disabled={submitting}
              >
                <ChevronLeft size={18} color="#94A3B8" />
                <Text style={styles.backBtnText}>Back</Text>
              </TouchableOpacity>
            ) : (
              <View style={{ width: 80 }} />
            )}

            {step < 4 ? (
              <TouchableOpacity
                style={styles.nextBtn}
                onPress={() => setStep(step + 1)}
              >
                <Text style={styles.nextBtnText}>Continue</Text>
                <ChevronRight size={18} color="#0F172A" />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                style={styles.finishBtn}
                onPress={handleFinishOnboarding}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator size="small" color="#0F172A" />
                ) : (
                  <>
                    <Text style={styles.finishBtnText}>Personalize Feed</Text>
                    <Check size={18} color="#0F172A" />
                  </>
                )}
              </TouchableOpacity>
            )}
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
  progressBarRow: {
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  progressSegment: {
    flex: 1,
    height: 4,
    borderRadius: 2,
  },
  progressActive: {
    backgroundColor: '#38BDF8',
  },
  progressInactive: {
    backgroundColor: '#1E293B',
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
  stepTitle: {
    color: '#F8FAFC',
    fontSize: 19,
    fontWeight: '800',
    marginBottom: 6,
  },
  stepSubtitle: {
    color: '#94A3B8',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 18,
  },
  domainGrid: {
    gap: 8,
  },
  domainCard: {
    backgroundColor: '#1E293B',
    borderRadius: 10,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: '#334155',
  },
  domainCardActive: {
    borderColor: '#38BDF8',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
  },
  domainName: {
    color: '#CBD5E1',
    fontSize: 14,
    fontWeight: '600',
  },
  domainNameActive: {
    color: '#38BDF8',
    fontWeight: '700',
  },
  subdomainSection: {
    marginTop: 18,
  },
  sectionLabel: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  chip: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  chipActive: {
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    borderColor: '#38BDF8',
  },
  chipText: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '600',
  },
  chipTextActive: {
    color: '#38BDF8',
  },
  inputGroup: {
    marginBottom: 14,
  },
  inputLabel: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
  },
  textInput: {
    backgroundColor: '#1E293B',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    color: '#F8FAFC',
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  customTopicRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  addTopicBtn: {
    backgroundColor: '#38BDF8',
    borderRadius: 8,
    paddingHorizontal: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  addTopicBtnText: {
    color: '#0F172A',
    fontWeight: '700',
    fontSize: 13,
  },
  entityList: {
    gap: 8,
  },
  entityItem: {
    backgroundColor: '#1E293B',
    borderRadius: 10,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: '#334155',
  },
  entityItemActive: {
    borderColor: '#38BDF8',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
  },
  entityInfo: {
    flex: 1,
  },
  entityName: {
    color: '#F8FAFC',
    fontSize: 14,
    fontWeight: '700',
  },
  entityType: {
    color: '#64748B',
    fontSize: 11,
    marginTop: 2,
  },
  followBtn: {
    backgroundColor: '#0F172A',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#475569',
  },
  followBtnActive: {
    backgroundColor: '#38BDF8',
    borderColor: '#38BDF8',
  },
  followBtnText: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '700',
  },
  followBtnTextActive: {
    color: '#0F172A',
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
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  backBtnText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '600',
  },
  nextBtn: {
    backgroundColor: '#38BDF8',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  nextBtnText: {
    color: '#0F172A',
    fontSize: 14,
    fontWeight: '700',
  },
  finishBtn: {
    backgroundColor: '#34D399',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  finishBtnText: {
    color: '#0F172A',
    fontSize: 14,
    fontWeight: '700',
  },
});
