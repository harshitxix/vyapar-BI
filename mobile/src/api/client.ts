import axios from 'axios';
import { Platform, NativeModules } from 'react-native';
import Constants from 'expo-constants';
import { FeedResponse, SourceHealth, Article } from '../types';

export const getApiBaseUrl = (): string => {
  if (Platform.OS === 'web') {
    return 'http://localhost:8000';
  }

  // In Expo Go, the app connects to the Metro bundler server.
  // We reverse-proxy /feed, /trends, /sources, /ingestion, /admin in metro.config.js
  // directly to http://127.0.0.1:8000.
  // Routing API requests through Metro's host works everywhere:
  // - On LAN (port 8081 is open in Windows Firewall; port 8000 is blocked on Private profile)
  // - On --tunnel (the Metro tunnel relays both JavaScript bundles and API requests)

  // 1. Try hostUri from Expo Constants
  const hostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as any).expoGoConfig?.debuggerHost ||
    (Constants as any).manifest?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoClient?.hostUri;

  if (hostUri) {
    const isHttps =
      hostUri.includes('.on.expo.app') ||
      hostUri.includes('exp.direct') ||
      hostUri.includes('ngrok.io');
    const protocol = isHttps ? 'https://' : 'http://';
    const cleanHost = hostUri.replace(/\/$/, '');
    return `${protocol}${cleanHost}`;
  }

  // 2. Try NativeModules.SourceCode.scriptURL
  const scriptURL = NativeModules.SourceCode?.scriptURL;
  if (scriptURL) {
    const match = scriptURL.match(/^https?:\/\/[^\/]+/);
    if (match) {
      return match[0];
    }
  }

  // 3. Fallback: Android emulator uses 10.0.2.2 to reach host machine; physical device uses LAN IP
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8081';
  }
  return 'http://192.168.31.86:8081';
};

export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl();
  console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  return config;
});

export const fetchFeed = async (
  domain?: string,
  cursor?: string,
  limit: number = 15
): Promise<FeedResponse> => {
  const params: Record<string, any> = { limit };
  if (domain && domain !== 'all') {
    params.domain = domain;
  }
  if (cursor) {
    params.cursor = cursor;
  }

  const response = await apiClient.get<FeedResponse>('/feed', { params });
  return response.data;
};

export const triggerManualRefresh = async (domain?: string): Promise<any> => {
  const payload: Record<string, any> = {};
  if (domain && domain !== 'all') {
    payload.domain = domain;
  }
  const response = await apiClient.post('/ingestion/refresh', payload);
  return response.data;
};

export const fetchSourcesStatus = async (): Promise<{
  total_sources: number;
  healthy: number;
  degraded: number;
  failed: number;
  sources: SourceHealth[];
}> => {
  const response = await apiClient.get('/sources/status');
  return response.data;
};

export const fetchTrends = async (
  domain?: string,
  status?: string,
  limit: number = 20
): Promise<any[]> => {
  const params: Record<string, any> = { limit };
  if (domain && domain !== 'all') {
    params.domain = domain;
  }
  if (status && status !== 'all') {
    params.status = status;
  }
  const response = await apiClient.get('/trends', { params });
  return response.data;
};

export const fetchTrendDetail = async (trendId: string): Promise<any> => {
  const response = await apiClient.get(`/trends/${trendId}`);
  return response.data;
};

export const fetchTrendTimeline = async (trendId: string): Promise<any[]> => {
  const response = await apiClient.get(`/trends/${trendId}/timeline`);
  return response.data;
};

export const triggerTrendRebuild = async (domain?: string): Promise<any> => {
  const payload: Record<string, any> = {
    domain: domain && domain !== 'all' ? domain : undefined,
    region: 'india',
    window_days: 14,
  };
  const response = await apiClient.post('/admin/trends/rebuild', payload);
  return response.data;
};

// ==========================================
// Phase 4: Personalization Engine API Calls
// ==========================================

