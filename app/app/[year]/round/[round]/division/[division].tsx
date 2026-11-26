import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../../../../src/api/client";
import { useAuth } from "../../../../../src/auth/AuthContext";
import { H2HSheet, type H2HTarget } from "../../../../../src/components/H2HSheet";
import { LadderCrossTable } from "../../../../../src/components/LadderCrossTable";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  LoadingState,
  OutcomeBadge,
  PageScroll,
  SectionHeader,
} from "../../../../../src/components/ui";
import { colors, radii, spacing, useResponsive } from "../../../../../src/theme/tokens";
import { formatDateRange } from "../../../../../src/utils/dates";

function paramNum(v: string | string[] | undefined): number {
  const s = Array.isArray(v) ? v[0] : v;
  return Number(s || 0);
}

export default function DivisionDetailScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{
    year: string;
    round: string;
    division: string;
  }>();

  const year = paramNum(params.year);
  const seasonRound = paramNum(params.round);
  const divisionId = paramNum(params.division);
  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);
  const [subNotice, setSubNotice] = useState<string | null>(null);

  const queryKey = [
    "division-detail",
    year,
    seasonRound,
    divisionId,
    user?.id ?? "anon",
  ];

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    enabled: year > 0 && seasonRound > 0 && divisionId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/v1/ladder/seasons/{year}/round/{season_round}/division/{division_id}/",
        {
          params: {
            path: {
              year,
              season_round: seasonRound,
              division_id: divisionId,
            },
          },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Division not found."));
      }
      return data;
    },
  });

  const subMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST(
        "/v1/ladder/seasons/{year}/round/{season_round}/division/{division_id}/subscription/",
        {
          params: {
            path: {
              year,
              season_round: seasonRound,
              division_id: divisionId,
            },
          },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not update subscription."));
      }
      return data;
    },
    onSuccess: (res) => {
      setSubNotice(res.detail);
      void queryClient.invalidateQueries({ queryKey });
      void queryClient.invalidateQueries({ queryKey: ["account"] });
    },
  });

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading division..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load division."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  const { season, stats, grid, recent_results } = data;
  const dateRange = formatDateRange(season.start_date, season.end_date);

  const headerBody = (
    <View style={[styles.headerRow, !isDesktop && styles.headerRowMobile]}>
      <View style={isDesktop ? styles.headerLeftDesktop : undefined}>
        {isDesktop ? (
          <>
            <Text style={styles.titleDesktop}>
              <Text
                onPress={() => router.push(`/${year}/round/${seasonRound}`)}
                style={styles.roundBreadcrumb}
              >
                {season.year} Round {season.season_round}
              </Text>
              {" - Division: "}
              {data.division}
            </Text>
            <Text style={styles.subtitleDesktop}>{dateRange}</Text>
          </>
        ) : (
          <>
            <Pressable
              onPress={() => router.push(`/${year}/round/${seasonRound}`)}
            >
              <Text style={styles.eyebrow}>{season.name}</Text>
            </Pressable>
            <Text style={styles.title}>Division {data.division}</Text>
            <Text style={styles.subtitleMobile}>{dateRange}</Text>
            <View style={styles.badgeRow}>
              {data.ladder_type ? <Badge label={data.ladder_type} /> : null}
              <Badge label={`${stats.players_count} Players`} />
              {data.is_closed ? (
                <Badge label="Round Closed" variant="amber" />
              ) : (
                <Badge label="Open" variant="green" />
              )}
            </View>
          </>
        )}
      </View>

      <View
        style={[
          styles.rightControls,
          !isDesktop && styles.rightControlsMobile,
        ]}
      >
        <View style={styles.navBtns}>
          {data.has_prev_division ? (
            <Button
              label={`← Div ${data.division - 1}`}
              variant="outline"
              size="sm"
              onPress={() =>
                router.replace(
                  `/${year}/round/${seasonRound}/division/${data.division - 1}`
                )
              }
            />
          ) : null}
          {data.has_next_division ? (
            <Button
              label={`Div ${data.division + 1} →`}
              variant="outline"
              size="sm"
              onPress={() =>
                router.replace(
                  `/${year}/round/${seasonRound}/division/${data.division + 1}`
                )
              }
            />
          ) : null}
          {user ? (
            <Button
              label={data.subscribed ? "Unsubscribe" : "Subscribe"}
              variant={data.subscribed ? "outline" : "secondary"}
              size="sm"
              loading={subMutation.isPending}
              onPress={() => subMutation.mutate()}
            />
          ) : null}
        </View>
        {subNotice ? <Text style={styles.subNotice}>{subNotice}</Text> : null}
      </View>
    </View>
  );

  return (
    <PageScroll desktopClean={isDesktop}>
      {isDesktop ? (
        <View style={styles.desktopHeader}>{headerBody}</View>
      ) : (
        <Card>{headerBody}</Card>
      )}

      {/* Cross Table */}
      {isDesktop ? (
        <LadderCrossTable grid={grid} onPressCell={setH2HTarget} />
      ) : (
        <Card>
          <SectionHeader
            title="Division Table"
            subtitle="Tap any player for profile or any score cell for Head-to-Head"
          />
          <LadderCrossTable grid={grid} onPressCell={setH2HTarget} />
        </Card>
      )}

      {/* Division Stats */}
      <Card>
        <SectionHeader
          title={`Division ${data.division} Stats`}
          subtitle={`${stats.total_matches_played} of ${stats.total_matches} matches played (${stats.matches_remaining} remaining)`}
          right={
            <Badge
              label={`${stats.perc_matches_played.toFixed(1)}%`}
              variant="green"
            />
          }
        />

        <View style={styles.progressTrack}>
          <View
            style={[
              styles.progressFill,
              { width: `${Math.min(100, stats.perc_matches_played)}%` },
            ]}
          />
        </View>

        <View style={styles.kpiGrid}>
          <View style={styles.kpiBox}>
            <Text style={styles.kpiLabel}>CURRENT LEADER</Text>
            <Text style={styles.kpiValue}>
              {stats.leader ? stats.leader.player_name : "No matches yet"}
            </Text>
            {stats.leader ? (
              <Text style={styles.kpiSub}>
                {stats.leader.total} pts · Avg {stats.leader.avg}
              </Text>
            ) : null}
          </View>

          <View style={styles.kpiBox}>
            <Text style={styles.kpiLabel}>AVG MATCH SCORE</Text>
            <Text style={styles.kpiValue}>{stats.avg_match_score ?? "—"}</Text>
            <Text style={styles.kpiSub}>
              {stats.avg_games_per_match
                ? `${stats.avg_games_per_match} games/match (${stats.total_games_played} total)`
                : "No completed matches"}
            </Text>
          </View>

          <View style={styles.kpiBox}>
            <Text style={styles.kpiLabel}>CLOSE MATCHES (9–7 / 9–8)</Text>
            <Text style={styles.kpiValue}>
              {stats.close_matches_count} ({stats.close_matches_pct.toFixed(0)}%)
            </Text>
            <Text style={styles.kpiSub}>Decided by 1–2 games</Text>
          </View>
        </View>
      </Card>

      {/* Latest Results */}
      <Card>
        <SectionHeader
          title="Latest Results"
          subtitle={`${recent_results.length} matches`}
        />
        {recent_results.length === 0 ? (
          <Text style={styles.emptyText}>
            No matches recorded yet for this division.
          </Text>
        ) : (
          recent_results.map((m, idx) => (
            <View
              key={`${m.winner_id}-${m.loser_id}-${idx}`}
              style={styles.resultRow}
            >
              <OutcomeBadge
                code={m.is_incomplete ? "I" : m.is_injury ? "R" : "W"}
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.resultLine} numberOfLines={1}>
                  <Text
                    onPress={() => router.push(`/player/${m.winner_id}`)}
                    style={styles.playerLink}
                  >
                    {m.winner_name}
                  </Text>{" "}
                  <Text style={{ color: colors.textMuted }}>vs</Text>{" "}
                  <Text
                    onPress={() => router.push(`/player/${m.loser_id}`)}
                    style={styles.playerLink}
                  >
                    {m.loser_name}
                  </Text>
                </Text>
                <Text style={styles.resultDate}>{m.date_display}</Text>
              </View>
              <Pressable
                onPress={() =>
                  setH2HTarget({
                    playerId: m.winner_id,
                    opponentId: m.loser_id,
                    title: `${m.winner_name} vs ${m.loser_name}`,
                  })
                }
                style={styles.scorePill}
              >
                <Text style={styles.scorePillText}>{m.score_display}</Text>
              </Pressable>
            </View>
          ))
        )}
      </Card>

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  desktopHeader: {
    paddingBottom: spacing.xs,
  },
  headerRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  headerRowMobile: {
    flexDirection: "column",
    alignItems: "stretch",
  },
  headerLeftDesktop: {
    flex: 1,
    minWidth: 260,
  },
  eyebrow: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.linkBlue,
  },
  title: {
    fontSize: 25,
    fontWeight: "800",
    color: colors.text,
    marginTop: 2,
  },
  titleDesktop: {
    fontSize: 32,
    fontWeight: "700",
    color: colors.text,
    letterSpacing: -0.3,
  },
  roundBreadcrumb: {
    color: colors.text,
  },
  subtitleMobile: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  subtitleDesktop: {
    fontSize: 17,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 4,
  },
  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  rightControls: {
    alignItems: "flex-end",
    gap: spacing.xs,
  },
  rightControlsMobile: {
    alignItems: "flex-start",
  },
  navBtns: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  subNotice: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.courtGreen,
  },
  progressTrack: {
    height: 8,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.pill,
    overflow: "hidden",
    marginBottom: spacing.md,
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.courtGreen,
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  kpiBox: {
    flex: 1,
    minWidth: 180,
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
    fontSize: 19,
    fontWeight: "800",
    color: colors.navy,
    marginTop: 4,
  },
  kpiSub: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textSecondary,
    marginTop: 2,
  },
  emptyText: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
  resultRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  resultLine: {
    fontSize: 16,
    fontWeight: "500",
    color: colors.text,
  },
  playerLink: {
    fontWeight: "700",
    color: colors.linkBlue,
  },
  resultDate: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  scorePill: {
    backgroundColor: colors.courtGreenSoft,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: radii.pill,
  },
  scorePillText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.courtGreen,
  },
});
