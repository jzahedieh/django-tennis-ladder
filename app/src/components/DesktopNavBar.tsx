import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type ViewStyle,
} from "react-native";

import { apiClient } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  MAX_CONTENT_WIDTH,
  cardShadow,
  colors,
  radii,
  spacing,
} from "../theme/tokens";
import { PlayerSearchBar } from "./PlayerSearchBar";

type OpenMenu = "prev" | "login" | "account" | null;

export function DesktopNavBar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, login, logout } = useAuth();

  const [openMenu, setOpenMenu] = useState<OpenMenu>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  useEffect(() => {
    setOpenMenu(null);
  }, [pathname]);

  const { data: archiveData } = useQuery({
    queryKey: ["seasons-archive"],
    staleTime: 60_000,
    queryFn: async () => {
      const { data } = await apiClient.GET("/v1/ladder/seasons/");
      return data ?? null;
    },
  });

  const seasons = archiveData?.seasons ?? [];
  const latestSeason = seasons[0];
  const previousSeasons = seasons.slice(1, 5);

  const currentHref = latestSeason
    ? `/${latestSeason.year}/round/${latestSeason.season_round}`
    : "/current";

  const isCurrentActive =
    pathname === "/current" ||
    pathname === "/ladder" ||
    Boolean(
      latestSeason &&
        pathname.startsWith(
          `/${latestSeason.year}/round/${latestSeason.season_round}`
        )
    );

  const isArchiveRoundPath = /^\/\d{4}\/round\/\d+/.test(pathname);
  const isPreviousActive =
    pathname.startsWith("/list") || (isArchiveRoundPath && !isCurrentActive);

  const isEnterActive =
    pathname.startsWith("/result/entry") || pathname === "/enter";
  const isStatsActive = pathname.startsWith("/stats");

  const navigate = (href: string) => {
    setOpenMenu(null);
    router.push(href as never);
  };

  const handleInlineLogin = async () => {
    if (!email.trim() || !password) return;
    setLoginError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      setPassword("");
      setOpenMenu(null);
    } catch (err) {
      setLoginError((err as Error).message || "Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setOpenMenu(null);
    await logout();
  };

  return (
    <View style={styles.bar}>
      {openMenu !== null ? (
        <Pressable
          onPress={() => setOpenMenu(null)}
          style={[
            styles.outsideDismiss,
            Platform.OS === "web"
              ? ({ position: "fixed" } as unknown as ViewStyle)
              : null,
          ]}
          accessibilityLabel="Close menu"
        />
      ) : null}

      <View style={styles.inner}>
        <Pressable onPress={() => navigate("/")} style={styles.brand}>
          <Image
            source={require("../../assets/highgate-logo.png")}
            style={styles.logo}
            resizeMode="contain"
          />
          <View>
            <Text style={styles.brandTop}>HIGHGATE</Text>
            <Text style={styles.brandSub}>COMPETITIONS</Text>
          </View>
        </Pressable>

        <View style={styles.navLinks}>
          <Pressable
            onPress={() => navigate("/result/entry")}
            style={[styles.navItem, isEnterActive && styles.navItemActive]}
          >
            <Text style={[styles.navText, isEnterActive && styles.navTextActive]}>
              Enter Result
            </Text>
          </Pressable>

          <Pressable
            onPress={() => navigate(currentHref)}
            style={[styles.navItem, isCurrentActive && styles.navItemActive]}
          >
            <Text
              style={[styles.navText, isCurrentActive && styles.navTextActive]}
            >
              Current Ladder
            </Text>
          </Pressable>

          {/* Previous Ladders Dropdown */}
          <View style={styles.menuAnchor}>
            <Pressable
              onPress={() =>
                setOpenMenu((prev) => (prev === "prev" ? null : "prev"))
              }
              style={[styles.navItem, isPreviousActive && styles.navItemActive]}
            >
              <Text
                style={[
                  styles.navText,
                  isPreviousActive && styles.navTextActive,
                ]}
              >
                Previous Ladders ▾
              </Text>
            </Pressable>

            {openMenu === "prev" ? (
              <View style={[styles.dropdown, styles.dropdownLeft]}>
                {previousSeasons.length === 0 ? (
                  <Text style={styles.dropdownHint}>Loading rounds...</Text>
                ) : (
                  previousSeasons.map((s) => (
                    <Pressable
                      key={s.id}
                      onPress={() =>
                        navigate(`/${s.year}/round/${s.season_round}`)
                      }
                      style={({ pressed }) => [
                        styles.dropdownItem,
                        pressed && styles.dropdownItemPressed,
                      ]}
                    >
                      <Text style={styles.dropdownItemText}>{s.name}</Text>
                    </Pressable>
                  ))
                )}
                <View style={styles.dropdownDivider} />
                <Pressable
                  onPress={() => navigate("/list")}
                  style={({ pressed }) => [
                    styles.dropdownItem,
                    pressed && styles.dropdownItemPressed,
                  ]}
                >
                  <Text style={styles.dropdownViewAll}>
                    .. view all {seasons.length} ladders ..
                  </Text>
                </Pressable>
              </View>
            ) : null}
          </View>

          <Pressable
            onPress={() => navigate("/stats")}
            style={[styles.navItem, isStatsActive && styles.navItemActive]}
          >
            <Text style={[styles.navText, isStatsActive && styles.navTextActive]}>
              Stats
            </Text>
          </Pressable>
        </View>

        <View style={styles.rightCluster}>
          <View style={styles.searchWrap}>
            <PlayerSearchBar compact onSelect={() => setOpenMenu(null)} />
          </View>

          {user ? (
            <View style={styles.menuAnchor}>
              <Pressable
                onPress={() =>
                  setOpenMenu((prev) => (prev === "account" ? null : "account"))
                }
                style={styles.accountTrigger}
              >
                <Ionicons name="person-circle" size={18} color={colors.navyDark} />
                <Text style={styles.accountTriggerText} numberOfLines={1}>
                  {user.player_name || user.email} ▾
                </Text>
              </Pressable>

              {openMenu === "account" ? (
                <View style={[styles.dropdown, styles.dropdownRight]}>
                  <View style={styles.accountHeader}>
                    <Text style={styles.accountEmail} numberOfLines={1}>
                      {user.email}
                    </Text>
                  </View>
                  <View style={styles.dropdownDivider} />
                  <Pressable
                    onPress={() => navigate("/account")}
                    style={({ pressed }) => [
                      styles.dropdownItem,
                      pressed && styles.dropdownItemPressed,
                    ]}
                  >
                    <Text style={styles.dropdownItemText}>
                      My Account & Subscriptions
                    </Text>
                  </Pressable>
                  {user.player_id ? (
                    <Pressable
                      onPress={() => navigate(`/player/${user.player_id}`)}
                      style={({ pressed }) => [
                        styles.dropdownItem,
                        pressed && styles.dropdownItemPressed,
                      ]}
                    >
                      <Text style={styles.dropdownItemText}>My Profile</Text>
                    </Pressable>
                  ) : null}
                  <View style={styles.dropdownDivider} />
                  <Pressable
                    onPress={() => void handleLogout()}
                    style={({ pressed }) => [
                      styles.dropdownItem,
                      pressed && styles.dropdownItemPressed,
                    ]}
                  >
                    <Text style={styles.logoutText}>Log Out</Text>
                  </Pressable>
                </View>
              ) : null}
            </View>
          ) : (
            <View style={styles.menuAnchor}>
              <Pressable
                onPress={() => {
                  setLoginError(null);
                  setOpenMenu((prev) => (prev === "login" ? null : "login"));
                }}
                style={styles.navItem}
              >
                <Text style={styles.loginTriggerText}>Log In ▾</Text>
              </Pressable>

              {openMenu === "login" ? (
                <View style={[styles.dropdown, styles.loginPopover]}>
                  {loginError ? (
                    <View style={styles.loginErrBox}>
                      <Text style={styles.loginErrText}>{loginError}</Text>
                    </View>
                  ) : null}

                  <Text style={styles.fieldLabel}>Email</Text>
                  <TextInput
                    value={email}
                    onChangeText={setEmail}
                    placeholder="you@example.com"
                    placeholderTextColor={colors.textMuted}
                    autoCapitalize="none"
                    autoComplete="email"
                    keyboardType="email-address"
                    style={styles.input}
                  />

                  <View style={styles.passwordLabelRow}>
                    <Text style={styles.fieldLabel}>Password</Text>
                    <Pressable onPress={() => navigate("/reset-password")}>
                      <Text style={styles.forgotLink}>Forgot?</Text>
                    </Pressable>
                  </View>
                  <TextInput
                    value={password}
                    onChangeText={setPassword}
                    placeholder="Password"
                    placeholderTextColor={colors.textMuted}
                    secureTextEntry
                    autoComplete="password"
                    style={styles.input}
                    onSubmitEditing={() => void handleInlineLogin()}
                  />

                  <Pressable
                    disabled={submitting || !email.trim() || !password}
                    onPress={() => void handleInlineLogin()}
                    style={({ pressed }) => [
                      styles.popoverLoginBtn,
                      (submitting || !email.trim() || !password) &&
                        styles.btnDisabled,
                      pressed && { opacity: 0.88 },
                    ]}
                  >
                    {submitting ? (
                      <ActivityIndicator size="small" color={colors.white} />
                    ) : (
                      <Text style={styles.popoverLoginBtnText}>Log In</Text>
                    )}
                  </Pressable>

                  <View style={styles.dropdownDivider} />
                  <Pressable
                    onPress={() => navigate("/reset-password")}
                    style={styles.firstTimeWrap}
                  >
                    <Text style={styles.firstTimeText}>
                      First time logging in?{" "}
                      <Text style={styles.forgotLink}>Set your password.</Text>
                    </Text>
                  </Pressable>
                </View>
              ) : null}
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: colors.clubBlue,
    borderBottomWidth: 1,
    borderBottomColor: "#8EA4CE",
    zIndex: 1000,
    overflow: "visible",
  },
  outsideDismiss: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    zIndex: 10,
  },
  inner: {
    width: "100%",
    maxWidth: MAX_CONTENT_WIDTH,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.xl,
    height: 62,
    gap: spacing.md,
    zIndex: 20,
    overflow: "visible",
  },
  brand: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    flexShrink: 0,
  },
  logo: {
    width: 38,
    height: 34,
  },
  brandTop: {
    fontSize: 14,
    fontWeight: "800",
    color: colors.navyDark,
    letterSpacing: 0.5,
  },
  brandSub: {
    fontSize: 10,
    fontWeight: "700",
    color: colors.navy,
    letterSpacing: 0.9,
  },
  navLinks: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flexShrink: 0,
    overflow: "visible",
  },
  menuAnchor: {
    position: "relative",
    zIndex: 30,
    overflow: "visible",
  },
  navItem: {
    paddingHorizontal: 9,
    paddingVertical: 6,
    borderRadius: radii.sm,
  },
  navItemActive: {
    backgroundColor: "rgba(255, 255, 255, 0.35)",
  },
  navText: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.navyDark,
  },
  navTextActive: {
    fontWeight: "800",
    color: colors.navyDark,
  },
  rightCluster: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    flex: 1,
    maxWidth: 430,
    justifyContent: "flex-end",
    overflow: "visible",
  },
  searchWrap: {
    flex: 1,
    maxWidth: 250,
  },
  accountTrigger: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 6,
    maxWidth: 185,
  },
  accountTriggerText: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.navyDark,
  },
  loginTriggerText: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.navyDark,
  },
  dropdown: {
    position: "absolute",
    top: "100%",
    marginTop: 6,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.md,
    paddingVertical: 6,
    minWidth: 225,
    zIndex: 1005,
    ...cardShadow,
  },
  dropdownLeft: {
    left: 0,
  },
  dropdownRight: {
    right: 0,
    minWidth: 235,
  },
  loginPopover: {
    right: 0,
    width: 300,
    padding: spacing.md,
    gap: spacing.sm,
  },
  dropdownItem: {
    paddingHorizontal: spacing.md,
    paddingVertical: 9,
  },
  dropdownItemPressed: {
    backgroundColor: colors.surfaceMuted,
  },
  dropdownItemText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
  },
  dropdownViewAll: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.linkBlue,
  },
  dropdownHint: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textMuted,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
  },
  dropdownDivider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 4,
  },
  accountHeader: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
  },
  accountEmail: {
    fontSize: 13,
    color: colors.textMuted,
    fontWeight: "600",
  },
  logoutText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.danger,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  passwordLabelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 2,
  },
  forgotLink: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.linkBlue,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.sm,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 15,
    fontWeight: "500",
    color: colors.text,
    backgroundColor: colors.surface,
  },
  popoverLoginBtn: {
    marginTop: 4,
    backgroundColor: colors.linkBlue,
    borderRadius: radii.sm,
    paddingVertical: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  btnDisabled: {
    opacity: 0.55,
  },
  popoverLoginBtnText: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.white,
  },
  loginErrBox: {
    backgroundColor: colors.dangerSoft,
    borderWidth: 1,
    borderColor: "#FECACA",
    borderRadius: radii.sm,
    padding: 8,
  },
  loginErrText: {
    fontSize: 13,
    color: colors.danger,
    fontWeight: "600",
  },
  firstTimeWrap: {
    paddingVertical: 2,
  },
  firstTimeText: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textMuted,
  },
});
