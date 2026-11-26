import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../../../src/api/client";
import { useAuth } from "../../../../src/auth/AuthContext";
import {
  Badge,
  Card,
  ErrorState,
  LoadingState,
  OutcomeBadge,
  PageScroll,
  SectionHeader,
} from "../../../../src/components/ui";
import { colors, radii, spacing } from "../../../../src/theme/tokens";

function paramNum(v: string | string[] | undefined): number {
  const s = Array.isArray(v) ? v[0] : v;
  return Number(s || 0);
}

export default function HeadToHeadScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const params = useLocalSearchParams<{
    playerId: string;
    opponentId: string;
  }>();
  const playerId = paramNum(params.playerId);
  const opponentId = paramNum(params.opponentId);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["h2h", playerId, opponentId, user?.id ?? "anon"],
    enabled: playerId > 0 && opponentId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/v1/players/{player_id}/vs/{opponent_id}/",
        {
          params: {
            path: { player_id: playerId, opponent_id: opponentId },
          },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load matchup."));
      }
      return data;
    },
  });

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading head-to-head..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Head-to-head not found."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  return (
    <PageScroll>
      <Card>
        <Text style={styles.eyebrow}>HEAD-TO-HEAD HISTORY</Text>
        <View style={styles.matchupHeader}>
          <Pressable
            onPress={() => router.push(`/player/${data.player_id}`)}
            style={styles.playerBox}
          >
            <Text style={styles.bigCount}>{data.stats.won}</Text>
            <Text style={styles.playerLink}>{data.player_name}</Text>
            <Text style={styles.pct}>{data.stats.player_win_pct}%</Text>
          </Pressable>

          <View style={styles.vsBox}>
            <Text style={styles.vsText}>VS</Text>
            <Text style={styles.totalText}>{data.stats.played} played</Text>
          </View>

          <Pressable
            onPress={() => router.push(`/player/${data.opponent_id}`)}
            style={styles.playerBox}
          >
            <Text style={styles.bigCount}>{data.stats.lost}</Text>
            <Text style={styles.playerLink}>{data.opponent_name}</Text>
            <Text style={styles.pct}>{data.stats.opponent_win_pct}%</Text>
          </Pressable>
        </View>

        <View style={styles.metaRow}>
          <Badge label={`Games ${data.stats.player_games}–${data.stats.opponent_games}`} />
          <Badge label={`Close matches: ${data.stats.close_matches}`} variant="blue" />
          {data.stats.incomplete > 0 ? (
            <Badge label={`Incomplete: ${data.stats.incomplete}`} variant="amber" />
          ) : null}
        </View>
      </Card>

      <Card>
        <SectionHeader
          title="All Matches"
          subtitle={
            data.stats.first_played
              ? `${data.stats.first_played} to ${data.stats.last_played}`
              : undefined
          }
        />
        {data.matches.length === 0 ? (
          <Text style={styles.empty}>No matches recorded yet.</Text>
        ) : (
          data.matches.map((m, idx) => (
            <Pressable
              key={`${m.date_added}-${idx}`}
              onPress={() =>
                router.push(
                  `/${m.year}/round/${m.season_round}/division/${m.division}`
                )
              }
              style={styles.matchRow}
            >
              <OutcomeBadge
                code={
                  m.is_incomplete
                    ? "I"
                    : m.player_won
                    ? "W"
                    : m.is_injury
                    ? "R"
                    : "L"
                }
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.matchTitle}>
                  {m.winner_name} def. {m.loser_name}
                </Text>
                <Text style={styles.matchMeta}>
                  {m.ladder_full} · {m.date_added}
                </Text>
              </View>
              <Badge label={m.score_display} variant={m.is_close ? "green" : "neutral"} />
            </Pressable>
          ))
        )}
      </Card>
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  eyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: spacing.sm,
  },
  matchupHeader: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    padding: spacing.lg,
    gap: spacing.md,
  },
  playerBox: {
    flex: 1,
    alignItems: "center",
  },
  bigCount: {
    fontSize: 34,
    fontWeight: "800",
    color: colors.navy,
  },
  playerLink: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.linkBlue,
    textAlign: "center",
    marginTop: 2,
  },
  pct: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textMuted,
    marginTop: 2,
  },
  vsBox: {
    alignItems: "center",
  },
  vsText: {
    fontSize: 15,
    fontWeight: "800",
    color: colors.textMuted,
  },
  totalText: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textMuted,
    marginTop: 2,
  },
  metaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  matchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 11,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  matchTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
  },
  matchMeta: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  empty: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
});
