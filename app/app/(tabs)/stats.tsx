import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import { useAuth } from "../../src/auth/AuthContext";
import { H2HSheet, type H2HTarget } from "../../src/components/H2HSheet";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  LoadingState,
  PageScroll,
  SectionHeader,
} from "../../src/components/ui";
import { colors, radii, spacing } from "../../src/theme/tokens";

type BoardKey =
  | "most_won"
  | "most_played"
  | "most_points"
  | "most_titles"
  | "highest_completion"
  | "top_rivalries"
  | "best_centile";

const BOARDS: { key: BoardKey; label: string }[] = [
  { key: "most_won", label: "Most Won" },
  { key: "most_played", label: "Most Played" },
  { key: "most_points", label: "Most Points" },
  { key: "most_titles", label: "Division Titles" },
  { key: "highest_completion", label: "Completion %" },
  { key: "top_rivalries", label: "Top Rivalries" },
  { key: "best_centile", label: "Best Centile" },
];

export default function ClubStatsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const params = useLocalSearchParams<{ season?: string }>();
  const initialSeason = params.season ? Number(params.season) : undefined;

  const [period, setPeriod] = useState<"all" | "5y" | "12m">("all");
  const [selectedYear, setSelectedYear] = useState<number | undefined>(
    undefined
  );
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | undefined>(
    initialSeason
  );
  const [activeBoard, setActiveBoard] = useState<BoardKey>("most_won");
  const [page, setPage] = useState(0);
  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);

  useEffect(() => {
    if (params.season) {
      setSelectedSeasonId(Number(params.season));
      setSelectedYear(undefined);
      setPage(0);
    }
  }, [params.season]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [
      "club-stats",
      period,
      selectedYear ?? null,
      selectedSeasonId ?? null,
      user?.id ?? "anon",
    ],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/v1/ladder/stats/", {
        params: {
          query: {
            period,
            year: selectedYear ?? null,
            season_id: selectedSeasonId ?? null,
          },
        },
      });
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load club stats."));
      }
      return data;
    },
  });

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Computing club leaderboards..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load stats."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  const pageSize = data.page_size || 10;
  const rows = data.leaderboards[activeBoard];
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(page, totalPages - 1);
  const pagedRows = rows.slice(safePage * pageSize, (safePage + 1) * pageSize);

  return (
    <PageScroll>
      {/* Filters */}
      <Card>
        <SectionHeader
          title="Club Stats & Leaderboards"
          subtitle={`Showing: ${data.filter.filter_label}`}
        />

        <View style={styles.filterGroup}>
          {(
            [
              ["all", "All-Time"],
              ["5y", "Past 5 Years"],
              ["12m", "Past 12 Months"],
            ] as const
          ).map(([val, lbl]) => {
            const active =
              data.filter.filter_type === "period" &&
              data.filter.period === val;
            return (
              <Pressable
                key={val}
                onPress={() => {
                  setPeriod(val);
                  setSelectedYear(undefined);
                  setSelectedSeasonId(undefined);
                  setPage(0);
                }}
                style={[styles.filterChip, active && styles.filterChipActive]}
              >
                <Text
                  style={[styles.filterText, active && styles.filterTextActive]}
                >
                  {lbl}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.yearChips}
        >
          {data.available_years.slice(0, 10).map((yr) => {
            const active = selectedYear === yr;
            return (
              <Pressable
                key={yr}
                onPress={() => {
                  setSelectedYear(yr);
                  setSelectedSeasonId(undefined);
                  setPage(0);
                }}
                style={[styles.subChip, active && styles.subChipActive]}
              >
                <Text
                  style={[
                    styles.subChipText,
                    active && styles.subChipTextActive,
                  ]}
                >
                  {yr}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </Card>

      {/* Summary KPIs */}
      <View style={styles.kpiRow}>
        <KpiCard label="Rounds" value={data.summary.seasons_count} />
        <KpiCard label="Divisions" value={data.summary.divisions_count} />
        <KpiCard label="Matches" value={data.summary.matches_played} />
        <KpiCard label="Active Players" value={data.summary.active_players} />
      </View>

      {/* Leaderboard Tabs + Table */}
      <Card>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.boardTabs}
        >
          {BOARDS.map((b) => {
            const active = activeBoard === b.key;
            return (
              <Pressable
                key={b.key}
                onPress={() => {
                  setActiveBoard(b.key);
                  setPage(0);
                }}
                style={[styles.boardTab, active && styles.boardTabActive]}
              >
                <Text
                  style={[
                    styles.boardTabText,
                    active && styles.boardTabTextActive,
                  ]}
                >
                  {b.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {pagedRows.length === 0 ? (
          <Text style={styles.empty}>No records for this period filter.</Text>
        ) : activeBoard === "top_rivalries" ? (
          data.leaderboards.top_rivalries
            .slice(safePage * pageSize, (safePage + 1) * pageSize)
            .map((r, idx) => (
              <Pressable
                key={`${r.player_a_id}-${r.player_b_id}`}
                onPress={() =>
                  setH2HTarget({
                    playerId: r.player_a_id,
                    opponentId: r.player_b_id,
                    title: `${r.player_a_name} vs ${r.player_b_name}`,
                  })
                }
                style={styles.row}
              >
                <Text style={styles.rank}>{safePage * pageSize + idx + 1}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>
                    {r.player_a_name} ({r.player_a_wins}) vs {r.player_b_name} (
                    {r.player_b_wins})
                  </Text>
                  <Text style={styles.rowSub}>
                    {r.last_played ? `Last played ${r.last_played}` : ""}
                  </Text>
                </View>
                <Badge label={`${r.matches_played} matches`} variant="blue" />
              </Pressable>
            ))
        ) : activeBoard === "most_won" ||
          activeBoard === "most_played" ||
          activeBoard === "most_points" ? (
          data.leaderboards[activeBoard]
            .slice(safePage * pageSize, (safePage + 1) * pageSize)
            .map((p, idx) => (
              <Pressable
                key={p.player_id}
                onPress={() => router.push(`/player/${p.player_id}`)}
                style={styles.row}
              >
                <Text style={styles.rank}>{safePage * pageSize + idx + 1}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>{p.player_name}</Text>
                  <Text style={styles.rowSub}>
                    {p.won}W / {p.played}P · Win {p.win_rate_display} · Avg{" "}
                    {p.avg_points_display}
                  </Text>
                </View>
                <Text style={styles.primaryVal}>
                  {activeBoard === "most_won"
                    ? `${p.won} W`
                    : activeBoard === "most_played"
                    ? `${p.played} P`
                    : `${p.total_points} pts`}
                </Text>
              </Pressable>
            ))
        ) : (
          data.leaderboards[activeBoard]
            .slice(safePage * pageSize, (safePage + 1) * pageSize)
            .map((p, idx) => (
              <Pressable
                key={p.player_id}
                onPress={() => router.push(`/player/${p.player_id}`)}
                style={styles.row}
              >
                <Text style={styles.rank}>{safePage * pageSize + idx + 1}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>{p.player_name}</Text>
                  <Text style={styles.rowSub}>
                    {p.seasons_played} rounds · Avg centile{" "}
                    {p.avg_centile_display}
                  </Text>
                </View>
                <Text style={styles.primaryVal}>
                  {activeBoard === "most_titles"
                    ? `${p.division_titles} title${p.division_titles === 1 ? "" : "s"}`
                    : activeBoard === "highest_completion"
                    ? p.completion_rate_display
                    : `${p.best_centile}%`}
                </Text>
              </Pressable>
            ))
        )}

        {totalPages > 1 ? (
          <View style={styles.pager}>
            <Button
              label="← Prev"
              variant="outline"
              size="sm"
              disabled={safePage === 0}
              onPress={() => setPage((p) => Math.max(0, p - 1))}
            />
            <Text style={styles.pageNum}>
              Page {safePage + 1} of {totalPages}
            </Text>
            <Button
              label="Next →"
              variant="outline"
              size="sm"
              disabled={safePage >= totalPages - 1}
              onPress={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            />
          </View>
        ) : null}
      </Card>

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

function KpiCard({ label, value }: { label: string; value: number }) {
  return (
    <Card style={styles.kpiCard}>
      <Text style={styles.kpiVal}>{value}</Text>
      <Text style={styles.kpiLbl}>{label}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  filterGroup: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  filterChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radii.md,
    backgroundColor: colors.surfaceMuted,
  },
  filterChipActive: {
    backgroundColor: colors.navy,
  },
  filterText: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  filterTextActive: {
    color: colors.white,
  },
  yearChips: {
    gap: spacing.sm,
    paddingVertical: 4,
  },
  subChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  subChipActive: {
    backgroundColor: colors.clubBlueSoft,
    borderColor: colors.navy,
  },
  subChipText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  subChipTextActive: {
    color: colors.navy,
    fontWeight: "800",
  },
  kpiRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  kpiCard: {
    flex: 1,
    minWidth: 110,
    alignItems: "center",
    paddingVertical: spacing.md,
  },
  kpiVal: {
    fontSize: 24,
    fontWeight: "800",
    color: colors.navy,
  },
  kpiLbl: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    marginTop: 2,
  },
  boardTabs: {
    gap: spacing.sm,
    marginBottom: spacing.md,
    paddingBottom: 4,
  },
  boardTab: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
  },
  boardTabActive: {
    backgroundColor: colors.courtGreen,
  },
  boardTabText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  boardTabTextActive: {
    color: colors.white,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 11,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  rank: {
    width: 30,
    fontSize: 15,
    fontWeight: "800",
    color: colors.textMuted,
    textAlign: "center",
  },
  rowTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.navy,
  },
  rowSub: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  primaryVal: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.courtGreen,
    fontVariant: ["tabular-nums"],
  },
  empty: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
  pager: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.md,
  },
  pageNum: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textMuted,
  },
});