export const fetchForYouFeed = async (
  cursor?: string,
  limit: number = 20
): Promise<any> => {
  const params: Record<string, any> = { limit };
  if (cursor) {
    params.cursor = cursor;
  }
  const response = await apiClient.get('/feed/for-you', { params });
  return response.data;
};

export const fetchFollowingFeed = async (
  cursor?: string,
  limit: number = 20
): Promise<any> => {
  const params: Record<string, any> = { limit };
  if (cursor) {
    params.cursor = cursor;
  }
  const response = await apiClient.get('/feed/following', { params });
  return response.data;
};

export const fetchPersonalizedTrends = async (limit: number = 20): Promise<any[]> => {
  const response = await apiClient.get('/trends/for-you', { params: { limit } });
  return response.data?.items || [];
};

export const fetchLatestFeed = async (
  cursor?: string,
  limit: number = 20
): Promise<any> => {
  const params: Record<string, any> = { limit };
  if (cursor) {
    params.cursor = cursor;
  }
  const response = await apiClient.get('/feed/latest', { params });
  return response.data;
};

export const fetchTaxonomyDomains = async (): Promise<any[]> => {
  const response = await apiClient.get('/taxonomy/domains');
  return response.data?.domains || [];
};

export const fetchEntities = async (domain?: string): Promise<any[]> => {
  const params: Record<string, any> = {};
  if (domain && domain !== 'all') {
    params.domain = domain;
  }
  const response = await apiClient.get('/entities', { params });
  return response.data || [];
};

export const fetchUserProfile = async (): Promise<any> => {
  const response = await apiClient.get('/users/me/market-profile');
  return response.data;
};

export const saveUserProfile = async (profileData: any): Promise<any> => {
  const response = await apiClient.post('/users/me/market-profile', profileData);
  return response.data;
};

export const updateUserProfile = async (profileData: any): Promise<any> => {
  const response = await apiClient.patch('/users/me/market-profile', profileData);
  return response.data;
};

export const fetchUserInterests = async (): Promise<any[]> => {
  const response = await apiClient.get('/users/me/interests');
  return response.data || [];
};

export const addUserInterest = async (
  topic: string,
  preference_score: number = 1.0
): Promise<any> => {
  const response = await apiClient.post('/users/me/interests', {
    topic,
    preference_score,
    preference_source: 'manual',
  });
  return response.data;
};

export const removeUserInterest = async (topicId: string): Promise<any> => {
  const response = await apiClient.delete(`/users/me/interests/${encodeURIComponent(topicId)}`);
  return response.data;
};

export const fetchFollowedEntities = async (): Promise<any[]> => {
  const response = await apiClient.get('/users/me/followed-entities');
  return response.data || [];
};

export const followEntity = async (entityId: string): Promise<any> => {
  const response = await apiClient.post('/users/me/followed-entities', {
    entity_id: entityId,
  });
  return response.data;
};

export const unfollowEntity = async (entityId: string): Promise<any> => {
  const response = await apiClient.delete(`/users/me/followed-entities/${entityId}`);
  return response.data;
};

export const fetchFeedPreferences = async (): Promise<any> => {
  const response = await apiClient.get('/users/me/feed-preferences');
  return response.data?.settings || {};
};

export const updateFeedPreferences = async (settings: any): Promise<any> => {
  const response = await apiClient.patch('/users/me/feed-preferences', settings);
  return response.data?.settings || {};
};

export const resetLearnedPreferences = async (): Promise<any> => {
  const response = await apiClient.post('/users/me/preferences/reset');
  return response.data;
};

export const recordInteraction = async (payload: {
  event_type: string;
  article_id?: string;
  trend_id?: string;
  topic_id?: string;
  entity_id?: string;
  source_screen?: string;
}): Promise<any> => {
  try {
    const response = await apiClient.post('/interactions', {
      source_screen: 'for_you',
      ...payload,
    });
    return response.data;
  } catch (err: any) {
    console.warn('[Interaction Log Failed]', err?.message);
    return null;
  }
};
