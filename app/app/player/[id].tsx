import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import { useAuth } from "../../src/auth/AuthContext";
import { CentileHistoryChart } from "../../src/components/CentileHistoryChart";
import { H2HSheet, type H2HTarget } from "../../src/components/H2HSheet";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  LoadingState,
  OutcomeBadge,
  PageScroll,
  SectionHeader,
} from "../../src/components/ui";
import { colors, radii, spacing } from "../../src/theme/tokens";

function paramNum(v: string | string[] | undefined): number {
  const s = Array.isArray(v) ? v[0] : v;
  return Number(s || 0);
}

export default function PlayerProfileScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const params = useLocalSearchParams<{ id: string }>();
  const playerId = paramNum(params.id);

  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);
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

  return (
    <PageScroll>
      {/* Header */}
      <Card>
        <Text style={styles.eyebrow}>PLAYER PROFILE</Text>
        <Text style={styles.playerName}>{data.player_name}</Text>
        <View style={styles.badgeRow}>
          <Badge label={`${stats.seasons_played} Rounds`} variant="navy" />
          <Badge label={`Best Div ${stats.highest_division}`} variant="blue" />
          <Badge label={`Peak ${stats.best_centile}`} variant="green" />
          {stats.divisions_won_badges.map((b) => (
            <Badge
              key={b.division}
              label={`★ ${b.label}`}
              variant={b.is_div1 ? "amber" : "green"}
            />
          ))}
        </View>
      </Card>

      {/* Career KPI Grid */}
      <Card>
        <SectionHeader title="Career Statistics" />
        <View style={styles.kpiGrid}>
          <KpiTile label="Played" value={String(stats.played)} />
          <KpiTile label="Won / Lost" value={`${stats.won} / ${stats.lost}`} />
          <KpiTile label="Win Rate" value={stats.win_rate} />
          <KpiTile label="Completion" value={stats.completion_rate} />
          <KpiTile label="Avg Pts" value={stats.average} />
          <KpiTile label="Avg Centile" value={stats.avg_centile} />
        </View>
      </Card>

      {/* Centile Chart */}
      {centile_chart_data.length > 0 ? (
        <Card>
          <SectionHeader
            title="Club Centile Standing"
            subtitle="Percentage of club players finished ahead of (100% = Division 1 Winner)"
          />
          <CentileHistoryChart data={centile_chart_data} />
        </Card>
      ) : null}

      {/* Insights & Form */}
      {insights.has_matches ? (
        <Card>
          <SectionHeader title="Performance Insights" />

          <Text style={styles.subLabel}>Recent Form (Newest First)</Text>
          <View style={styles.formRow}>
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
                style={styles.formChip}
              >
                <OutcomeBadge code={m.outcome_code} />
                <Text style={styles.formScore}>{m.score_display}</Text>
                <Text style={styles.formOpp} numberOfLines={1}>
                  vs {m.opponent_name}
                </Text>
              </Pressable>
            ))}
          </View>

          <View style={styles.kpiGrid}>
            <KpiTile
              label="Win Streak (Curr / Best)"
              value={`${insights.current_win_streak} / ${insights.longest_win_streak}`}
            />
            <KpiTile
              label="Clutch (9–7 / 9–8)"
              value={`${insights.clutch_won}/${insights.clutch_played} (${insights.clutch_win_rate})`}
            />
            <KpiTile
              label="Games Won %"
              value={insights.games_win_rate}
            />
            <KpiTile
              label="Best Round"
              value={
                insights.best_round_label
                  ? `${insights.best_round_points} pts`
                  : "—"
              }
            />
          </View>

          {(insights.most_played_rival ||
            insights.favourite_rival ||
            insights.toughest_rival) ? (
            <View style={styles.rivalsWrap}>
              {insights.most_played_rival ? (
                <RivalChip
                  label="Most Played Rival"
                  rival={insights.most_played_rival}
                  onPress={() =>
                    setH2HTarget({
                      playerId,
                      opponentId: insights.most_played_rival!.opponent_id,
                    })
                  }
                />
              ) : null}
              {insights.favourite_rival ? (
                <RivalChip
                  label="Favourite Matchup"
                  rival={insights.favourite_rival}
                  onPress={() =>
                    setH2HTarget({
                      playerId,
                      opponentId: insights.favourite_rival!.opponent_id,
                    })
                  }
                />
              ) : null}
              {insights.toughest_rival ? (
                <RivalChip
                  label="Toughest Rival"
                  rival={insights.toughest_rival}
                  onPress={() =>
                    setH2HTarget({
                      playerId,
                      opponentId: insights.toughest_rival!.opponent_id,
                    })
                  }
                />
              ) : null}
            </View>
          ) : null}
        </Card>
      ) : null}

      {/* Head-to-Head Summary */}
      {head_to_head.length > 0 ? (
        <Card>
          <SectionHeader
            title="Head-to-Head Records"
            subtitle={`${stats.unique_opponents} opponents`}
          />
          {head_to_head.slice(0, h2hLimit).map((h) => (
            <Pressable
              key={h.opponent_id}
              onPress={() =>
                setH2HTarget({
                  playerId,
                  opponentId: h.opponent_id,
                  title: `${data.player_name} vs ${h.opponent_name}`,
                })
              }
              style={styles.row}
            >
              <Text style={styles.rowPrimary} numberOfLines={1}>
                {h.opponent_name}
              </Text>
              <Text style={styles.rowMeta}>
                {h.won_played_display} ({h.win_rate_display})
              </Text>
              <Badge label="H2H" variant="blue" />
            </Pressable>
          ))}
          {head_to_head.length > h2hLimit ? (
            <Button
              label="Show More Opponents"
              variant="outline"
              size="sm"
              onPress={() => setH2hLimit((p) => p + 15)}
              style={{ marginTop: spacing.md }}
            />
          ) : null}
        </Card>
      ) : null}

      {/* Season History */}
      {season_history.length > 0 ? (
        <Card>
          <SectionHeader title="Ladder History" />
          {season_history.slice(0, histLimit).map((item) => (
            <Pressable
              key={item.league_id}
              onPress={() =>
                router.push(
                  `/${item.year}/round/${item.season_round}/division/${item.division}`
                )
              }
              style={styles.row}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.rowPrimary}>
                  {item.season_name} · Div {item.division}{" "}
                  {item.is_division_winner ? "★" : ""}
                </Text>
                <Text style={styles.rowMeta}>
                  {item.games}/{item.scheduled_matches} played ({item.pct_played}%) ·{" "}
                  Avg {item.points_per_game.toFixed(2)}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={styles.ptsVal}>{item.total_points} pts</Text>
                {item.centile !== null && item.centile !== undefined ? (
                  <Text style={styles.rowMeta}>{item.centile}% centile</Text>
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

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

function KpiTile({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.kpiBox}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiValue}>{value}</Text>
    </View>
  );
}

function RivalChip({
  label,
  rival,
  onPress,
}: {
  label: string;
  rival: { opponent_name: string; won_played_display: string; win_rate_display: string };
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={styles.rivalCard}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.rivalName} numberOfLines={1}>
        {rival.opponent_name}
      </Text>
      <Text style={styles.rivalSub}>
        {rival.won_played_display} ({rival.win_rate_display})
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  eyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.8,
  },
  playerName: {
    fontSize: 28,
    fontWeight: "800",
    color: colors.text,
    marginTop: 2,
  },
  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  kpiBox: {
    flexGrow: 1,
    minWidth: 130,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  kpiLabel: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
  },
  kpiValue: {
    fontSize: 20,
    fontWeight: "800",
    color: colors.navy,
    marginTop: 2,
  },
  subLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  formRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  formChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radii.md,
    maxWidth: "100%",
  },
  formScore: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.text,
  },
  formOpp: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    maxWidth: 130,
  },
  rivalsWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  rivalCard: {
    flex: 1,
    minWidth: 150,
    backgroundColor: colors.clubBlueSoft,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  rivalName: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.navy,
    marginTop: 2,
  },
  rivalSub: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textSecondary,
    marginTop: 2,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 11,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  rowPrimary: {
    flex: 1,
    fontSize: 16,
    fontWeight: "700",
    color: colors.navy,
  },
  rowMeta: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
  },
  ptsVal: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.navy,
  },
});
