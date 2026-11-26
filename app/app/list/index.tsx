import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import {
  Badge,
  Card,
  ErrorState,
  LoadingState,
  PageScroll,
  SectionHeader,
} from "../../src/components/ui";
import { colors, radii, spacing } from "../../src/theme/tokens";
import { formatDateRange } from "../../src/utils/dates";

export default function PreviousLaddersScreen() {
  const router = useRouter();
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["seasons-archive"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/v1/ladder/seasons/");
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load previous ladders."));
      }
      return data;
    },
  });

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading previous ladders..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load previous ladders."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  const { seasons, available_years, summary } = data;
  const filtered =
    selectedYear === null
      ? seasons
      : seasons.filter((s) => s.year === selectedYear);

  return (
    <PageScroll>
      <Card>
        <SectionHeader
          title="Previous Ladders"
          subtitle={`${summary.total_seasons} published rounds · ${summary.years_span}`}
          right={
            <Badge
              label={`${summary.overall_completion} Avg Completion`}
              variant="green"
            />
          }
        />

        <View style={styles.kpiGrid}>
          <View style={styles.kpiBox}>
            <Text style={styles.kpiVal}>{summary.total_seasons}</Text>
            <Text style={styles.kpiLbl}>Rounds</Text>
          </View>
          <View style={styles.kpiBox}>
            <Text style={styles.kpiVal}>{summary.total_divisions}</Text>
            <Text style={styles.kpiLbl}>Divisions</Text>
          </View>
          <View style={styles.kpiBox}>
            <Text style={styles.kpiVal}>{summary.total_matches_played}</Text>
            <Text style={styles.kpiLbl}>Matches Played</Text>
          </View>
        </View>

        <View style={styles.yearRow}>
          <Pressable
            onPress={() => setSelectedYear(null)}
            style={[
              styles.yearChip,
              selectedYear === null && styles.yearChipActive,
            ]}
          >
            <Text
              style={[
                styles.yearText,
                selectedYear === null && styles.yearTextActive,
              ]}
            >
              All Years
            </Text>
          </Pressable>
          {available_years.map((yr) => (
            <Pressable
              key={yr}
              onPress={() => setSelectedYear(yr)}
              style={[
                styles.yearChip,
                selectedYear === yr && styles.yearChipActive,
              ]}
            >
              <Text
                style={[
                  styles.yearText,
                  selectedYear === yr && styles.yearTextActive,
                ]}
              >
                {yr}
              </Text>
            </Pressable>
          ))}
        </View>
      </Card>

      <View style={styles.list}>
        {filtered.map((s) => (
          <Pressable
            key={s.id}
            onPress={() => router.push(`/${s.year}/round/${s.season_round}`)}
          >
            <Card style={styles.seasonCard}>
              <View style={styles.seasonTop}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.seasonTitle}>{s.name}</Text>
                  <Text style={styles.seasonDates}>
                    {formatDateRange(s.start_date, s.end_date)}
                  </Text>
                </View>
                {s.is_latest ? <Badge label="Latest" variant="navy" /> : null}
              </View>

              <View style={styles.seasonStats}>
                <Text style={styles.statItem}>{s.divisions_count} Divisions</Text>
                <Text style={styles.statItem}>{s.player_count} Players</Text>
                <Text style={styles.statItem}>
                  {s.matches_played} / {s.total_matches} Matches ({s.completion_pct}%)
                </Text>
              </View>
            </Card>
          </Pressable>
        ))}
      </View>
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  kpiGrid: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  kpiBox: {
    flex: 1,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    padding: spacing.md,
    alignItems: "center",
  },
  kpiVal: {
    fontSize: 22,
    fontWeight: "800",
    color: colors.navy,
  },
  kpiLbl: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    marginTop: 2,
  },
  yearRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  yearChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
  },
  yearChipActive: {
    backgroundColor: colors.navy,
  },
  yearText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  yearTextActive: {
    color: colors.white,
  },
  list: {
    gap: spacing.md,
  },
  seasonCard: {
    padding: spacing.lg,
  },
  seasonTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  seasonTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.linkBlue,
  },
  seasonDates: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  seasonStats: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  statItem: {
    fontSize: 15,
    color: colors.textSecondary,
    fontWeight: "600",
  },
});
