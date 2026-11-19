import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { RefreshCw, Sliders, Radio } from 'lucide-react-native';

interface HeaderProps {
  onRefreshPress: () => void;
  onSettingsPress?: () => void;
  isRefreshing: boolean;
  totalArticles: number;
  userDomain?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onRefreshPress,
  onSettingsPress,
  isRefreshing,
  totalArticles,
  userDomain,
}) => {
  return (
    <View style={styles.container}>
      <View>
        <View style={styles.titleRow}>
          <Text style={styles.title}>Vyapar</Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>INTELLIGENCE</Text>
          </View>
        </View>
        <View style={styles.statusRow}>
          <View style={styles.liveIndicator} />
          <Text style={styles.subtitle}>
            {userDomain ? `${userDomain.toUpperCase()} Feed` : 'Live Market Feed'} • {totalArticles} Updates
          </Text>
        </View>
      </View>

      <View style={styles.rightButtons}>
        {onSettingsPress && (
          <TouchableOpacity
            style={styles.iconButton}
            onPress={onSettingsPress}
            activeOpacity={0.7}
          >
            <Sliders size={18} color="#38BDF8" />
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.refreshButton}
          onPress={onRefreshPress}
          disabled={isRefreshing}
          activeOpacity={0.7}
        >
          {isRefreshing ? (
            <ActivityIndicator size="small" color="#38BDF8" />
          ) : (
            <RefreshCw size={19} color="#38BDF8" />
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 8,
    backgroundColor: '#0F172A',
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#F8FAFC',
    letterSpacing: -0.5,
  },
  badge: {
    backgroundColor: '#38BDF8',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeText: {
    color: '#0F172A',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 3,
  },
  liveIndicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#10B981',
  },
  subtitle: {
    fontSize: 12,
    color: '#94A3B8',
    fontWeight: '500',
  },
  rightButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#1E293B',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  refreshButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#1E293B',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
});
