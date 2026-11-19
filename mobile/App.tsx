import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  StyleSheet,
  View,
  FlatList,
  ActivityIndicator,
  Text,
  RefreshControl,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { Header } from './src/components/Header';
import { ArticleCard } from './src/components/ArticleCard';
import { ArticleModal } from './src/components/ArticleModal';
import { TrendCard } from './src/components/TrendCard';
import { TrendModal } from './src/components/TrendModal';
import { OnboardingModal } from './src/components/OnboardingModal';
import { PersonalizationSettingsModal } from './src/components/PersonalizationSettingsModal';
import {
  fetchForYouFeed,
  fetchFollowingFeed,
  fetchPersonalizedTrends,
  fetchLatestFeed,
  fetchUserProfile,
  triggerManualRefresh,
  triggerTrendRebuild,
  getApiBaseUrl,
} from './src/api/client';
import { Article, TrendSummary, PersonalizedFeedItem } from './src/types';
import {
  AlertCircle,
  CheckCircle2,
  RotateCcw,
  Sparkles,
  Flame,
  Newspaper,
  Compass,
  BookmarkCheck,
  SlidersHorizontal,
  MapPin,
} from 'lucide-react-native';

type TabType = 'for_you' | 'trends' | 'following' | 'latest';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('for_you');
  const [items, setItems] = useState<PersonalizedFeedItem[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [userProfile, setUserProfile] = useState<any>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState<boolean>(true);

  // Modals state
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [selectedTrend, setSelectedTrend] = useState<TrendSummary | null>(null);
  const [onboardingVisible, setOnboardingVisible] = useState<boolean>(false);
  const [settingsVisible, setSettingsVisible] = useState<boolean>(false);

  const [error, setError] = useState<string | null>(null);

  // Toast notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<'info' | 'success'>('info');
  const toastAnim = useRef(new Animated.Value(-60)).current;

  const showToast = (message: string, type: 'info' | 'success' = 'info') => {
    setToastMessage(message);
    setToastType(type);
    Animated.sequence([
      Animated.timing(toastAnim, {
        toValue: 12,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.delay(2800),
      Animated.timing(toastAnim, {
        toValue: -60,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setToastMessage(null);
    });
  };

  // Initial Profile Check
  const checkUserProfile = async () => {
    try {
      const prof = await fetchUserProfile();
      setUserProfile(prof);
      if (!prof || !prof.business_domain) {
        // Open onboarding for new user
        setOnboardingVisible(true);
      }
    } catch (e) {
      console.warn('Profile fetch notice:', e);
    }
  };

  useEffect(() => {
    checkUserProfile();
  }, []);

  const loadData = useCallback(
    async (tab: TabType, isRefresh: boolean = false) => {
      try {
        setError(null);
        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        if (tab === 'for_you') {
          const res = await fetchForYouFeed(undefined, 20);
          setItems(res.items || []);
          setNextCursor(res.next_cursor);
          setHasMore(res.has_more ?? false);
          if (isRefresh) {
            showToast(`✨ Personalized ${res.items?.length || 0} stories & trends`, 'success');
          }
        } else if (tab === 'following') {
          const res = await fetchFollowingFeed(undefined, 20);
          setItems(res.items || []);
          setNextCursor(res.next_cursor);
          setHasMore(res.has_more ?? false);
          if (isRefresh) {
            showToast(`✓ Updated followed topics and brands`, 'info');
          }
        } else if (tab === 'trends') {
          const trList = await fetchPersonalizedTrends(20);
          setTrends(trList);
          if (isRefresh) {
            showToast(`🔥 Ranked ${trList.length} market trends for your domain`, 'success');
          }
        } else if (tab === 'latest') {
          const res = await fetchLatestFeed(undefined, 20);
          setItems(res.items || []);
          setNextCursor(res.next_cursor);
          setHasMore(res.has_more ?? false);
          if (isRefresh) {
            showToast(`✓ Latest chronological feed loaded`, 'info');
          }
        }
      } catch (err: any) {
        console.error('Error loading feed data:', err);
        const baseUrl = getApiBaseUrl();
        setError(
          err.response?.data?.detail ||
            `Could not connect to Vyapar API at ${baseUrl}: ${err.message || 'Network Error'}`
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    []
  );

  useEffect(() => {
    loadData(activeTab);
  }, [activeTab]);

  const handlePullToRefresh = async () => {
    try {
      setRefreshing(true);
      if (activeTab === 'trends') {
        await triggerTrendRebuild(userProfile?.business_domain);
      } else {
        await triggerManualRefresh(userProfile?.business_domain);
      }
      await new Promise((res) => setTimeout(res, 800));
    } catch (e) {
      console.warn('Manual refresh notice:', e);
    }
    await loadData(activeTab, true);
  };

  const handleLoadMore = async () => {
    if (activeTab === 'trends' || loadingMore || !hasMore || !nextCursor) return;

    try {
      setLoadingMore(true);
      let res: any;
      if (activeTab === 'for_you') {
        res = await fetchForYouFeed(nextCursor, 15);
      } else if (activeTab === 'following') {
        res = await fetchFollowingFeed(nextCursor, 15);
      } else if (activeTab === 'latest') {
        res = await fetchLatestFeed(nextCursor, 15);
      }

      if (res && res.items) {
        setItems((prev) => {
          const existingKeys = new Set(prev.map((it) => `${it.type}_${it.id}`));
          const uniqueNewItems = res.items.filter(
            (it: any) => !existingKeys.has(`${it.type}_${it.id}`)
          );
          return [...prev, ...uniqueNewItems];
        });
        setNextCursor(res.next_cursor);
        setHasMore(res.has_more ?? false);
      }
    } catch (err) {
      console.error('Error loading more items:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleDismissArticle = (articleId: string) => {
    setItems((prev) => prev.filter((it) => it.id !== articleId));
    showToast('Feed tuned • Item hidden', 'info');
  };

  const renderFooter = () => {
    if (!loadingMore) return null;
    return (
      <View style={styles.footerLoader}>
        <ActivityIndicator size="small" color="#38BDF8" />
        <Text style={styles.footerText}>Loading relevant intelligence...</Text>
      </View>
    );
  };

  const renderEmptyState = () => {
    if (loading) return null;
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyTitle}>
          {activeTab === 'following'
            ? 'No Followed Stories Yet'
            : activeTab === 'trends'
            ? 'No Trends Detected'
            : 'Feed is Up to Date'}
        </Text>
        <Text style={styles.emptySubtitle}>
          {activeTab === 'following'
            ? 'Follow companies and topics in Settings to curate an exclusive intelligence feed.'
            : activeTab === 'trends'
            ? 'The Trend Engine detects market movements across sources. Pull down to trigger detection.'
            : 'Pull down to refresh or tune your business preferences in Settings.'}
        </Text>
        <TouchableOpacity
          style={styles.retryButton}
          onPress={() => {
            if (activeTab === 'following') {
              setSettingsVisible(true);
            } else {
              handlePullToRefresh();
            }
          }}
        >
          <RotateCcw size={15} color="#0F172A" />
          <Text style={styles.retryButtonText}>
            {activeTab === 'following' ? 'Manage Followed Topics' : 'Refresh Feed'}
          </Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <Animated.View
          style={[
            styles.toastBanner,
            toastType === 'success' ? styles.toastSuccess : styles.toastInfo,
            { transform: [{ translateY: toastAnim }] },
          ]}
        >
          {toastType === 'success' ? (
            <Sparkles size={14} color="#34D399" />
          ) : (
            <CheckCircle2 size={14} color="#38BDF8" />
          )}
          <Text style={styles.toastText}>{toastMessage}</Text>
        </Animated.View>
      )}

      {/* Main App Header */}
      <Header
        onRefreshPress={handlePullToRefresh}
        onSettingsPress={() => setSettingsVisible(true)}
        isRefreshing={refreshing}
        totalArticles={activeTab === 'trends' ? trends.length : items.length}
        userDomain={userProfile?.business_domain}
      />

      {/* Active Market Profile Pill Bar */}
      <View style={styles.profileBar}>
        <TouchableOpacity
          style={styles.profileInfoBtn}
          onPress={() => setSettingsVisible(true)}
          activeOpacity={0.8}
        >
          <View style={styles.profileDot} />
          <Text style={styles.profileDomainText}>
            {userProfile?.business_domain
              ? userProfile.business_domain.toUpperCase()
              : 'SETUP PROFILE'}
          </Text>
          {userProfile?.city && (
            <View style={styles.profileCityTag}>
              <MapPin size={10} color="#94A3B8" />
              <Text style={styles.profileCityText}>{userProfile.city}</Text>
            </View>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.tunePill}
          onPress={() => setSettingsVisible(true)}
          activeOpacity={0.8}
        >
          <SlidersHorizontal size={12} color="#38BDF8" />
          <Text style={styles.tunePillText}>Tune Feed</Text>
        </TouchableOpacity>
      </View>

      {/* 4 Navigation Tabs */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tabButton, activeTab === 'for_you' && styles.tabButtonActiveForYou]}
          onPress={() => setActiveTab('for_you')}
        >
          <Sparkles
            size={13}
            color={activeTab === 'for_you' ? '#38BDF8' : '#94A3B8'}
          />
          <Text
            style={[styles.tabText, activeTab === 'for_you' && styles.tabTextActiveForYou]}
          >
            For You
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabButton, activeTab === 'trends' && styles.tabButtonActiveTrends]}
          onPress={() => setActiveTab('trends')}
        >
          <Flame
            size={13}
            color={activeTab === 'trends' ? '#F97316' : '#94A3B8'}
          />
          <Text
            style={[styles.tabText, activeTab === 'trends' && styles.tabTextActiveTrends]}
          >
            Trends
          </Text>
          {trends.length > 0 && (
            <View style={styles.trendCountBadge}>
              <Text style={styles.trendCountText}>{trends.length}</Text>
            </View>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabButton, activeTab === 'following' && styles.tabButtonActiveFollowing]}
          onPress={() => setActiveTab('following')}
        >
          <BookmarkCheck
            size={13}
            color={activeTab === 'following' ? '#34D399' : '#94A3B8'}
          />
          <Text
            style={[styles.tabText, activeTab === 'following' && styles.tabTextActiveFollowing]}
          >
            Following
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabButton, activeTab === 'latest' && styles.tabButtonActiveLatest]}
          onPress={() => setActiveTab('latest')}
        >
          <Compass
            size={13}
            color={activeTab === 'latest' ? '#A78BFA' : '#94A3B8'}
          />
          <Text
            style={[styles.tabText, activeTab === 'latest' && styles.tabTextActiveLatest]}
          >
            Latest
          </Text>
        </TouchableOpacity>
      </View>

      {/* Error Alert Banner */}
      {error && (
        <View style={styles.errorBanner}>
          <AlertCircle size={16} color="#EF4444" />
          <Text style={styles.errorText} numberOfLines={2}>
            {error}
          </Text>
        </View>
      )}

      {/* Main Content Area */}
      {loading ? (
        <View style={styles.centerLoader}>
          <ActivityIndicator size="large" color="#38BDF8" />
          <Text style={styles.loadingText}>
            {activeTab === 'for_you'
              ? 'Computing Personalized Relevance Scores...'
              : activeTab === 'trends'
              ? 'Ranking Market Trends by Business Impact...'
              : activeTab === 'following'
              ? 'Filtering Followed Companies & Topics...'
              : 'Fetching Latest Market Wire...'}
          </Text>
        </View>
      ) : activeTab === 'trends' ? (
        <FlatList
          data={trends}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TrendCard trend={item} onPress={() => setSelectedTrend(item)} />
          )}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handlePullToRefresh}
              tintColor="#F97316"
              colors={['#F97316']}
            />
          }
          ListEmptyComponent={renderEmptyState}
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item, index) => `${item.type}_${item.id}_${index}`}
          renderItem={({ item }) => {
            if (item.type === 'trend') {
              return (
                <TrendCard
                  trend={item as any}
                  onPress={() => setSelectedTrend(item as any)}
                />
              );
            }
            return (
              <ArticleCard
                article={item}
                onPress={() => setSelectedArticle(item as any)}
                onDismiss={handleDismissArticle}
              />
            );
          }}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handlePullToRefresh}
              tintColor="#38BDF8"
              colors={['#38BDF8']}
            />
          }
          onEndReached={handleLoadMore}
          onEndReachedThreshold={0.4}
          ListFooterComponent={renderFooter}
          ListEmptyComponent={renderEmptyState}
        />
      )}

      {/* Article Detail Modal */}
      <ArticleModal
        article={selectedArticle}
        visible={selectedArticle !== null}
        onClose={() => setSelectedArticle(null)}
      />

      {/* Trend Detail Modal */}
      <TrendModal
        trendSummary={selectedTrend}
        visible={selectedTrend !== null}
        onClose={() => setSelectedTrend(null)}
      />

      {/* Phase 4 Onboarding Modal */}
      <OnboardingModal
        visible={onboardingVisible}
        onClose={() => setOnboardingVisible(false)}
        onComplete={() => {
          setOnboardingVisible(false);
          checkUserProfile();
          loadData('for_you', true);
        }}
      />

      {/* Phase 4 Personalization Settings Modal */}
      <PersonalizationSettingsModal
        visible={settingsVisible}
        onClose={() => setSettingsVisible(false)}
        onPreferencesUpdated={() => {
          checkUserProfile();
          loadData(activeTab, true);
        }}
        onOpenOnboarding={() => setOnboardingVisible(true)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0F19',
  },
  profileBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 7,
    backgroundColor: '#111827',
    borderBottomWidth: 1,
    borderBottomColor: '#1F2937',
  },
  profileInfoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  profileDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#38BDF8',
  },
  profileDomainText: {
    color: '#38BDF8',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  profileCityTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: 'rgba(51, 65, 85, 0.5)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: 4,
  },
  profileCityText: {
    color: '#CBD5E1',
    fontSize: 10,
    fontWeight: '600',
  },
  tunePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.3)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  tunePillText: {
    color: '#38BDF8',
    fontSize: 11,
    fontWeight: '700',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#111827',
    marginHorizontal: 12,
    marginTop: 6,
    marginBottom: 4,
    padding: 3,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1F2937',
  },
  tabButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 7,
    borderRadius: 7,
  },
  tabButtonActiveForYou: {
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.35)',
  },
  tabButtonActiveTrends: {
    backgroundColor: 'rgba(249, 115, 22, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(249, 115, 22, 0.35)',
  },
  tabButtonActiveFollowing: {
    backgroundColor: 'rgba(52, 211, 153, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(52, 211, 153, 0.35)',
  },
  tabButtonActiveLatest: {
    backgroundColor: 'rgba(167, 139, 250, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(167, 139, 250, 0.35)',
  },
  tabText: {
    color: '#94A3B8',
    fontSize: 11.5,
    fontWeight: '600',
  },
  tabTextActiveForYou: {
    color: '#38BDF8',
    fontWeight: '700',
  },
  tabTextActiveTrends: {
    color: '#F97316',
    fontWeight: '700',
  },
  tabTextActiveFollowing: {
    color: '#34D399',
    fontWeight: '700',
  },
  tabTextActiveLatest: {
    color: '#A78BFA',
    fontWeight: '700',
  },
  trendCountBadge: {
    backgroundColor: '#F97316',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 8,
    marginLeft: 1,
  },
  trendCountText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: '800',
  },
  listContent: {
    paddingVertical: 8,
  },
  toastBanner: {
    position: 'absolute',
    top: 50,
    left: 20,
    right: 20,
    zIndex: 9999,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 6,
    elevation: 8,
  },
  toastSuccess: {
    backgroundColor: '#064E3B',
    borderWidth: 1,
    borderColor: '#059669',
  },
  toastInfo: {
    backgroundColor: '#0C4A6E',
    borderWidth: 1,
    borderColor: '#0284C7',
  },
  toastText: {
    color: '#F8FAFC',
    fontSize: 12.5,
    fontWeight: '600',
    flex: 1,
  },
  centerLoader: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  loadingText: {
    color: '#94A3B8',
    fontSize: 13,
    marginTop: 12,
    textAlign: 'center',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingVertical: 48,
  },
  emptyTitle: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
  },
  emptySubtitle: {
    color: '#64748B',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 16,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#38BDF8',
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#0F172A',
    fontWeight: '700',
    fontSize: 13,
  },
  footerLoader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
  },
  footerText: {
    color: '#64748B',
    fontSize: 12,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderColor: 'rgba(239, 68, 68, 0.35)',
    borderWidth: 1,
    borderRadius: 8,
    marginHorizontal: 12,
    marginVertical: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  errorText: {
    color: '#FCA5A5',
    fontSize: 12,
    flex: 1,
  },
});
