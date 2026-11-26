import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";

import { apiClient, extractApiError } from "../src/api/client";
import { Button, Card, PageScroll } from "../src/components/ui";
import { colors, radii, spacing } from "../src/theme/tokens";

export default function ResetPasswordScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ uid?: string; token?: string }>();
  const hasConfirmParams = Boolean(params.uid && params.token);

  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{
    type: "ok" | "err";
    text: string;
  } | null>(null);

  const requestReset = async () => {
    setSubmitting(true);
    setStatusMsg(null);
    try {
      const { data, error } = await apiClient.POST("/v1/auth/password-reset", {
        body: { email: email.trim() },
      });
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not send reset email."));
      }
      setStatusMsg({ type: "ok", text: data.detail });
    } catch (err) {
      setStatusMsg({ type: "err", text: (err as Error).message });
    } finally {
      setSubmitting(false);
    }
  };

  const confirmReset = async () => {
    if (!params.uid || !params.token) return;
    setSubmitting(true);
    setStatusMsg(null);
    try {
      const { data, error } = await apiClient.POST(
        "/v1/auth/password-reset/confirm",
        {
          body: {
            uid: String(params.uid),
            token: String(params.token),
            new_password: newPassword,
          },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not reset password."));
      }
      setStatusMsg({ type: "ok", text: data.detail });
    } catch (err) {
      setStatusMsg({ type: "err", text: (err as Error).message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageScroll>
      <View style={styles.wrap}>
        <Card style={styles.card}>
          <Text style={styles.title}>
            {hasConfirmParams ? "Choose New Password" : "Set / Reset Password"}
          </Text>
          <Text style={styles.sub}>
            {hasConfirmParams
              ? "Enter your new password below."
              : "Enter the email linked to your Highgate Ladder account and we will send a setup/reset link."}
          </Text>

          {statusMsg ? (
            <View
              style={[
                styles.msgBox,
                statusMsg.type === "err" ? styles.msgErr : styles.msgOk,
              ]}
            >
              <Text
                style={{
                  fontSize: 14,
                  fontWeight: "600",
                  color:
                    statusMsg.type === "err"
                      ? colors.danger
                      : colors.courtGreen,
                }}
              >
                {statusMsg.text}
              </Text>
            </View>
          ) : null}

          {hasConfirmParams ? (
            <>
              <TextInput
                value={newPassword}
                onChangeText={setNewPassword}
                secureTextEntry
                placeholder="New password"
                style={styles.input}
              />
              <Button
                label="Set Password"
                loading={submitting}
                disabled={!newPassword}
                onPress={() => void confirmReset()}
              />
            </>
          ) : (
            <>
              <TextInput
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                placeholder="you@example.com"
                style={styles.input}
              />
              <Button
                label="Send Reset Email"
                loading={submitting}
                disabled={!email.trim()}
                onPress={() => void requestReset()}
              />
            </>
          )}

          <Button
            label="Back to Log In"
            variant="outline"
            size="sm"
            onPress={() => router.replace("/login")}
            style={{ marginTop: spacing.md }}
          />
        </Card>
      </View>
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  wrap: {
    maxWidth: 440,
    width: "100%",
    alignSelf: "center",
    paddingVertical: spacing.lg,
  },
  card: {
    gap: spacing.sm,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: colors.text,
  },
  sub: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  msgBox: {
    borderRadius: radii.md,
    borderWidth: 1,
    padding: spacing.md,
  },
  msgOk: {
    backgroundColor: colors.courtGreenSoft,
    borderColor: "#86EFAC",
  },
  msgErr: {
    backgroundColor: colors.dangerSoft,
    borderColor: "#FECACA",
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
  },
});
