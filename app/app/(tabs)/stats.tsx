import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

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
import {
  cardShadow,
  colors,
  radii,
  spacing,
  useResponsive,
} from "../../src/theme/tokens";
import { formatDate } from "../../src/utils/dates";

type PickerOption = {
  key: string;
  label: string;
  onSelect: () => void;
};

export default function ClubStatsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ season?: string }>();
  const initialSeason = params.season ? Number(params.season) : undefined;

  const [period, setPeriod] = useState<"all" | "5y" | "12m">("all");
  const [selectedYear, setSelectedYear] = useState<number | undefined>(
    undefined
  );
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | undefined>(
    initialSeason
  );
  const [pickerModal, setPickerModal] = useState<"year" | "season" | null>(
    null
  );
  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);

  useEffect(() => {
    if (params.season) {
      setSelectedSeasonId(Number(params.season));
      setSelectedYear(undefined);
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
  const filterResetKey = `${data.filter.filter_type}:${data.filter.period ?? ""}:${data.filter.selected_year ?? ""}:${data.filter.selected_season_id ?? ""}`;
  const selectedSeasonObj = data.available_seasons.find(
    (s) => s.id === data.filter.selected_season_id
  );

  const yearOptions: PickerOption[] = [
    {
      key: "clear-year",
      label: "All Years (Clear Year Filter)",
      onSelect: () => {
        setSelectedYear(undefined);
        setSelectedSeasonId(undefined);
      },
    },
    ...data.available_years.map((yr) => ({
      key: String(yr),
      label: String(yr),
      onSelect: () => {
        setSelectedYear(yr);
        setSelectedSeasonId(undefined);
      },
    })),
  ];

  const seasonOptions: PickerOption[] = [
    {
      key: "clear-season",
      label: "All Rounds (Clear Round Filter)",
      onSelect: () => {
        setSelectedSeasonId(undefined);
        setSelectedYear(undefined);
      },
    },
    ...data.available_seasons.map((s) => ({
      key: String(s.id),
      label: `${s.year} Round ${s.season_round}`,
      onSelect: () => {
        setSelectedSeasonId(s.id);
        setSelectedYear(undefined);
      },
    })),
  ];

  const halfColStyle = isDesktop ? styles.gridHalf : undefined;

  return (
    <PageScroll>
      {/* Header & Filters */}
      <Card style={styles.compactCard}>
        <Text style={styles.pageTitle}>Club Stats & Leaderboards</Text>
        <View style={styles.showingRow}>
          <Text style={styles.showingText}>Showing records for:</Text>
          <Badge label={data.filter.filter_label} variant="navy" />
        </View>

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

        <View style={styles.selectRow}>
          <Pressable
            onPress={() => setPickerModal("year")}
            style={[
              styles.selectBtn,
              data.filter.selected_year ? styles.selectBtnActive : undefined,
            ]}
          >
            <Text
              style={[
                styles.selectBtnText,
                data.filter.selected_year ? styles.selectBtnTextActive : undefined,
              ]}
              numberOfLines={1}
            >
              {data.filter.selected_year
                ? `Year: ${data.filter.selected_year}`
                : "By Year..."}
            </Text>
            <Text style={styles.caret}>▾</Text>
          </Pressable>

          <Pressable
            onPress={() => setPickerModal("season")}
            style={[
              styles.selectBtn,
              selectedSeasonObj ? styles.selectBtnActive : undefined,
            ]}
          >
            <Text
              style={[
                styles.selectBtnText,
                selectedSeasonObj ? styles.selectBtnTextActive : undefined,
              ]}
              numberOfLines={1}
            >
              {selectedSeasonObj
                ? `${selectedSeasonObj.year} R${selectedSeasonObj.season_round}`
                : "By Round..."}
            </Text>
            <Text style={styles.caret}>▾</Text>
          </Pressable>
        </View>
      </Card>

      {/* Period Summary KPI Strip */}
      <View style={styles.kpiGrid}>
        <KpiTile
          label="LADDERS / ROUNDS"
          value={data.summary.seasons_count}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="TOTAL DIVISIONS"
          value={data.summary.divisions_count}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="MATCHES PLAYED"
          value={data.summary.matches_played}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="ACTIVE PLAYERS"
          value={data.summary.active_players}
          isDesktop={isDesktop}
        />
      </View>

      {/* Leaderboards Grid (all 7 cards matching web) */}
      <View style={[styles.boardsGrid, isDesktop && styles.boardsGridDesktop]}>
        {/* 1. Most Matches Won */}
        <LeaderboardCard
          title="Most Matches Won"
          badge={data.filter.filter_label}
          rows={data.leaderboards.most_won}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage="No matches recorded for this period."
          containerStyle={halfColStyle}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Player</Text>
              <Text style={[styles.th, styles.colSm]}>Played</Text>
              <Text style={[styles.th, styles.colMd]}>Win %</Text>
              <Text style={[styles.th, styles.colVal]}>Won</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => (
            <Pressable
              key={row.player_id}
              onPress={() => router.push(`/player/${row.player_id}`)}
              style={[styles.tr, isLast && styles.trLast]}
            >
              <Text style={styles.rankCell}>{rank}</Text>
              <Text style={[styles.playerLink, { flex: 1 }]} numberOfLines={1}>
                {row.player_name}
              </Text>
              <Text style={[styles.numMuted, styles.colSm]} numberOfLines={1}>
                {row.played}
              </Text>
              <Text style={[styles.numMuted, styles.colMd]} numberOfLines={1}>
                {row.win_rate_display}
              </Text>
              <Text style={[styles.numBold, styles.colVal]} numberOfLines={1}>
                {row.won}
              </Text>
            </Pressable>
          )}
        />

        {/* 2. Most Matches Played */}
        <LeaderboardCard
          title="Most Matches Played"
          badge="Most Active"
          rows={data.leaderboards.most_played}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage="No matches recorded for this period."
          containerStyle={halfColStyle}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Player</Text>
              <Text style={[styles.th, styles.colSm]}>Won</Text>
              <Text style={[styles.th, styles.colMd]}>Win %</Text>
              <Text style={[styles.th, styles.colVal]}>Played</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => (
            <Pressable
              key={row.player_id}
              onPress={() => router.push(`/player/${row.player_id}`)}
              style={[styles.tr, isLast && styles.trLast]}
            >
              <Text style={styles.rankCell}>{rank}</Text>
              <Text style={[styles.playerLink, { flex: 1 }]} numberOfLines={1}>
                {row.player_name}
              </Text>
              <Text style={[styles.numMuted, styles.colSm]} numberOfLines={1}>
                {row.won}
              </Text>
              <Text style={[styles.numMuted, styles.colMd]} numberOfLines={1}>
                {row.win_rate_display}
              </Text>
              <Text style={[styles.numBold, styles.colVal]} numberOfLines={1}>
                {row.played}
              </Text>
            </Pressable>
          )}
        />

        {/* 3. Most Total Points */}
        <LeaderboardCard
          title="Most Total Points"
          badge="12 / win · games+1 / loss"
          rows={data.leaderboards.most_points}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage="No points recorded for this period."
          containerStyle={halfColStyle}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Player</Text>
              <Text style={[styles.th, styles.colSm]}>Played</Text>
              <Text style={[styles.th, styles.colMd]}>Avg Pts</Text>
              <Text style={[styles.th, styles.colVal]}>Points</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => (
            <Pressable
              key={row.player_id}
              onPress={() => router.push(`/player/${row.player_id}`)}
              style={[styles.tr, isLast && styles.trLast]}
            >
              <Text style={styles.rankCell}>{rank}</Text>
              <Text style={[styles.playerLink, { flex: 1 }]} numberOfLines={1}>
                {row.player_name}
              </Text>
              <Text style={[styles.numMuted, styles.colSm]}>{row.played}</Text>
              <Text style={[styles.numMuted, styles.colMd]}>
                {row.avg_points_display}
              </Text>
              <Text style={[styles.numBold, styles.colVal]}>
                {row.total_points}
              </Text>
            </Pressable>
          )}
        />

        {/* 4. Most Division Titles */}
        <LeaderboardCard
          title="Most Division Titles"
          badge="#1 Finishes"
          rows={data.leaderboards.most_titles}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage="No division titles recorded in this period."
          containerStyle={halfColStyle}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Player</Text>
              <Text style={[styles.th, styles.colSm]}>Rounds</Text>
              <Text style={[styles.th, styles.colVal]}>Titles</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => (
            <Pressable
              key={row.player_id}
              onPress={() => router.push(`/player/${row.player_id}`)}
              style={[styles.tr, isLast && styles.trLast]}
            >
              <Text style={styles.rankCell}>{rank}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.playerLink} numberOfLines={1}>
                  {row.player_name}
                </Text>
                {row.divisions_won_badges.length > 0 ? (
                  <View style={styles.divBadgesWrap}>
                    {row.divisions_won_badges.map((b) => (
                      <Badge
                        key={b.division}
                        label={b.label}
                        variant={b.is_div1 ? "amber" : "neutral"}
                      />
                    ))}
                  </View>
                ) : null}
              </View>
              <Text style={[styles.numMuted, styles.colSm]}>
                {row.seasons_played}
              </Text>
              <Text style={[styles.numBold, styles.colVal]}>
                {row.division_titles}
              </Text>
            </Pressable>
          )}
        />

        {/* 5. Match Completion % */}
        <LeaderboardCard
          title="Match Completion %"
          badge={`Min ${data.filter.min_rounds} round${data.filter.min_rounds === 1 ? "" : "s"}`}
          rows={data.leaderboards.highest_completion}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage={`No players with at least ${data.filter.min_rounds} round${data.filter.min_rounds === 1 ? "" : "s"} in this period.`}
          containerStyle={halfColStyle}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Player</Text>
              <Text style={[styles.th, styles.colMd]}>Matches</Text>
              <Text style={[styles.th, styles.colSm]}>Rds</Text>
              <Text style={[styles.th, styles.colVal]}>Rate</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => (
            <Pressable
              key={row.player_id}
              onPress={() => router.push(`/player/${row.player_id}`)}
              style={[styles.tr, isLast && styles.trLast]}
            >
              <Text style={styles.rankCell}>{rank}</Text>
              <Text style={[styles.playerLink, { flex: 1 }]} numberOfLines={1}>
                {row.player_name}
              </Text>
              <Text style={[styles.numMuted, styles.colMd]} numberOfLines={1}>
                {row.played_matches}/{row.scheduled_matches}
              </Text>
              <Text style={[styles.numMuted, styles.colSm]} numberOfLines={1}>
                {row.seasons_played}
              </Text>
              <Text style={[styles.numBold, styles.colVal]} numberOfLines={1}>
                {row.completion_rate_display}
              </Text>
            </Pressable>
          )}
        />

        {/* 6. Most Played Rivalries */}
        <LeaderboardCard
          title="Most Played Rivalries"
          badge="Head-to-Head"
          rows={data.leaderboards.top_rivalries}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage="No repeat head-to-head matchups in this period."
          containerStyle={halfColStyle}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Rivalry</Text>
              <Text style={[styles.th, styles.colMd]}>Record</Text>
              <Text style={[styles.th, styles.colVal]}>Matches</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => {
            const lastPlayed = formatDate(row.last_played).replace(
              /^\d+\s+/,
              ""
            );
            return (
              <Pressable
                key={`${row.player_a_id}-${row.player_b_id}`}
                onPress={() =>
                  setH2HTarget({
                    playerId: row.player_a_id,
                    opponentId: row.player_b_id,
                    title: `${row.player_a_name} vs ${row.player_b_name}`,
                  })
                }
                style={[styles.tr, isLast && styles.trLast]}
              >
                <Text style={styles.rankCell}>{rank}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.playerLink} numberOfLines={2}>
                    {row.player_a_name}{" "}
                    <Text style={styles.vsText}>vs</Text> {row.player_b_name}
                  </Text>
                  {lastPlayed ? (
                    <Text style={styles.rowSub}>Last played {lastPlayed}</Text>
                  ) : null}
                </View>
                <View style={styles.colMd}>
                  <Badge
                    label={`${row.player_a_wins}–${row.player_b_wins}`}
                    variant="neutral"
                  />
                </View>
                <Text style={[styles.numBold, styles.colVal]}>
                  {row.matches_played}
                </Text>
              </Pressable>
            );
          }}
        />

        {/* 7. Best Centile & Top Finishers (full width at bottom) */}
        <LeaderboardCard
          title="Best Centile & Top Finishers"
          subtitle="Highest overall club standing achieved across divisions (higher % = higher up the club ladder)"
          badge={data.filter.filter_label}
          rows={data.leaderboards.best_centile}
          pageSize={pageSize}
          resetKey={filterResetKey}
          emptyMessage="No ladder standings recorded for this period."
          containerStyle={isDesktop ? styles.gridFull : undefined}
          headerColumns={
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.colRank]}>#</Text>
              <Text style={[styles.th, { flex: 1 }]}>Player</Text>
              <Text style={[styles.th, styles.colRankCol]}>Rank</Text>
              <Text style={[styles.th, styles.colSm]}>Avg</Text>
              <Text style={[styles.th, styles.colVal]}>Best</Text>
            </View>
          }
          renderRow={(row, rank, isLast) => (
            <View
              key={row.player_id}
              style={[styles.tr, isLast && styles.trLast]}
            >
              <Text style={styles.rankCell}>{rank}</Text>
              <View style={{ flex: 1 }}>
                <Pressable onPress={() => router.push(`/player/${row.player_id}`)}>
                  <Text style={styles.playerLink} numberOfLines={1}>
                    {row.player_name}
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() =>
                    router.push(
                      `/${row.best_year}/round/${row.best_round}/division/${row.best_division}`
                    )
                  }
                >
                  <Text style={styles.rowSub} numberOfLines={1}>
                    {row.best_year} R{row.best_round} · Div {row.best_division} ·{" "}
                    {row.seasons_played} rds
                  </Text>
                </Pressable>
              </View>
              <View style={styles.rankColWrap}>
                <Text style={styles.numMuted}>
                  #{row.best_rank}/{row.best_total_players}
                </Text>
                {row.peak_count > 1 ? (
                  <Badge label={`×${row.peak_count}`} variant="neutral" />
                ) : null}
              </View>
              <Text style={[styles.numMuted, styles.colSm]}>
                {row.avg_centile_display}
              </Text>
              <Text style={[styles.numBold, styles.colVal]}>
                {row.best_centile}%
              </Text>
            </View>
          )}
        />
      </View>

      {/* Year / Round Picker Modal */}
      <Modal
        visible={pickerModal !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setPickerModal(null)}
      >
        <Pressable
          style={styles.modalBackdrop}
          onPress={() => setPickerModal(null)}
        >
          <Pressable style={styles.modalSheet} onPress={() => {}}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {pickerModal === "year" ? "Filter by Year" : "Filter by Round"}
              </Text>
              <Pressable onPress={() => setPickerModal(null)}>
                <Text style={styles.modalClose}>Done</Text>
              </Pressable>
            </View>
            <FlatList
              data={pickerModal === "year" ? yearOptions : seasonOptions}
              keyExtractor={(item) => item.key}
              renderItem={({ item }) => (
                <Pressable
                  onPress={() => {
                    item.onSelect();
                    setPickerModal(null);
                  }}
                  style={styles.modalRow}
                >
                  <Text style={styles.modalRowText}>{item.label}</Text>
                </Pressable>
              )}
            />
          </Pressable>
        </Pressable>
      </Modal>

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

