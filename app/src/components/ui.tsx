import { useRouter } from "expo-router";
import React from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  View,
  ViewStyle,
} from "react-native";

import type { RecentMatchOut } from "../api/types";
import {
  MAX_CONTENT_WIDTH,
  cardShadow,
  colors,
  radii,
  spacing,
  useResponsive,
} from "../theme/tokens";

export function PageScroll({
  children,
  contentStyle,
  desktopClean = false,
}: {
  children: React.ReactNode;
  contentStyle?: StyleProp<ViewStyle>;
  desktopClean?: boolean;
}) {
  const { isDesktop } = useResponsive();
  return (
    <ScrollView
      style={[
        styles.pageScroll,
        isDesktop && desktopClean && styles.pageScrollClean,
      ]}
      contentContainerStyle={[styles.pageScrollContent, contentStyle]}
      keyboardShouldPersistTaps="handled"
    >
      <ResponsiveContainer>
        {children}
        {isDesktop ? <SiteFooter /> : null}
      </ResponsiveContainer>
    </ScrollView>
  );
}

function SiteFooter() {
  return (
    <View style={styles.footer}>
      <Pressable
        onPress={() => void Linking.openURL("mailto:feedback@highgate-ladder.co.uk")}
      >
        <Text style={styles.footerLink}>feedback@highgate-ladder.co.uk</Text>
      </Pressable>
      <Text style={styles.footerText}>
        Want to contribute?{" "}
        <Text
          onPress={() =>
            void Linking.openURL("https://github.com/jzahedieh/django-tennis-ladder")
          }
          style={styles.footerLink}
        >
          GitHub
        </Text>
      </Text>
    </View>
  );
}

