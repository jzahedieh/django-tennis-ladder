import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { apiClient, extractApiError } from "../api/client";
import { colors, radii, spacing } from "../theme/tokens";
import { Button, ErrorState, LoadingState, OutcomeBadge } from "./ui";

export interface H2HTarget {
  playerId: number;
  opponentId: number;
  title?: string;
}

export function H2HSheet({
  target,
  onClose,
}: {
  target: H2HTarget | null;
  onClose: () => void;
}) {
  const router = useRouter();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["h2h", target?.playerId, target?.opponentId],
    enabled: Boolean(target),
    queryFn: async () => {
      if (!target) throw new Error("No target");
      const { data, error } = await apiClient.GET(
        "/v1/players/{player_id}/vs/{opponent_id}/",
        {
          params: {
            path: {
              player_id: target.playerId,
              opponent_id: target.opponentId,
            },
          },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load head-to-head."));
      }
      return data;
    },
  });

  if (!target) return null;

  return (
    <Modal
      visible={Boolean(target)}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.eyebrow}>HEAD-TO-HEAD</Text>
              <Text style={styles.title} numberOfLines={2}>
                {data
                  ? `${data.player_name} vs ${data.opponent_name}`
                  : target.title || "Matchup History"}
              </Text>
            </View>
            <Pressable onPress={onClose} hitSlop={10} style={styles.closeBtn}>
              <Ionicons name="close" size={20} color={colors.textSecondary} />
            </Pressable>
          </View>

          <ScrollView style={styles.body} contentContainerStyle={{ gap: spacing.md }}>
            {isLoading ? <LoadingState label="Loading matchup..." /> : null}
            {error ? (
              <ErrorState
                message={(error as Error).message}
                onRetry={() => void refetch()}
              />
            ) : null}

            {data ? (
              <>
                <View style={styles.summaryRow}>
                  <View style={styles.playerCol}>
                    <Text style={styles.playerCount}>{data.stats.won}</Text>
                    <Text style={styles.playerLabel} numberOfLines={1}>
                      {data.player_name}
                    </Text>
                  </View>
                  <View style={styles.centerCol}>
                    <Text style={styles.playedCount}>{data.stats.played}</Text>
                    <Text style={styles.playedLabel}>MATCHES</Text>
                  </View>
                  <View style={styles.playerCol}>
                    <Text style={styles.playerCount}>{data.stats.lost}</Text>
                    <Text style={styles.playerLabel} numberOfLines={1}>
                      {data.opponent_name}
                    </Text>
                  </View>
                </View>

                <View style={styles.barTrack}>
                  <View
                    style={[
                      styles.barLeft,
                      {
                        flex: Math.max(data.stats.player_win_pct, data.stats.played ? 1 : 50),
                      },
                    ]}
                  />
                  <View
                    style={[
                      styles.barRight,
                      {
                        flex: Math.max(data.stats.opponent_win_pct, data.stats.played ? 1 : 50),
                      },
                    ]}
                  />
                </View>

                <View style={styles.metaStrip}>
                  <Text style={styles.metaText}>
                    Games: {data.stats.player_games} – {data.stats.opponent_games}
                  </Text>
                  <Text style={styles.metaText}>
                    Close (9–7 / 9–8): {data.stats.close_matches}
                  </Text>
                </View>

                {data.matches.length === 0 ? (
                  <Text style={styles.noMatches}>
                    No previous ladder matches played between these players.
                  </Text>
                ) : (
                  <View style={styles.matchList}>
                    {data.matches.slice(0, 6).map((m, idx) => (
                      <View key={`${m.date_added}-${idx}`} style={styles.matchRow}>
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
                          <Text style={styles.matchScore}>
                            {m.winner_name} def. {m.loser_name} ({m.score_display})
                          </Text>
                          <Text style={styles.matchMeta}>
                            {m.ladder_short} · {m.date_added}
                          </Text>
                        </View>
                      </View>
                    ))}
                  </View>
                )}

                <View style={styles.footerActions}>
                  <Button
                    label="Full Head-to-Head →"
                    variant="secondary"
                    size="sm"
                    onPress={() => {
                      onClose();
                      router.push(
                        `/head_to_head/${target.playerId}/vs/${target.opponentId}`
                      );
                    }}
                    style={{ flex: 1 }}
                  />
                  <Button
                    label="Close"
                    variant="outline"
                    size="sm"
                    onPress={onClose}
                  />
                </View>
              </>
            ) : null}
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.55)",
    justifyContent: "center",
    alignItems: "center",
    padding: spacing.lg,
  },
  sheet: {
    width: "100%",
    maxWidth: 520,
    maxHeight: "85%",
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    overflow: "hidden",
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: spacing.md,
  },
  eyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: colors.text,
    marginTop: 2,
  },
  closeBtn: {
    padding: 4,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
  },
  body: {
    padding: spacing.lg,
  },
  summaryRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    padding: spacing.md,
  },
  playerCol: {
    flex: 1,
    alignItems: "center",
  },
  playerCount: {
    fontSize: 28,
    fontWeight: "800",
    color: colors.navy,
  },
  playerLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
    marginTop: 2,
  },
  centerCol: {
    alignItems: "center",
    paddingHorizontal: spacing.md,
  },
  playedCount: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.text,
  },
  playedLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textMuted,
  },
  barTrack: {
    flexDirection: "row",
    height: 8,
    borderRadius: radii.pill,
    overflow: "hidden",
    backgroundColor: colors.border,
  },
  barLeft: {
    backgroundColor: colors.courtGreen,
  },
  barRight: {
    backgroundColor: colors.clubBlue,
  },
  metaStrip: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  metaText: {
    fontSize: 14,
    color: colors.textMuted,
    fontWeight: "600",
  },
  noMatches: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.lg,
  },
  matchList: {
    gap: spacing.sm,
  },
  matchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  matchScore: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
  matchMeta: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  footerActions: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.sm,
    marginBottom: spacing.lg,
  },
});