function KpiTile({
  label,
  value,
  isDesktop,
}: {
  label: string;
  value: number;
  isDesktop: boolean;
}) {
  return (
    <View
      style={[
        styles.kpiBox,
        isDesktop ? styles.kpiBoxDesktop : styles.kpiBoxMobile,
      ]}
    >
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiVal}>{value}</Text>
    </View>
  );
}

function LeaderboardCard<T>({
  title,
  subtitle,
  badge,
  rows,
  pageSize,
  resetKey,
  emptyMessage,
  headerColumns,
  renderRow,
  containerStyle,
}: {
  title: string;
  subtitle?: string;
  badge: string;
  rows: T[];
  pageSize: number;
  resetKey: string;
  emptyMessage: string;
  headerColumns: React.ReactNode;
  renderRow: (row: T, rank: number, isLast: boolean) => React.ReactNode;
  containerStyle?: object;
}) {
  const [page, setPage] = useState(0);

  useEffect(() => {
    setPage(0);
  }, [resetKey]);

  const total = rows.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages - 1);
  const start = safePage * pageSize;
  const end = Math.min(start + pageSize, total);
  const pagedRows = rows.slice(start, end);

  return (
    <Card style={[styles.compactCard, containerStyle]}>
      <SectionHeader
        title={title}
        subtitle={subtitle}
        right={<Badge label={badge} variant="neutral" />}
      />

      {total === 0 ? (
        <Text style={styles.empty}>{emptyMessage}</Text>
      ) : (
        <>
          {headerColumns}
          {pagedRows.map((row, idx) =>
            renderRow(row, start + idx + 1, idx === pagedRows.length - 1)
          )}
        </>
      )}

      {total > pageSize ? (
        <View style={styles.pager}>
          <Text style={styles.pageStatus}>
            Showing {start + 1}–{end} of {total}
          </Text>
          <View style={styles.pagerBtns}>
            <Button
              label={`« Prev ${pageSize}`}
              variant="outline"
              size="sm"
              disabled={safePage === 0}
              onPress={() => setPage((p) => Math.max(0, p - 1))}
            />
            <Button
              label={`Next ${pageSize} »`}
              variant="outline"
              size="sm"
              disabled={safePage >= totalPages - 1}
              onPress={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            />
          </View>
        </View>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  compactCard: {
    padding: spacing.md,
  },
  pageTitle: {
    fontSize: 24,
    fontWeight: "800",
    color: colors.text,
  },
  showingRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: spacing.xs,
    marginTop: 4,
    marginBottom: spacing.md,
  },
  showingText: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
  },
  filterGroup: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
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
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  filterTextActive: {
    color: colors.white,
  },
  selectRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  selectBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    backgroundColor: colors.surface,
  },
  selectBtnActive: {
    borderColor: colors.navy,
    backgroundColor: colors.clubBlueSoft,
  },
  selectBtnText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textSecondary,
    flexShrink: 1,
  },
  selectBtnTextActive: {
    color: colors.navy,
    fontWeight: "700",
  },
  caret: {
    fontSize: 12,
    color: colors.textMuted,
    marginLeft: 6,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  kpiBox: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    paddingVertical: 10,
    paddingHorizontal: spacing.sm,
    alignItems: "center",
    ...cardShadow,
  },
  kpiBoxMobile: {
    flexBasis: "47%",
    flexGrow: 1,
  },
  kpiBoxDesktop: {
    flexBasis: "23%",
    flexGrow: 1,
  },
  kpiLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.4,
    textAlign: "center",
  },
  kpiVal: {
    fontSize: 22,
    fontWeight: "800",
    color: colors.text,
    marginTop: 2,
    fontVariant: ["tabular-nums"],
  },
  boardsGrid: {
    gap: spacing.lg,
  },
  boardsGridDesktop: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "stretch",
  },
  gridHalf: {
    flexBasis: "48%",
    flexGrow: 1,
  },
  gridFull: {
    flexBasis: "100%",
  },
  tableHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  th: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textMuted,
    textTransform: "uppercase",
  },
  tr: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  trLast: {
    borderBottomWidth: 0,
    paddingBottom: 2,
  },
  colRank: {
    width: 24,
    textAlign: "center",
  },
  colSm: {
    width: 54,
    textAlign: "center",
  },
  colMd: {
    width: 64,
    textAlign: "center",
    alignItems: "center",
  },
  colVal: {
    width: 62,
    textAlign: "right",
  },
  colRankCol: {
    width: 72,
    textAlign: "center",
  },
  rankCell: {
    width: 24,
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    textAlign: "center",
    fontVariant: ["tabular-nums"],
  },
  playerLink: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.linkBlue,
  },
  vsText: {
    fontWeight: "400",
    color: colors.textMuted,
  },
  rowSub: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  divBadgesWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 4,
    marginTop: 4,
  },
  rankColWrap: {
    width: 72,
    alignItems: "center",
    gap: 2,
  },
  numMuted: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
    fontVariant: ["tabular-nums"],
  },
  numBold: {
    fontSize: 15,
    fontWeight: "800",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  empty: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
  pager: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
    marginTop: spacing.md,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceMuted,
  },
  pageStatus: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.textMuted,
  },
  pagerBtns: {
    flexDirection: "row",
    gap: spacing.xs,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.45)",
    justifyContent: "center",
    padding: spacing.lg,
  },
  modalSheet: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    maxHeight: "70%",
    overflow: "hidden",
    ...cardShadow,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.text,
  },
  modalClose: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.linkBlue,
  },
  modalRow: {
    paddingHorizontal: spacing.lg,
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  modalRowText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
});
