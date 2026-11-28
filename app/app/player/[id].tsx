import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import type { PlayerH2HSummaryOut } from "../../src/api/types";
import { useAuth } from "../../src/auth/AuthContext";
import { CentileHistoryChart } from "../../src/components/CentileHistoryChart";
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
import { cardShadow, colors, radii, spacing, useResponsive } from "../../src/theme/tokens";
import { formatDate } from "../../src/utils/dates";

function paramNum(v: string | string[] | undefined): number {
  const s = Array.isArray(v) ? v[0] : v;
  return Number(s || 0);
}

export default function PlayerProfileScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ id: string }>();
  const playerId = paramNum(params.id);

  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);
  const [h2hFilter, setH2hFilter] = useState("");
  const [h2hLimit, setH2hLimit] = useState(10);
  const [histLimit, setHistLimit] = useState(10);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["player-profile", playerId, user?.id ?? "anon"],
    enabled: playerId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/v1/players/{player_id}/", {
        params: { path: { player_id: playerId } },
      });
      if (error || !data) {
        throw new Error(extractApiError(error, "Player not found."));
      }
      return data;
    },
  });

  const filteredH2H = useMemo(() => {
    const rows = data?.head_to_head ?? [];
    const q = h2hFilter.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((h) => h.opponent_name.toLowerCase().includes(q));
  }, [data?.head_to_head, h2hFilter]);

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading player profile..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load player."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  const { stats, insights, centile_chart_data, head_to_head, season_history } =
    data;

  const activeYears = stats.first_year
    ? stats.last_year && stats.last_year !== stats.first_year
      ? `${stats.first_year}–${stats.last_year}`
      : String(stats.first_year)
    : null;

  const playedBreakdown = [
    `${stats.won}W – ${stats.lost}L`,
    stats.retired > 0 ? `${stats.retired}R` : null,
    stats.incomplete > 0 ? `${stats.incomplete}I` : null,
  ]
    .filter(Boolean)
    .join(" – ");

  const visibleH2H = h2hFilter.trim()
    ? filteredH2H
    : filteredH2H.slice(0, h2hLimit);

  return (
    <PageScroll>
      {/* Header */}
      <Card style={styles.compactCard}>
        <Text style={styles.playerName}>{data.player_name}</Text>
        <Text style={styles.headerMeta}>
          {[
            activeYears ? `Active: ${activeYears}` : null,
            `${stats.seasons_played} round${stats.seasons_played === 1 ? "" : "s"}`,
            stats.unique_opponents
              ? `${stats.unique_opponents} opponent${stats.unique_opponents === 1 ? "" : "s"}`
              : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </Text>
        {stats.divisions_won_badges.length > 0 ? (
          <View style={styles.badgeRow}>
            {stats.divisions_won_badges.map((b) => (
              <Badge
                key={b.division}
                label={`🏆 ${b.label}`}
                variant={b.is_div1 ? "amber" : "neutral"}
              />
            ))}
          </View>
        ) : null}
      </Card>

      {/* Career KPI Strip */}
      <View style={styles.kpiGrid}>
        <KpiTile
          label="PLAYED"
          value={String(stats.played)}
          sub={insights.has_matches ? playedBreakdown : undefined}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="WIN RATE"
          value={stats.win_rate}
          sub={insights.has_matches ? `${stats.won} won` : undefined}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="COMPLETION"
          value={stats.completion_rate}
          sub={
            stats.scheduled_matches
              ? `${stats.played}/${stats.scheduled_matches} matches`
              : undefined
          }
          isDesktop={isDesktop}
        />
        <KpiTile
          label="AVG. POINTS"
          value={stats.average}
          sub={insights.has_matches ? `${stats.total_points} total pts` : undefined}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="BEST CENTILE"
          value={stats.best_centile}
          sub={`Avg: ${stats.avg_centile}${stats.best_rank ? ` · #${stats.best_rank}` : ""}`}
          isDesktop={isDesktop}
        />
        <KpiTile
          label="DIV TITLES"
          value={String(stats.division_titles)}
          sub={`Peak: Div ${stats.highest_division} · ${stats.seasons_played} rds`}
          isDesktop={isDesktop}
        />
      </View>

      {/* Insights & Highlights (3 cards matching mobile/desktop web) */}
      {insights.has_matches ? (
        <View style={[styles.insightsGrid, isDesktop && styles.insightsGridDesktop]}>
          <Card style={[styles.compactCard, isDesktop && styles.insightCol]}>
            <SectionHeader
              title="Form & Milestones"
              right={<Badge label="Streaks" />}
            />
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>Recent Form</Text>
              <View style={styles.formBadges}>
                {insights.recent_form.map((m, idx) => (
                  <Pressable
                    key={`${m.date_added}-${idx}`}
                    onPress={() =>
                      setH2HTarget({
                        playerId,
                        opponentId: m.opponent_id,
                        title: `${data.player_name} vs ${m.opponent_name}`,
                      })
                    }
                    style={[
                      styles.formBadge,
                      m.outcome_code === "W"
                        ? styles.formWin
                        : m.outcome_code === "R"
                        ? styles.formRet
                        : m.outcome_code === "I"
                        ? styles.formInc
                        : styles.formLoss,
                    ]}
                  >
                    <Text
                      style={[
                        styles.formBadgeText,
                        m.outcome_code === "W"
                          ? styles.formWinText
                          : m.outcome_code === "R"
                          ? styles.formRetText
                          : m.outcome_code === "I"
                          ? styles.formIncText
                          : styles.formLossText,
                      ]}
                    >
                      {m.outcome_code}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>Longest Win Streak</Text>
              <View style={styles.kvRightWrap}>
                <Text style={styles.kvValue}>
                  {insights.longest_win_streak} win
                  {insights.longest_win_streak === 1 ? "" : "s"}
                </Text>
                {insights.current_win_streak > 1 ? (
                  <Badge
                    label={`${insights.current_win_streak} active`}
                    variant="green"
                  />
                ) : null}
              </View>
            </View>
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>100% Rounds Completed</Text>
              <Text style={styles.kvValue}>
                {insights.full_completion_rounds}/{stats.seasons_played}{" "}
                <Text style={styles.kvSub}>({insights.full_completion_rate})</Text>
              </Text>
            </View>
            <View style={[styles.kvRow, styles.kvRowLast]}>
              <Text style={styles.kvLabel}>Best Round Haul</Text>
              <Text style={styles.kvValue}>
                {insights.best_round_points ? (
                  <>
                    {insights.best_round_points} pts{" "}
                    <Text style={styles.kvSub}>({insights.best_round_label})</Text>
                  </>
                ) : (
                  "—"
                )}
              </Text>
            </View>
          </Card>

          <Card style={[styles.compactCard, isDesktop && styles.insightCol]}>
            <SectionHeader
              title="Matchup Profile"
              right={<Badge label="Performance" />}
            />
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>Close Matches (9–7 / 9–8)</Text>
              <Text style={styles.kvValue}>
                {insights.clutch_played > 0 ? (
                  <>
                    {insights.clutch_won}/{insights.clutch_played} won{" "}
                    <Text style={styles.kvSub}>({insights.clutch_win_rate})</Text>
                  </>
                ) : (
                  "0 played"
                )}
              </Text>
            </View>
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>Dominant Wins (9–0 to 9–2)</Text>
              <View style={styles.kvRightWrap}>
                <Text style={styles.kvValue}>{insights.dominant_wins}</Text>
                {insights.bagels_won > 0 ? (
                  <Badge
                    label={`${insights.bagels_won} × 9–0`}
                    variant="amber"
                  />
                ) : null}
              </View>
            </View>
            <View style={styles.kvRow}>
              <Text style={styles.kvLabel}>Total Games Won / Lost</Text>
              <Text style={styles.kvValue}>
                {insights.total_games_won}–{insights.total_games_lost}{" "}
                <Text style={styles.kvSub}>({insights.games_win_rate})</Text>
              </Text>
            </View>
            <View style={[styles.kvRow, styles.kvRowLast]}>
              <Text style={styles.kvLabel}>Avg Score (Win / Loss)</Text>
              <Text style={styles.kvValue}>
                9–{insights.avg_loser_score_in_wins}{" "}
                <Text style={styles.kvSub}>/</Text>{" "}
                {insights.avg_player_score_in_losses}–9
              </Text>
            </View>
          </Card>

          <Card style={[styles.compactCard, isDesktop && styles.insightCol]}>
            <SectionHeader
              title="Rivalry Highlights"
              right={<Badge label="Tap for H2H" />}
            />
            <RivalRow
              label="Most Played"
              rival={insights.most_played_rival}
              pillVariant="neutral"
              onPress={(rival) =>
                setH2HTarget({
                  playerId,
                  opponentId: rival.opponent_id,
                  title: `${data.player_name} vs ${rival.opponent_name}`,
                })
              }
            />
            <RivalRow
              label="Most Wins Against"
              rival={insights.favourite_rival}
              pillVariant="green"
              onPress={(rival) =>
                setH2HTarget({
                  playerId,
                  opponentId: rival.opponent_id,
                  title: `${data.player_name} vs ${rival.opponent_name}`,
                })
              }
            />
            <RivalRow
              label="Toughest Rival"
              rival={insights.toughest_rival}
              pillVariant="neutral"
              onPress={(rival) =>
                setH2HTarget({
                  playerId,
                  opponentId: rival.opponent_id,
                  title: `${data.player_name} vs ${rival.opponent_name}`,
                })
              }
            />
            <View style={[styles.kvRow, styles.kvRowLast]}>
              <Text style={styles.kvLabel}>Unique Opponents</Text>
              <Text style={styles.kvValue}>
                {stats.unique_opponents} player
                {stats.unique_opponents === 1 ? "" : "s"}
              </Text>
            </View>
          </Card>
        </View>
      ) : null}

      {/* Head-to-Head */}
      {head_to_head.length > 0 ? (
        <Card style={styles.compactCard}>
          <SectionHeader
            title="Head-to-Head"
            subtitle="Tap any matchup to view full match history"
          />
          {head_to_head.length > 5 ? (
            <TextInput
              value={h2hFilter}
              onChangeText={setH2hFilter}
              placeholder="Filter rivals..."
              placeholderTextColor={colors.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              style={styles.filterInput}
            />
          ) : null}

          <View style={styles.tableHeader}>
            <Text style={[styles.tableHeaderText, { flex: 1 }]}>Player</Text>
            <Text style={[styles.tableHeaderText, styles.colRecord]}>
              Won / Played
            </Text>
            <Text style={[styles.tableHeaderText, styles.colDate]}>
              Last Played
            </Text>
          </View>

          {visibleH2H.length === 0 ? (
            <Text style={styles.emptyText}>No matching opponents.</Text>
          ) : (
            visibleH2H.map((h, idx) => (
              <View
                key={h.opponent_id}
                style={[
                  styles.h2hRow,
                  idx === visibleH2H.length - 1 && styles.kvRowLast,
                ]}
              >
                <Pressable
                  onPress={() => router.push(`/player/${h.opponent_id}`)}
                  style={{ flex: 1 }}
                >
                  <Text style={styles.h2hName} numberOfLines={2}>
                    {h.opponent_name}
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() =>
                    setH2HTarget({
                      playerId,
                      opponentId: h.opponent_id,
                      title: `${data.player_name} vs ${h.opponent_name}`,
                    })
                  }
                  style={styles.h2hTapArea}
                >
                  <View style={styles.h2hRecordWrap}>
                    <Text style={styles.h2hRecord}>{h.won_played_display}</Text>
                    <Badge
                      label={h.win_rate_display}
                      variant={h.win_rate > 50 ? "green" : "neutral"}
                    />
                  </View>
                  <Text style={styles.h2hDate} numberOfLines={1}>
                    {formatDate(h.last_played).replace(/^\d+\s+/, "") || "—"}
                  </Text>
                </Pressable>
              </View>
            ))
          )}

          {!h2hFilter.trim() && filteredH2H.length > h2hLimit ? (
            <Button
              label={`Show More (${filteredH2H.length - h2hLimit} remaining)`}
              variant="outline"
              size="sm"
              onPress={() => setH2hLimit((p) => p + 15)}
              style={{ marginTop: spacing.md }}
            />
          ) : null}
        </Card>
      ) : null}

      {/* History */}
      {season_history.length > 0 ? (
        <Card style={styles.compactCard}>
          <SectionHeader
            title="History"
            subtitle={`${season_history.length} ladder round${season_history.length === 1 ? "" : "s"} entered`}
            right={
              stats.division_titles > 0 ? (
                <Badge
                  label={`🏆 ${stats.division_titles} Title${stats.division_titles === 1 ? "" : "s"}`}
                  variant="amber"
                />
              ) : null
            }
          />
          {season_history.slice(0, histLimit).map((item, idx, arr) => (
            <Pressable
              key={item.league_id}
              onPress={() =>
                router.push(
                  `/${item.year}/round/${item.season_round}/division/${item.division}`
                )
              }
              style={[
                styles.histRow,
                idx === arr.length - 1 && styles.kvRowLast,
              ]}
            >
              <View style={{ flex: 1 }}>
                <View style={styles.histTitleRow}>
                  <Text style={styles.histTitle}>
                    {item.year} R{item.season_round} · Div {item.division}
                  </Text>
                  {item.is_division_winner ? (
                    <Badge label="🏆 1st" variant="amber" />
                  ) : null}
                </View>
                <Text style={styles.histMeta}>
                  {item.won_count}/{item.games} won · {item.pct_played}% played · Avg{" "}
                  {item.points_per_game.toFixed(2)}
                </Text>
              </View>
              <View style={styles.histRight}>
                <Text style={styles.ptsVal}>{item.total_points} pts</Text>
                {item.centile !== null && item.centile !== undefined ? (
                  <Text style={styles.histMeta}>{item.centile}% centile</Text>
                ) : null}
              </View>
            </Pressable>
          ))}
          {season_history.length > histLimit ? (
            <Button
              label="Show Older Rounds"
              variant="outline"
              size="sm"
              onPress={() => setHistLimit((p) => p + 15)}
              style={{ marginTop: spacing.md }}
            />
          ) : null}
        </Card>
      ) : null}

      {/* Centile Position at the bottom (matching mobile web) */}
      {centile_chart_data.length > 0 ? (
        <Card style={styles.compactCard}>
          <SectionHeader
            title="Centile Position"
            subtitle="Position across the whole ladder as a percentage (100% = Division 1 Winner)"
          />
          <CentileHistoryChart data={centile_chart_data} />
        </Card>
      ) : null}

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

function KpiTile({
  label,
  value,
  sub,
  isDesktop,
}: {
  label: string;
  value: string;
  sub?: string;
  isDesktop: boolean;
}) {
  return (
    <View style={[styles.kpiBox, isDesktop ? styles.kpiBoxDesktop : styles.kpiBoxMobile]}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiValue}>{value}</Text>
      {sub ? (
        <Text style={styles.kpiSub} numberOfLines={1}>
          {sub}
        </Text>
      ) : null}
    </View>
  );
}

function RivalRow({
  label,
  rival,
  pillVariant,
  onPress,
}: {
  label: string;
  rival: PlayerH2HSummaryOut | null | undefined;
  pillVariant: "neutral" | "green";
  onPress: (rival: PlayerH2HSummaryOut) => void;
}) {
  return (
    <View style={styles.kvRow}>
      <Text style={styles.kvLabel}>{label}</Text>
      {rival ? (
        <Pressable onPress={() => onPress(rival)} style={styles.kvRightWrap}>
          <Text style={styles.rivalLink} numberOfLines={1}>
            {rival.opponent_name}
          </Text>
          <Badge label={rival.won_played_display} variant={pillVariant} />
        </Pressable>
      ) : (
        <Text style={styles.kvValue}>—</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  compactCard: {
    padding: spacing.md,
  },
  playerName: {
    fontSize: 26,
    fontWeight: "800",
    color: colors.text,
  },
  headerMeta: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 4,
  },
  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
    marginTop: spacing.sm,
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
    flexBasis: "15%",
    flexGrow: 1,
  },
  kpiLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.4,
  },
  kpiValue: {
    fontSize: 21,
    fontWeight: "800",
    color: colors.text,
    marginTop: 2,
    fontVariant: ["tabular-nums"],
  },
  kpiSub: {
    fontSize: 12,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  insightsGrid: {
    gap: spacing.lg,
  },
  insightsGridDesktop: {
    flexDirection: "row",
    alignItems: "stretch",
  },
  insightCol: {
    flex: 1,
  },
  kvRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  kvRowLast: {
    borderBottomWidth: 0,
    paddingBottom: 2,
  },
  kvLabel: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    flexShrink: 1,
  },
  kvValue: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.text,
    textAlign: "right",
    fontVariant: ["tabular-nums"],
  },
  kvSub: {
    fontWeight: "500",
    color: colors.textMuted,
  },
  kvRightWrap: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 6,
    flexShrink: 1,
  },
  formBadges: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  formBadge: {
    minWidth: 24,
    height: 24,
    paddingHorizontal: 6,
    borderRadius: radii.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  formBadgeText: {
    fontSize: 12,
    fontWeight: "800",
  },
  formWin: {
    backgroundColor: colors.courtGreen,
  },
  formWinText: {
    color: colors.white,
  },
  formRet: {
    backgroundColor: colors.incompleteBg,
  },
  formRetText: {
    color: colors.incompleteText,
  },
  formInc: {
    backgroundColor: colors.clubBlueSoft,
  },
  formIncText: {
    color: colors.navy,
  },
  formLoss: {
    backgroundColor: colors.textMuted,
  },
  formLossText: {
    color: colors.white,
  },
  rivalLink: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.linkBlue,
    flexShrink: 1,
  },
  filterInput: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    fontSize: 15,
    color: colors.text,
    backgroundColor: colors.surface,
    marginBottom: spacing.sm,
  },
  tableHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tableHeaderText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textMuted,
    textTransform: "uppercase",
  },
  colRecord: {
    width: 112,
    textAlign: "center",
  },
  colDate: {
    width: 74,
    textAlign: "right",
  },
  h2hRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  h2hTapArea: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  h2hName: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.linkBlue,
  },
  h2hRecordWrap: {
    width: 112,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  h2hRecord: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  h2hDate: {
    width: 74,
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "right",
  },
  emptyText: {
    fontSize: 14,
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
  histRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  histTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flexWrap: "wrap",
  },
  histTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.linkBlue,
  },
  histMeta: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  histRight: {
    alignItems: "flex-end",
  },
  ptsVal: {
    fontSize: 15,
    fontWeight: "800",
    color: colors.navy,
    fontVariant: ["tabular-nums"],
  },
});