export function ResponsiveContainer({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const { isDesktop } = useResponsive();
  return (
    <View
      style={[
        styles.container,
        isDesktop && styles.containerDesktop,
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function Card({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function SectionHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <View style={styles.sectionHeader}>
      <View style={{ flex: 1 }}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
      </View>
      {right}
    </View>
  );
}

export function Badge({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: "neutral" | "navy" | "blue" | "green" | "amber" | "danger";
}) {
  const palette = {
    neutral: { bg: colors.surfaceMuted, text: colors.textSecondary, border: colors.border },
    navy: { bg: colors.navy, text: colors.white, border: colors.navy },
    blue: { bg: colors.clubBlueSoft, text: colors.navy, border: colors.clubBlue },
    green: { bg: colors.winBg, text: colors.winText, border: "#BBF7D0" },
    amber: { bg: colors.incompleteBg, text: colors.incompleteText, border: "#FDE68A" },
    danger: { bg: colors.retiredBg, text: colors.retiredText, border: "#FECACA" },
  }[variant];

  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: palette.bg, borderColor: palette.border },
      ]}
    >
      <Text style={[styles.badgeText, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

export function OutcomeBadge({ code }: { code: string }) {
  const upper = code.toUpperCase();
  const variant =
    upper === "W"
      ? "green"
      : upper === "I"
      ? "amber"
      : upper === "R"
      ? "danger"
      : "neutral";
  return <Badge label={upper} variant={variant} />;
}

export function Button({
  label,
  onPress,
  variant = "primary",
  size = "md",
  disabled = false,
  loading = false,
  style,
}: {
  label: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "outline" | "danger";
  size?: "sm" | "md";
  disabled?: boolean;
  loading?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const theme = {
    primary: { bg: colors.courtGreen, text: colors.white, border: colors.courtGreen },
    secondary: { bg: colors.navy, text: colors.white, border: colors.navy },
    outline: { bg: colors.surface, text: colors.navy, border: colors.borderStrong },
    danger: { bg: colors.danger, text: colors.white, border: colors.danger },
  }[variant];

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.btn,
        size === "sm" && styles.btnSm,
        {
          backgroundColor: theme.bg,
          borderColor: theme.border,
          opacity: disabled || loading ? 0.55 : pressed ? 0.85 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={theme.text} />
      ) : (
        <Text
          style={[
            styles.btnText,
            size === "sm" && styles.btnTextSm,
            { color: theme.text },
          ]}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <View style={styles.stateBox}>
      <ActivityIndicator size="large" color={colors.navy} />
      <Text style={styles.stateText}>{label}</Text>
    </View>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card style={styles.errorCard}>
      <Text style={styles.errorTitle}>Unable to load data</Text>
      <Text style={styles.errorText}>{message}</Text>
      {onRetry ? (
        <Button
          label="Try Again"
          onPress={onRetry}
          variant="secondary"
          size="sm"
          style={{ alignSelf: "flex-start", marginTop: spacing.sm }}
        />
      ) : null}
    </Card>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: React.ReactNode;
}) {
  return (
    <Card style={styles.emptyCard}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyText}>{message}</Text>
      {action ? <View style={{ marginTop: spacing.md }}>{action}</View> : null}
    </Card>
  );
}

/** Renders recent match rows matching the web layout (`[Div X] Winner def. Loser` + score pill). */
export function RecentResultsList({
  matches,
  showDivisionBadge = false,
  onSelectH2H,
}: {
  matches: RecentMatchOut[];
  showDivisionBadge?: boolean;
  onSelectH2H: (target: {
    playerId: number;
    opponentId: number;
    title?: string;
  }) => void;
}) {
  const router = useRouter();

  return (
    <View style={styles.recentList}>
      {matches.map((m, idx) => (
        <View
          key={`${m.division}-${m.winner_id}-${m.loser_id}-${m.date_added}-${idx}`}
          style={[
            styles.recentRow,
            idx === matches.length - 1 && styles.recentRowLast,
          ]}
        >
          <View style={styles.recentLeftCol}>
            <View style={styles.recentTopLine}>
              {showDivisionBadge ? (
                <Pressable
                  onPress={() =>
                    router.push(
                      `/${m.year}/round/${m.season_round}/division/${m.division}`
                    )
                  }
                  style={styles.recentDivBadge}
                >
                  <Text style={styles.recentDivBadgeText}>Div {m.division}</Text>
                </Pressable>
              ) : null}
              <Text style={styles.recentPlayersLine} numberOfLines={1}>
                <Text
                  onPress={() => router.push(`/player/${m.winner_id}`)}
                  style={styles.recentWinnerName}
                >
                  {m.winner_name}
                </Text>{" "}
                <Text style={styles.recentDefWord}>
                  {m.is_incomplete ? "vs" : "def."}
                </Text>{" "}
                <Text
                  onPress={() => router.push(`/player/${m.loser_id}`)}
                  style={
                    m.is_incomplete
                      ? styles.recentWinnerName
                      : styles.recentLoserName
                  }
                >
                  {m.loser_name}
                </Text>
              </Text>
            </View>
            <Text style={styles.recentDateText}>{m.date_display}</Text>
          </View>

          <Pressable
            onPress={() =>
              onSelectH2H({
                playerId: m.winner_id,
                opponentId: m.loser_id,
                title: `${m.winner_name} vs ${m.loser_name}`,
              })
            }
            style={[
              styles.recentScorePill,
              m.is_incomplete && styles.recentScorePillIncomplete,
            ]}
          >
            <Text
              style={[
                styles.recentScoreText,
                m.is_incomplete && styles.recentScoreTextIncomplete,
              ]}
            >
              {m.score_display}
            </Text>
          </Pressable>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  pageScroll: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  pageScrollClean: {
    backgroundColor: colors.white,
  },
  pageScrollContent: {
    paddingBottom: spacing.xxl + 24,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.lg,
    marginTop: spacing.md,
    gap: 6,
  },
  footerText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textMuted,
  },
  footerLink: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.linkBlue,
  },
  container: {
    width: "100%",
    maxWidth: MAX_CONTENT_WIDTH,
    alignSelf: "center",
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    gap: spacing.lg,
  },
  containerDesktop: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    ...cardShadow,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: 19,
    fontWeight: "700",
    color: colors.text,
  },
  sectionSubtitle: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radii.pill,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  badgeText: {
    fontSize: 13,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  btn: {
    backgroundColor: colors.courtGreen,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: 11,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 42,
  },
  btnSm: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    minHeight: 36,
  },
  btnText: {
    fontSize: 16,
    fontWeight: "700",
  },
  btnTextSm: {
    fontSize: 14,
    fontWeight: "700",
  },
  stateBox: {
    paddingVertical: 48,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
  },
  stateText: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
  },
  errorCard: {
    borderColor: "#FECACA",
    backgroundColor: colors.dangerSoft,
  },
  errorTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.danger,
  },
  errorText: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textSecondary,
    marginTop: 4,
  },
  emptyCard: {
    alignItems: "center",
    paddingVertical: spacing.xl,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.text,
  },
  emptyText: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 4,
    textAlign: "center",
  },
  recentList: {
    gap: 2,
  },
  recentRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceMuted,
  },
  recentRowLast: {
    borderBottomWidth: 0,
    paddingBottom: 2,
  },
  recentLeftCol: {
    flex: 1,
    minWidth: 0,
  },
  recentTopLine: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  recentDivBadge: {
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.sm,
    paddingHorizontal: 7,
    paddingVertical: 2,
    flexShrink: 0,
  },
  recentDivBadgeText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  recentPlayersLine: {
    flex: 1,
    fontSize: 15,
    color: colors.text,
  },
  recentWinnerName: {
    fontWeight: "700",
    color: colors.text,
  },
  recentDefWord: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
  },
  recentLoserName: {
    fontWeight: "500",
    color: colors.textMuted,
  },
  recentDateText: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 3,
  },
  recentScorePill: {
    backgroundColor: colors.clubBlueSoft,
    borderWidth: 1,
    borderColor: colors.clubBlue,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radii.pill,
    flexShrink: 0,
  },
  recentScorePillIncomplete: {
    backgroundColor: colors.surfaceMuted,
    borderColor: colors.border,
  },
  recentScoreText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.linkBlue,
    fontVariant: ["tabular-nums"],
  },
  recentScoreTextIncomplete: {
    color: colors.textSecondary,
  },
});
