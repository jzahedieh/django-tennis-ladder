import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { apiClient } from "../api/client";
import type { PlayerAutocompleteOption } from "../api/types";
import { cardShadow, colors, radii, spacing } from "../theme/tokens";

export function PlayerSearchBar({
  compact = false,
  onSelect,
}: {
  compact?: boolean;
  onSelect?: () => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(query.trim());
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const { data } = useQuery({
    queryKey: ["player-search", debounced],
    enabled: debounced.length >= 2,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/v1/players/search/", {
        params: { query: { q: debounced, limit: 10 } },
      });
      if (error || !data) return { options: [] as PlayerAutocompleteOption[] };
      return data;
    },
  });

  const options = data?.options ?? [];
  const showDropdown = focused && debounced.length >= 2;

  const handleSelect = (opt: PlayerAutocompleteOption) => {
    setQuery("");
    setDebounced("");
    setFocused(false);
    onSelect?.();
    router.push(`/player/${opt.id}`);
  };

  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]}>
      <View style={[styles.inputRow, compact && styles.inputRowCompact]}>
        <Ionicons name="search" size={16} color={colors.textMuted} />
        <TextInput
          value={query}
          onChangeText={setQuery}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 180)}
          placeholder="Search players..."
          placeholderTextColor={colors.textMuted}
          autoCapitalize="words"
          autoCorrect={false}
          returnKeyType="search"
          style={[styles.input, compact && styles.inputCompact]}
        />
        {query.length > 0 ? (
          <Pressable
            onPress={() => {
              setQuery("");
              setDebounced("");
            }}
            hitSlop={8}
          >
            <Ionicons name="close-circle" size={17} color={colors.textMuted} />
          </Pressable>
        ) : null}
      </View>

      {showDropdown ? (
        <View style={styles.dropdown}>
          {options.length === 0 ? (
            <View style={styles.emptyRow}>
              <Text style={styles.emptyText}>No players found</Text>
            </View>
          ) : (
            options.map((opt) => (
              <Pressable
                key={opt.id}
                onPress={() => handleSelect(opt)}
                style={({ pressed }) => [
                  styles.optionRow,
                  pressed && styles.optionPressed,
                ]}
              >
                <Text style={styles.optionName}>{opt.label}</Text>
                {opt.subtext ? (
                  <Text style={styles.optionMeta}>{opt.subtext}</Text>
                ) : null}
              </Pressable>
            ))
          )}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "relative",
    zIndex: 50,
    minWidth: 240,
  },
  wrapCompact: {
    minWidth: 0,
    width: "100%",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    height: 40,
    gap: spacing.sm,
  },
  inputRowCompact: {
    height: 38,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.md,
  },
  input: {
    flex: 1,
    fontSize: 15,
    fontWeight: "500",
    color: colors.text,
    paddingVertical: 0,
  },
  inputCompact: {
    fontSize: 15,
    fontWeight: "500",
  },
  dropdown: {
    position: "absolute",
    top: 44,
    left: 0,
    right: 0,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
    zIndex: 100,
    ...cardShadow,
  },
  optionRow: {
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  optionPressed: {
    backgroundColor: colors.clubBlueSoft,
  },
  optionName: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
  optionMeta: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  emptyRow: {
    padding: spacing.md,
  },
  emptyText: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
  },
});
