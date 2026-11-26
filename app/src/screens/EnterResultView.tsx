import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../api/client";
import type { EnteredMatchOut } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { H2HSheet, type H2HTarget } from "../components/H2HSheet";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  OutcomeBadge,
  PageScroll,
  SectionHeader,
} from "../components/ui";
import { colors, radii, spacing } from "../theme/tokens";

const SCORE_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8];

export function EnterResultView() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isHydrating } = useAuth();

  const [selectedOpponentId, setSelectedOpponentId] = useState<number | null>(
    null
  );
  const [outcome, setOutcome] = useState<"won" | "lost" | "incomplete">("won");
  const [incompleteReason, setIncompleteReason] = useState<"time" | "injury">(
    "time"
  );
  const [injuredPlayer, setInjuredPlayer] = useState<"opponent" | "me">(
    "opponent"
  );
  const [primaryScore, setPrimaryScore] = useState<number>(4);
  const [opponentScore, setOpponentScore] = useState<number>(4);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);
  const [editingMatch, setEditingMatch] = useState<EnteredMatchOut | null>(null);
  const [deletingMatch, setDeletingMatch] = useState<EnteredMatchOut | null>(
    null
  );

  // Edit modal state
  const [editMode, setEditMode] = useState<"completed" | "time" | "injury">(
    "completed"
  );
  const [editWinnerId, setEditWinnerId] = useState<number>(0);
  const [editMyScore, setEditMyScore] = useState<number>(4);
  const [editLosingScore, setEditLosingScore] = useState<number>(4);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["result-entry", user?.id ?? "anon"],
    enabled: Boolean(user),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/v1/ladder/results/entry/");
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load entry form."));
      }
      return data;
    },
  });

  const invalidateLadderCaches = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["result-entry"] }),
      queryClient.invalidateQueries({ queryKey: ["current-overview"] }),
      queryClient.invalidateQueries({ queryKey: ["season-detail"] }),
      queryClient.invalidateQueries({ queryKey: ["division-detail"] }),
      queryClient.invalidateQueries({ queryKey: ["club-stats"] }),
    ]);
  };

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!selectedOpponentId) {
        throw new Error("Please select an opponent first.");
      }
      const { data: res, error } = await apiClient.POST(
        "/v1/ladder/results/entry/",
        {
          body: {
            opponent_id: selectedOpponentId,
            outcome,
            primary_score: primaryScore,
            opponent_score:
              outcome === "incomplete" && incompleteReason === "time"
                ? opponentScore
                : null,
            incomplete_reason:
              outcome === "incomplete" ? incompleteReason : null,
            injured_player:
              outcome === "incomplete" && incompleteReason === "injury"
                ? injuredPlayer
                : null,
          },
        }
      );
      if (error || !res) {
        throw new Error(extractApiError(error, "Failed to save result."));
      }
      return res;
    },
    onSuccess: async (res) => {
      setSelectedOpponentId(null);
      setOutcome("won");
      setPrimaryScore(4);
      setOpponentScore(4);
      setFeedback({ type: "success", text: res.detail });
      await invalidateLadderCaches();
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", text: err.message });
    },
  });

  const editMutation = useMutation({
    mutationFn: async () => {
      if (!editingMatch) throw new Error("No match selected");
      const { data: res, error } = await apiClient.PUT(
        "/v1/ladder/results/entry/{pair_key}/",
        {
          params: { path: { pair_key: editingMatch.pair_key } },
          body:
            editMode === "time"
              ? {
                  match_mode: "time",
                  winner_score: editMyScore,
                  losing_score: editLosingScore,
                }
              : {
                  match_mode: editMode,
                  winner_id: editWinnerId,
                  losing_score: editLosingScore,
                },
        }
      );
      if (error || !res) {
        throw new Error(extractApiError(error, "Could not update result."));
      }
      return res;
    },
    onSuccess: async (res) => {
      setEditingMatch(null);
      setFeedback({ type: "success", text: res.detail });
      await invalidateLadderCaches();
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", text: err.message });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (pairKey: string) => {
      const { data: res, error } = await apiClient.DELETE(
        "/v1/ladder/results/entry/{pair_key}/",
        { params: { path: { pair_key: pairKey } } }
      );
      if (error || !res) {
        throw new Error(extractApiError(error, "Could not delete result."));
      }
      return res;
    },
    onSuccess: async (res) => {
      setDeletingMatch(null);
      setFeedback({ type: "success", text: res.detail });
      await invalidateLadderCaches();
    },
    onError: (err: Error) => {
      setDeletingMatch(null);
      setFeedback({ type: "error", text: err.message });
    },
  });

  const openEditModal = (m: EnteredMatchOut) => {
    setEditingMatch(m);
    if (m.is_incomplete) {
      setEditMode("time");
      setEditMyScore(m.my_score);
      setEditLosingScore(m.opp_score);
    } else {
      setEditMode(m.is_injury ? "injury" : "completed");
      setEditWinnerId(m.winner_id);
      setEditLosingScore(m.losing_score);
    }
  };

  if (isHydrating || (user && isLoading)) {
    return (
      <PageScroll>
        <LoadingState label="Loading match entry..." />
      </PageScroll>
    );
  }

  if (!user) {
    return (
      <PageScroll>
        <EmptyState
          title="Sign in to enter a match result"
          message="Record wins, losses, or incomplete matches directly from the court."
          action={
            <Button
              label="Log In"
              onPress={() => router.push("/accounts/login")}
            />
          }
        />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Unable to load result entry."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  if (!data.has_active_ladder || !data.ladder) {
    return (
      <PageScroll>
        <EmptyState
          title="No active ladder division"
          message="Your account does not currently belong to a published ladder division."
        />
      </PageScroll>
    );
  }

  const { ladder, unplayed, entered, is_closed, total_opponents, player_id } =
    data;

  const scorePromptLabel =
    outcome === "won"
      ? "3. Opponent's Score (0–8)"
      : outcome === "lost"
      ? "3. Your Score (0–8)"
      : incompleteReason === "time"
      ? "3. Your Score (0–8)"
      : injuredPlayer === "opponent"
      ? "3. Opponent's Score at Retirement (0–8)"
      : "3. Your Score at Retirement (0–8)";

  return (
    <PageScroll>
      {/* Header */}
      <Card>
        <View style={styles.headerRow}>
          <View style={{ flex: 1, minWidth: 200 }}>
            <Text style={styles.title}>Enter Result</Text>
            <Text style={styles.subtitle}>
              {ladder.season_name} · Division {ladder.division} ·{" "}
              {entered.length} of {total_opponents} played
            </Text>
          </View>
          <Button
            label="View Division →"
            variant="outline"
            size="sm"
            onPress={() =>
              router.push(
                `/${ladder.year}/round/${ladder.season_round}/division/${ladder.division}`
              )
            }
          />
        </View>
      </Card>

      {feedback ? (
        <Card
          style={[
            styles.banner,
            feedback.type === "error" ? styles.bannerErr : styles.bannerOk,
          ]}
        >
          <Text
            style={[
              styles.bannerText,
              {
                color:
                  feedback.type === "error"
                    ? colors.danger
                    : colors.courtGreen,
              },
            ]}
          >
            {feedback.text}
          </Text>
        </Card>
      ) : null}

      {is_closed ? (
        <Card>
          <Text style={styles.closedTitle}>This ladder round is now closed</Text>
          <Text style={styles.closedSub}>
            If you need to adjust a past result, please contact
            results@highgate-ladder.co.uk.
          </Text>
        </Card>
      ) : (
        <Card>
          <SectionHeader
            title="Record Match"
            right={
              <Badge label={`${unplayed.length} remaining`} variant="blue" />
            }
          />

          {unplayed.length === 0 ? (
            <Text style={styles.allDoneText}>
              You have played every opponent in Division {ladder.division}!
            </Text>
          ) : (
            <View style={{ gap: spacing.lg }}>
              {/* Step 1: Opponent Picker */}
              <View>
                <Text style={styles.stepLabel}>1. Who did you play?</Text>
                <View style={styles.oppGrid}>
                  {unplayed.map((opp) => {
                    const selected = selectedOpponentId === opp.id;
                    return (
                      <Pressable
                        key={opp.id}
                        onPress={() => setSelectedOpponentId(opp.id)}
                        style={[
                          styles.oppCard,
                          selected && styles.oppCardSelected,
                        ]}
                      >
                        <View style={{ flex: 1 }}>
                          <Text
                            style={[
                              styles.oppName,
                              selected && styles.oppNameSelected,
                            ]}
                          >
                            {opp.name}
                          </Text>
                          {opp.h2h_played > 0 ? (
                            <Text style={styles.oppH2hSub}>
                              H2H: {opp.h2h_won}W–{opp.h2h_lost}L ({opp.h2h_played})
                            </Text>
                          ) : null}
                        </View>
                        <View style={styles.oppBadges}>
                          {player_id ? (
                            <Pressable
                              onPress={(e) => {
                                e.stopPropagation();
                                setH2HTarget({
                                  playerId: player_id,
                                  opponentId: opp.id,
                                });
                              }}
                            >
                              <Badge label="H2H" variant="blue" />
                            </Pressable>
                          ) : null}
                          <Pressable
                            onPress={(e) => {
                              e.stopPropagation();
                              router.push(`/player/${opp.id}`);
                            }}
                          >
                            <Badge label="Profile ↗" />
                          </Pressable>
                        </View>
                      </Pressable>
                    );
                  })}
                </View>
              </View>

              {/* Step 2: Outcome */}
              <View>
                <Text style={styles.stepLabel}>2. Match Outcome</Text>
                <View style={styles.segRow}>
                  {(
                    [
                      ["won", "I Won"],
                      ["lost", "I Lost"],
                      ["incomplete", "Incomplete"],
                    ] as const
                  ).map(([val, label]) => (
                    <Pressable
                      key={val}
                      onPress={() => setOutcome(val)}
                      style={[
                        styles.segBtn,
                        outcome === val && styles.segBtnActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.segText,
                          outcome === val && styles.segTextActive,
                        ]}
                      >
                        {label}
                      </Text>
                    </Pressable>
                  ))}
                </View>

                {outcome === "incomplete" ? (
                  <View style={styles.subOptions}>
                    <Text style={styles.subPrompt}>Reason</Text>
                    <View style={styles.segRow}>
                      <Pressable
                        onPress={() => setIncompleteReason("time")}
                        style={[
                          styles.segBtn,
                          incompleteReason === "time" && styles.segBtnActive,
                        ]}
                      >
                        <Text
                          style={[
                            styles.segText,
                            incompleteReason === "time" && styles.segTextActive,
                          ]}
                        >
                          Ran out of time
                        </Text>
                      </Pressable>
                      <Pressable
                        onPress={() => setIncompleteReason("injury")}
                        style={[
                          styles.segBtn,
                          incompleteReason === "injury" && styles.segBtnActive,
                        ]}
                      >
                        <Text
                          style={[
                            styles.segText,
                            incompleteReason === "injury" &&
                              styles.segTextActive,
                          ]}
                        >
                          Injury / retirement
                        </Text>
                      </Pressable>
                    </View>

                    {incompleteReason === "injury" ? (
                      <>
                        <Text style={styles.subPrompt}>Who retired?</Text>
                        <View style={styles.segRow}>
                          <Pressable
                            onPress={() => setInjuredPlayer("opponent")}
                            style={[
                              styles.segBtn,
                              injuredPlayer === "opponent" &&
                                styles.segBtnActive,
                            ]}
                          >
                            <Text
                              style={[
                                styles.segText,
                                injuredPlayer === "opponent" &&
                                  styles.segTextActive,
                              ]}
                            >
                              Opponent (You Win)
                            </Text>
                          </Pressable>
                          <Pressable
                            onPress={() => setInjuredPlayer("me")}
                            style={[
                              styles.segBtn,
                              injuredPlayer === "me" && styles.segBtnActive,
                            ]}
                          >
                            <Text
                              style={[
                                styles.segText,
                                injuredPlayer === "me" && styles.segTextActive,
                              ]}
                            >
                              Me (Opponent Wins)
                            </Text>
                          </Pressable>
                        </View>
                      </>
                    ) : null}
                  </View>
                ) : null}
              </View>

              {/* Step 3: Score Pills */}
              <View>
                <Text style={styles.stepLabel}>{scorePromptLabel}</Text>
                <View style={styles.scoreGrid}>
                  {SCORE_OPTIONS.map((num) => (
                    <Pressable
                      key={`p-${num}`}
                      onPress={() => setPrimaryScore(num)}
                      style={[
                        styles.scoreBtn,
                        primaryScore === num && styles.scoreBtnActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.scoreBtnText,
                          primaryScore === num && styles.scoreBtnTextActive,
                        ]}
                      >
                        {num}
                      </Text>
                    </Pressable>
                  ))}
                </View>

                {outcome === "incomplete" && incompleteReason === "time" ? (
                  <View style={{ marginTop: spacing.md }}>
                    <Text style={styles.stepLabel}>
                      4. Opponent's Score (0–8)
                    </Text>
                    <View style={styles.scoreGrid}>
                      {SCORE_OPTIONS.map((num) => (
                        <Pressable
                          key={`o-${num}`}
                          onPress={() => setOpponentScore(num)}
                          style={[
                            styles.scoreBtn,
                            opponentScore === num && styles.scoreBtnActive,
                          ]}
                        >
                          <Text
                            style={[
                              styles.scoreBtnText,
                              opponentScore === num &&
                                styles.scoreBtnTextActive,
                            ]}
                          >
                            {num}
                          </Text>
                        </Pressable>
                      ))}
                    </View>
                  </View>
                ) : null}
              </View>

              <Button
                label="Submit Match Result"
                disabled={!selectedOpponentId}
                loading={submitMutation.isPending}
                onPress={() => submitMutation.mutate()}
              />
            </View>
          )}
        </Card>
      )}

      {/* Entered Matches */}
      <Card>
        <SectionHeader
          title="Your Entered Matches"
          subtitle={`${entered.length} recorded in Division ${ladder.division}`}
        />
        {entered.length === 0 ? (
          <Text style={styles.emptyEntered}>No matches entered yet.</Text>
        ) : (
          entered.map((m) => (
            <View key={m.pair_key} style={styles.enteredRow}>
              <OutcomeBadge code={m.outcome_code} />
              <View style={{ flex: 1 }}>
                <Text style={styles.enteredOpp}>vs {m.opponent_name}</Text>
                <Text style={styles.enteredMeta}>
                  {m.score_display} · {m.date_added}
                </Text>
              </View>
              {!is_closed ? (
                <View style={styles.rowActions}>
                  <Button
                    label="Edit"
                    variant="outline"
                    size="sm"
                    onPress={() => openEditModal(m)}
                  />
                  <Button
                    label="Delete"
                    variant="danger"
                    size="sm"
                    onPress={() => setDeletingMatch(m)}
                  />
                </View>
              ) : null}
            </View>
          ))
        )}
      </Card>

      {/* Edit Modal */}
      <Modal
        visible={Boolean(editingMatch)}
        transparent
        animationType="fade"
        onRequestClose={() => setEditingMatch(null)}
      >
        <View style={styles.modalBackdrop}>
          <Card style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              Edit Match vs {editingMatch?.opponent_name}
            </Text>

            <Text style={styles.subPrompt}>Match Type</Text>
            <View style={styles.segRow}>
              {(
                [
                  ["completed", "Completed"],
                  ["time", "Time (Inc.)"],
                  ["injury", "Injury (Ret.)"],
                ] as const
              ).map(([val, lbl]) => (
                <Pressable
                  key={val}
                  onPress={() => setEditMode(val)}
                  style={[styles.segBtn, editMode === val && styles.segBtnActive]}
                >
                  <Text
                    style={[
                      styles.segText,
                      editMode === val && styles.segTextActive,
                    ]}
                  >
                    {lbl}
                  </Text>
                </Pressable>
              ))}
            </View>

            {editMode === "time" && editingMatch ? (
              <>
                <Text style={styles.subPrompt}>Your Score (0–8)</Text>
                <View style={styles.scoreGrid}>
                  {SCORE_OPTIONS.map((num) => (
                    <Pressable
                      key={`ew-${num}`}
                      onPress={() => setEditMyScore(num)}
                      style={[
                        styles.scoreBtn,
                        editMyScore === num && styles.scoreBtnActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.scoreBtnText,
                          editMyScore === num && styles.scoreBtnTextActive,
                        ]}
                      >
                        {num}
                      </Text>
                    </Pressable>
                  ))}
                </View>
                <Text style={styles.subPrompt}>Opponent Score (0–8)</Text>
                <View style={styles.scoreGrid}>
                  {SCORE_OPTIONS.map((num) => (
                    <Pressable
                      key={`el-${num}`}
                      onPress={() => setEditLosingScore(num)}
                      style={[
                        styles.scoreBtn,
                        editLosingScore === num && styles.scoreBtnActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.scoreBtnText,
                          editLosingScore === num && styles.scoreBtnTextActive,
                        ]}
                      >
                        {num}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </>
            ) : editingMatch && player_id ? (
              <>
                <Text style={styles.subPrompt}>Winner</Text>
                <View style={styles.segRow}>
                  <Pressable
                    onPress={() => setEditWinnerId(player_id)}
                    style={[
                      styles.segBtn,
                      editWinnerId === player_id && styles.segBtnActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.segText,
                        editWinnerId === player_id && styles.segTextActive,
                      ]}
                    >
                      You Won
                    </Text>
                  </Pressable>
                  <Pressable
                    onPress={() => setEditWinnerId(editingMatch.opponent_id)}
                    style={[
                      styles.segBtn,
                      editWinnerId === editingMatch.opponent_id &&
                        styles.segBtnActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.segText,
                        editWinnerId === editingMatch.opponent_id &&
                          styles.segTextActive,
                      ]}
                    >
                      {editingMatch.opponent_name}
                    </Text>
                  </Pressable>
                </View>

                <Text style={styles.subPrompt}>Losing Score (0–8)</Text>
                <View style={styles.scoreGrid}>
                  {SCORE_OPTIONS.map((num) => (
                    <Pressable
                      key={`ec-${num}`}
                      onPress={() => setEditLosingScore(num)}
                      style={[
                        styles.scoreBtn,
                        editLosingScore === num && styles.scoreBtnActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.scoreBtnText,
                          editLosingScore === num && styles.scoreBtnTextActive,
                        ]}
                      >
                        {num}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </>
            ) : null}

            <View style={styles.modalActions}>
              <Button
                label="Cancel"
                variant="outline"
                size="sm"
                onPress={() => setEditingMatch(null)}
              />
              <Button
                label="Save Changes"
                size="sm"
                loading={editMutation.isPending}
                onPress={() => editMutation.mutate()}
              />
            </View>
          </Card>
        </View>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal
        visible={Boolean(deletingMatch)}
        transparent
        animationType="fade"
        onRequestClose={() => setDeletingMatch(null)}
      >
        <View style={styles.modalBackdrop}>
          <Card style={styles.modalCard}>
            <Text style={styles.modalTitle}>Delete Match Result?</Text>
            <Text style={styles.closedSub}>
              Remove {deletingMatch?.score_display} vs{" "}
              {deletingMatch?.opponent_name}? This cannot be undone.
            </Text>
            <View style={styles.modalActions}>
              <Button
                label="Cancel"
                variant="outline"
                size="sm"
                onPress={() => setDeletingMatch(null)}
              />
              <Button
                label="Delete Result"
                variant="danger"
                size="sm"
                loading={deleteMutation.isPending}
                onPress={() => {
                  if (deletingMatch) deleteMutation.mutate(deletingMatch.pair_key);
                }}
              />
            </View>
          </Card>
        </View>
      </Modal>

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: colors.text,
  },
  subtitle: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  banner: {
    paddingVertical: spacing.md,
  },
  bannerOk: {
    backgroundColor: colors.courtGreenSoft,
    borderColor: "#86EFAC",
  },
  bannerErr: {
    backgroundColor: colors.dangerSoft,
    borderColor: "#FECACA",
  },
  bannerText: {
    fontSize: 15,
    fontWeight: "700",
  },
  closedTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.text,
  },
  closedSub: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 4,
  },
  allDoneText: {
    fontSize: 16,
    color: colors.courtGreen,
    fontWeight: "600",
    textAlign: "center",
    paddingVertical: spacing.md,
  },
  stepLabel: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
    marginBottom: spacing.sm,
  },
  oppGrid: {
    gap: spacing.sm,
  },
  oppCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
  },
  oppCardSelected: {
    borderColor: colors.courtGreen,
    backgroundColor: colors.courtGreenSoft,
  },
  oppName: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
  },
  oppNameSelected: {
    color: colors.courtGreen,
  },
  oppH2hSub: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  oppBadges: {
    flexDirection: "row",
    gap: 6,
  },
  segRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  segBtn: {
    flex: 1,
    paddingVertical: 11,
    paddingHorizontal: spacing.sm,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
    alignItems: "center",
  },
  segBtnActive: {
    backgroundColor: colors.navy,
    borderColor: colors.navy,
  },
  segText: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.textSecondary,
    textAlign: "center",
  },
  segTextActive: {
    color: colors.white,
  },
  subOptions: {
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    gap: spacing.sm,
  },
  subPrompt: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textMuted,
    marginTop: spacing.sm,
  },
  scoreGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: 4,
  },
  scoreBtn: {
    width: 48,
    height: 48,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
    justifyContent: "center",
    alignItems: "center",
  },
  scoreBtnActive: {
    backgroundColor: colors.courtGreen,
    borderColor: colors.courtGreen,
  },
  scoreBtnText: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.text,
  },
  scoreBtnTextActive: {
    color: colors.white,
  },
  emptyEntered: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    textAlign: "center",
    paddingVertical: spacing.md,
  },
  enteredRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  enteredOpp: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
  },
  enteredMeta: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  rowActions: {
    flexDirection: "row",
    gap: spacing.xs,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(15, 23, 42, 0.55)",
    justifyContent: "center",
    alignItems: "center",
    padding: spacing.lg,
  },
  modalCard: {
    width: "100%",
    maxWidth: 460,
    gap: spacing.sm,
  },
  modalTitle: {
    fontSize: 19,
    fontWeight: "800",
    color: colors.text,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
});
