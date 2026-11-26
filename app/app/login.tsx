import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { useAuth } from "../src/auth/AuthContext";
import { Button, Card, PageScroll } from "../src/components/ui";
import { colors, radii, spacing } from "../src/theme/tokens";

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleLogin = async () => {
    setErrorMsg(null);
    setSubmitting(true);
    try {
      await login(email, password);
      if (router.canGoBack()) {
        router.back();
      } else {
        router.replace("/");
      }
    } catch (err) {
      setErrorMsg((err as Error).message || "Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageScroll>
      <View style={styles.wrap}>
        <Card style={styles.card}>
          <Text style={styles.eyebrow}>HIGHGATE COMPETITIONS</Text>
          <Text style={styles.title}>Log In</Text>
          <Text style={styles.sub}>
            Use your Highgate Ladder email address and password.
          </Text>

          {errorMsg ? (
            <View style={styles.errBox}>
              <Text style={styles.errText}>{errorMsg}</Text>
            </View>
          ) : null}

          <Text style={styles.label}>Email / Username</Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            placeholder="you@example.com"
            style={styles.input}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="password"
            placeholder="Password"
            style={styles.input}
            onSubmitEditing={() => void handleLogin()}
          />

          <Button
            label="Log In"
            loading={submitting}
            disabled={!email.trim() || !password}
            onPress={() => void handleLogin()}
          />

          <Pressable
            onPress={() => router.push("/reset-password")}
            style={styles.linkWrap}
          >
            <Text style={styles.linkText}>
              First time logging in or forgot password? Set your password →
            </Text>
          </Pressable>
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
    gap: spacing.xs,
  },
  eyebrow: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 26,
    fontWeight: "800",
    color: colors.text,
  },
  sub: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  errBox: {
    backgroundColor: colors.dangerSoft,
    borderColor: "#FECACA",
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  errText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.danger,
  },
  label: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
    marginTop: spacing.xs,
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
  linkWrap: {
    marginTop: spacing.md,
    alignItems: "center",
  },
  linkText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.navy,
    textAlign: "center",
  },
});
