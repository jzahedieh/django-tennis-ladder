import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import { useAuth } from "../../src/auth/AuthContext";
import { H2HSheet, type H2HTarget } from "../../src/components/H2HSheet";
import { SeasonProgressChart } from "../../src/components/SeasonProgressChart";
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
import { colors, radii, spacing, useResponsive } from "../../src/theme/tokens";
import { formatDateRange } from "../../src/utils/dates";

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { isDesktop } = useResponsive();
  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);
  const [resultsLimit, setResultsLimit] = useState(15);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["current-overview", user?.id ?? "anon"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/v1/ladder/seasons/current/overview"
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Failed to load current round."));
      }
      return data;
    },
  });

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading Highgate Ladder..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load overview."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  const { season, stats, leaders, progress, recent_results, my_division } = data;
  const visibleResults = recent_results.slice(0, resultsLimit);

  return (
    <PageScroll>
      {/* My Division Hero when signed in and enrolled */}
      {my_division ? (
        <Card style={styles.myDivCard}>
          <View style={styles.myDivRow}>
            <View style={{ flex: 1, minWidth: 200 }}>
              <Text style={styles.myDivEyebrow}>YOUR ACTIVE DIVISION</Text>
              <Text style={styles.myDivTitle}>
                Division {my_division.division} · {season.name}
              </Text>
              <Text style={styles.myDivMeta}>
                Rank #{my_division.rank_in_division} of{" "}
                {my_division.division_size} · {my_division.total_points} pts ·{" "}
                {my_division.matches_played}/{my_division.total_opponents} played
              </Text>
            </View>
            <View style={styles.myDivActions}>
              {!my_division.is_closed ? (
                <Button
                  label="Enter Score"
                  size="sm"
                  onPress={() => router.push("/enter")}
                />
              ) : null}
              <Button
                label="View Table"
                size="sm"
                variant="outline"
                onPress={() =>
                  router.push(
                    `/${season.year}/round/${season.season_round}/division/${my_division.division}`
                  )
                }
              />
            </View>
          </View>
        </Card>
      ) : !user ? (
        <Card style={styles.guestBanner}>
          <View style={styles.myDivRow}>
            <View style={{ flex: 1, minWidth: 200 }}>
              <Text style={styles.guestTitle}>Highgate CLTC Ladder</Text>
              <Text style={styles.guestSub}>
                Sign in to record match results, track your division, and view
                full player names.
              </Text>
            </View>
            <Button
              label="Log In"
              variant="secondary"
              size="sm"
              onPress={() => router.push("/login")}
            />
          </View>
        </Card>
      ) : null}

      {/* Season Progress Hero */}
      <Card>
        <SectionHeader
          title={`${season.name} Progress`}
          subtitle={formatDateRange(season.start_date, season.end_date)}
          right={
            <Pressable
              onPress={() => router.push(`/stats?season=${season.id}`)}
            >
              <Badge label="Round Stats →" variant="blue" />
            </Pressable>
          }
        />

        <View style={styles.kpiRow}>
          <Badge label={`${stats.divisions} Divisions`} />
          <Badge label={`${stats.player_count} Players`} />
          <Badge
            label={`${stats.results_count} / ${stats.total_games_count} Matches (${stats.percentage_played}%)`}
            variant="green"
          />
          {season.is_closed ? <Badge label="Round Closed" variant="amber" /> : null}
        </View>

        <SeasonProgressChart progress={progress} />
      </Card>

      {/* Leaders + Recent Results two-column on desktop, stacked on mobile */}
      <View style={[styles.splitGrid, isDesktop && styles.splitGridDesktop]}>
        <Card style={isDesktop ? styles.colLeft : undefined}>
          <SectionHeader
            title="Division Leaders"
            right={
              <Pressable onPress={() => router.push("/ladder")}>
                <Text style={styles.linkText}>All Grids →</Text>
              </Pressable>
            }
          />
          <View style={styles.list}>
            {leaders.map((leader) => (
              <View key={leader.division} style={styles.leaderRow}>
                <Pressable
                  onPress={() =>
                    router.push(
                      `/${season.year}/round/${season.season_round}/division/${leader.division}`
                    )
                  }
                  style={styles.divPill}
                >
                  <Text style={styles.divPillText}>Div {leader.division}</Text>
                </Pressable>
                <Pressable
                  disabled={!leader.player_id}
                  onPress={() => {
                    if (leader.player_id) {
                      router.push(`/player/${leader.player_id}`);
                    }
                  }}
                  style={{ flex: 1 }}
                >
                  <Text
                    style={[
                      styles.leaderName,
                      !leader.player_id && styles.mutedName,
                    ]}
                    numberOfLines={1}
                  >
                    {leader.player}
                  </Text>
                </Pressable>
                <Text style={styles.leaderPts}>{String(leader.total)} pts</Text>
                <Text style={styles.leaderPct}>{leader.played.toFixed(0)}%</Text>
              </View>
            ))}
          </View>
        </Card>

        <Card style={isDesktop ? styles.colRight : undefined}>
          <SectionHeader
            title="Latest Results"
            subtitle={`Most recent ${recent_results.length} matches`}
          />
          {visibleResults.length === 0 ? (
            <Text style={styles.emptyMsg}>No matches recorded in this round yet.</Text>
          ) : (
            <View style={styles.list}>
              {visibleResults.map((m, idx) => (
                <View
                  key={`${m.winner_id}-${m.loser_id}-${idx}`}
                  style={styles.resultRow}
                >
                  <OutcomeBadge
                    code={m.is_incomplete ? "I" : m.is_injury ? "R" : "W"}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.resultPlayers} numberOfLines={1}>
                      <Text
                        onPress={() => router.push(`/player/${m.winner_id}`)}
                        style={styles.playerLink}
                      >
                        {m.winner_name}
                      </Text>{" "}
                      <Text style={styles.vsWord}>vs</Text>{" "}
                      <Text
                        onPress={() => router.push(`/player/${m.loser_id}`)}
                        style={styles.playerLink}
                      >
                        {m.loser_name}
                      </Text>
                    </Text>
                    <Text style={styles.resultMeta}>
                      Div {m.division} · {m.date_display}
                    </Text>
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
              ))}
            </View>
          )}

          {recent_results.length > resultsLimit ? (
            <Button
              label="Show More Results"
              variant="outline"
              size="sm"
              onPress={() => setResultsLimit((prev) => prev + 15)}
              style={{ marginTop: spacing.md }}
            />
          ) : null}
        </Card>
      </View>

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  myDivCard: {
    backgroundColor: colors.navy,
    borderColor: colors.navyDark,
  },
  myDivRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  myDivEyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.clubBlue,
    letterSpacing: 0.8,
  },
  myDivTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: colors.white,
    marginTop: 2,
  },
  myDivMeta: {
    fontSize: 15,
    fontWeight: "500",
    color: "#E2E8F0",
    marginTop: 4,
  },
  myDivActions: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  guestBanner: {
    backgroundColor: colors.clubBlueSoft,
    borderColor: colors.clubBlue,
  },
  guestTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: colors.navyDark,
  },
  guestSub: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textSecondary,
    marginTop: 2,
  },
  kpiRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  splitGrid: {
    gap: spacing.lg,
  },
  splitGridDesktop: {
    flexDirection: "row",
    alignItems: "flex-start",
  },
  colLeft: {
    flex: 5,
  },
  colRight: {
    flex: 6,
  },
  linkText: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.navy,
  },
  list: {
    gap: 2,
  },
  leaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  divPill: {
    backgroundColor: colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.sm,
    minWidth: 64,
    alignItems: "center",
  },
  divPillText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.navy,
  },
  leaderName: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
  },
  mutedName: {
    color: colors.textMuted,
    fontWeight: "500",
  },
  leaderPts: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.navy,
    fontVariant: ["tabular-nums"],
  },
  leaderPct: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textMuted,
    width: 44,
    textAlign: "right",
    fontVariant: ["tabular-nums"],
  },
  resultRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  resultPlayers: {
    fontSize: 16,
    fontWeight: "500",
    color: colors.text,
  },
  playerLink: {
    fontWeight: "700",
    color: colors.navy,
  },
  vsWord: {
    color: colors.textMuted,
  },
  resultMeta: {
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
  emptyMsg: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    paddingVertical: spacing.lg,
    textAlign: "center",
  },
});
