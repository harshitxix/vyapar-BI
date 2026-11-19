import React from 'react';
import { ScrollView, TouchableOpacity, Text, StyleSheet } from 'react-native';

export interface DomainOption {
  id: string;
  label: string;
}

const DOMAINS: DomainOption[] = [
  { id: 'all', label: 'All Stories' },
  { id: 'grocery', label: '🛒 Grocery & FMCG' },
  { id: 'retail', label: '🛍️ Retail' },
  { id: 'technology', label: '⚡ Tech & Q-Commerce' },
  { id: 'fashion', label: '👗 Fashion' },
  { id: 'general_business', label: '📈 General Business' },
];

interface DomainFilterBarProps {
  selectedDomain: string;
  onSelectDomain: (domainId: string) => void;
}

export const DomainFilterBar: React.FC<DomainFilterBarProps> = ({
  selectedDomain,
  onSelectDomain,
}) => {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {DOMAINS.map((item) => {
        const isSelected = selectedDomain === item.id;
        return (
          <TouchableOpacity
            key={item.id}
            style={[styles.pill, isSelected && styles.pillSelected]}
            onPress={() => onSelectDomain(item.id)}
            activeOpacity={0.7}
          >
            <Text style={[styles.pillText, isSelected && styles.pillTextSelected]}>
              {item.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 6,
    backgroundColor: '#0F172A',
  },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 16,
    backgroundColor: '#1E293B',
    borderWidth: 1,
    borderColor: '#334155',
  },
  pillSelected: {
    backgroundColor: '#38BDF8',
    borderColor: '#38BDF8',
  },
  pillText: {
    color: '#94A3B8',
    fontSize: 13,
    fontWeight: '600',
  },
  pillTextSelected: {
    color: '#0F172A',
    fontWeight: '700',
  },
});
