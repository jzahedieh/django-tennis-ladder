import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import type { SubscriptionRef } from "../../src/api/types";
import { useAuth } from "../../src/auth/AuthContext";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageScroll,
  SectionHeader,
} from "../../src/components/ui";
import { colors, radii, spacing } from "../../src/theme/tokens";

export default function AccountScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isHydrating, logout, refreshUser } = useAuth();

  const [email, setEmail] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [unsubscribingId, setUnsubscribingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<{
    type: "ok" | "err";
    text: string;
  } | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["account", user?.id ?? "anon"],
    enabled: Boolean(user),
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/v1/account/");
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load account."));
      }
      return data;
    },
  });

  useEffect(() => {
    if (data?.email) {
      setEmail(data.email);
    }
  }, [data?.email]);

  const emailMutation = useMutation({
    mutationFn: async () => {
      const { data: res, error } = await apiClient.PATCH("/v1/account/email/", {
        body: { email: email.trim() },
      });
      if (error || !res) {
        throw new Error(extractApiError(error, "Could not update email."));
      }
      return res;
    },
    onSuccess: async () => {
      setNotice({
        type: "ok",
        text: "Email updated. Confirmation sent to your old and new addresses.",
      });
      await refreshUser();
      await queryClient.invalidateQueries({ queryKey: ["account"] });
    },
    onError: (err: Error) => {
      setNotice({ type: "err", text: err.message });
    },
  });

  const passwordMutation = useMutation({
    mutationFn: async () => {
      const { data: res, error } = await apiClient.POST(
        "/v1/account/password/",
        {
          body: {
            old_password: oldPassword,
            new_password: newPassword,
          },
        }
      );
      if (error || !res) {
        throw new Error(extractApiError(error, "Could not change password."));
      }
      return res;
    },
    onSuccess: (res) => {
      setOldPassword("");
      setNewPassword("");
      setNotice({ type: "ok", text: res.detail });
    },
    onError: (err: Error) => {
      setNotice({ type: "err", text: err.message });
    },
  });

  const unsubscribeMutation = useMutation({
    mutationFn: async (sub: SubscriptionRef) => {
      setUnsubscribingId(sub.ladder_id);
      const { data: res, error } = await apiClient.POST(
        "/v1/ladder/seasons/{year}/round/{season_round}/division/{division_id}/subscription/",
        {
          params: {
            path: {
              year: sub.year,
              season_round: sub.season_round,
              division_id: sub.division,
            },
          },
        }
      );
      if (error || !res) {
        throw new Error(extractApiError(error, "Could not unsubscribe."));
      }
      return res;
    },
    onSuccess: async (res) => {
      setNotice({ type: "ok", text: res.detail });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["account"] }),
        queryClient.invalidateQueries({ queryKey: ["division-detail"] }),
      ]);
    },
    onError: (err: Error) => {
      setNotice({ type: "err", text: err.message });
    },
    onSettled: () => {
      setUnsubscribingId(null);
    },
  });

  if (isHydrating || (user && isLoading)) {
    return (
      <PageScroll>
        <LoadingState label="Loading account..." />
      </PageScroll>
    );
  }

  if (!user) {
    return (
      <PageScroll>
        <EmptyState
          title="Highgate Competitions Account"
          message="Log in to enter results, subscribe to division updates, and manage your email or password."
          action={
            <View style={styles.guestBtns}>
              <Button label="Log In" onPress={() => router.push("/login")} />
              <Button
                label="First-Time Setup / Reset Password"
                variant="outline"
                onPress={() => router.push("/reset-password")}
              />
            </View>
          }
        />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load account."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  return (
    <PageScroll>
      <Card>
        <View style={styles.topRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.eyebrow}>MY ACCOUNT</Text>
            <Text style={styles.name}>{data.player_name || data.email}</Text>
            <Text style={styles.emailSub}>{data.email}</Text>
          </View>
          <View style={styles.topActions}>
            {data.player_id ? (
              <Button
                label="My Profile"
                variant="secondary"
                size="sm"
                onPress={() => router.push(`/player/${data.player_id}`)}
              />
            ) : null}
            <Button
              label="Log Out"
              variant="outline"
              size="sm"
              onPress={() => void logout()}
            />
          </View>
        </View>
      </Card>

      {notice ? (
        <Card
          style={[
            styles.noticeCard,
            notice.type === "err" ? styles.noticeErr : styles.noticeOk,
          ]}
        >
          <Text
            style={{
              fontWeight: "700",
              fontSize: 13,
              color:
                notice.type === "err" ? colors.danger : colors.courtGreen,
            }}
          >
            {notice.text}
          </Text>
        </Card>
      ) : null}

      {/* Divisions & Subscriptions */}
      <Card>
        <SectionHeader title="Current Ladder & Notifications" />
        {data.current_division ? (
          <View style={styles.divBox}>
            <Text style={styles.divTitle}>
              {data.current_division.season_name} · Division{" "}
              {data.current_division.division}
            </Text>
            <Button
              label="Open Division"
              variant="outline"
              size="sm"
              onPress={() =>
                router.push(
                  `/${data.current_division!.year}/round/${data.current_division!.season_round}/division/${data.current_division!.division}`
                )
              }
            />
          </View>
        ) : (
          <Text style={styles.mutedText}>
            Not enrolled in the current round ({data.current_season_name || "—"}).
          </Text>
        )}

        <Text style={styles.subHeading}>
          Active Email Subscriptions ({data.subscriptions.length})
        </Text>
        {data.subscriptions.length === 0 ? (
          <Text style={styles.mutedText}>
            No active email subscriptions for open ladders.
          </Text>
        ) : (
          data.subscriptions.map((s) => (
            <View key={s.ladder_id} style={styles.subRow}>
              <Pressable
                onPress={() =>
                  router.push(
                    `/${s.year}/round/${s.season_round}/division/${s.division}`
                  )
                }
                style={{ flex: 1 }}
              >
                <Text style={styles.subTitle}>
                  {s.season_name} · Division {s.division}
                </Text>
              </Pressable>
              <Button
                label="Unsubscribe"
                variant="outline"
                size="sm"
                loading={unsubscribingId === s.ladder_id}
                onPress={() => unsubscribeMutation.mutate(s)}
              />
            </View>
          ))
        )}
      </Card>

      {/* Email Change */}
      <Card>
        <SectionHeader title="Email / Login Address" />
        <TextInput
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="you@example.com"
          style={styles.input}
        />
        <Button
          label="Update Email"
          variant="secondary"
          size="sm"
          loading={emailMutation.isPending}
          onPress={() => emailMutation.mutate()}
        />
      </Card>

      {/* Password Change */}
      <Card>
        <SectionHeader title="Change Password" />
        <TextInput
          value={oldPassword}
          onChangeText={setOldPassword}
          secureTextEntry
          placeholder="Current password"
          style={styles.input}
        />
        <TextInput
          value={newPassword}
          onChangeText={setNewPassword}
          secureTextEntry
          placeholder="New password"
          style={styles.input}
        />
        <Button
          label="Update Password"
          variant="secondary"
          size="sm"
          disabled={!oldPassword || !newPassword}
          loading={passwordMutation.isPending}
          onPress={() => passwordMutation.mutate()}
        />
      </Card>
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  guestBtns: {
    gap: spacing.sm,
    width: "100%",
  },
  topRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  eyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.8,
  },
  name: {
    fontSize: 24,
    fontWeight: "800",
    color: colors.text,
    marginTop: 2,
  },
  emailSub: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  topActions: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  noticeCard: {
    paddingVertical: spacing.md,
  },
  noticeOk: {
    backgroundColor: colors.courtGreenSoft,
    borderColor: "#86EFAC",
  },
  noticeErr: {
    backgroundColor: colors.dangerSoft,
    borderColor: "#FECACA",
  },
  divBox: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
    backgroundColor: colors.surfaceMuted,
    padding: spacing.md,
    borderRadius: radii.md,
    marginBottom: spacing.md,
  },
  divTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.navy,
    flex: 1,
  },
  subHeading: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.textSecondary,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  subRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  subTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
  mutedText: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.textMuted,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 11,
    fontSize: 16,
    fontWeight: "500",
    color: colors.text,
    backgroundColor: colors.surface,
    marginBottom: spacing.md,
  },
});
