import { Ionicons } from "@expo/vector-icons";
import { usePathname, useRouter } from "expo-router";
import React from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, radii, spacing } from "../theme/tokens";
import { PlayerSearchBar } from "./PlayerSearchBar";

const ROOT_TAB_PATHS = new Set([
  "/",
  "/index",
  "/ladder",
  "/enter",
  "/stats",
  "/account",
]);

interface MobileTabDef {
  key: string;
  label: string;
  href: string;
  icon: keyof typeof Ionicons.glyphMap;
  iconActive: keyof typeof Ionicons.glyphMap;
  accessibilityLabel?: string;
  isActive: (pathname: string) => boolean;
}

const MOBILE_TABS: MobileTabDef[] = [
  {
    key: "home",
    label: "Home",
    href: "/",
    icon: "home-outline",
    iconActive: "home",
    isActive: (p) => p === "/" || p === "" || p === "/index",
  },
  {
    key: "ladder",
    label: "Ladder",
    href: "/ladder",
    icon: "grid-outline",
    iconActive: "grid",
    isActive: (p) =>
      p.startsWith("/ladder") ||
      p.startsWith("/current") ||
      p.startsWith("/list") ||
      /^\/\d{4}\/round/.test(p),
  },
  {
    key: "enter",
    label: "Enter",
    href: "/enter",
    icon: "add-circle-outline",
    iconActive: "add-circle",
    accessibilityLabel: "Enter Score",
    isActive: (p) => p.startsWith("/enter") || p.startsWith("/result/entry"),
  },
  {
    key: "stats",
    label: "Stats",
    href: "/stats",
    icon: "bar-chart-outline",
    iconActive: "bar-chart",
    isActive: (p) => p.startsWith("/stats"),
  },
  {
    key: "account",
    label: "Account",
    href: "/account",
    icon: "person-outline",
    iconActive: "person",
    isActive: (p) =>
      p.startsWith("/account") ||
      p.startsWith("/login") ||
      p.startsWith("/accounts") ||
      p.startsWith("/reset-password"),
  },
];

export function MobileTopBar() {
  const router = useRouter();
  const pathname = usePathname();
  const showBack = !ROOT_TAB_PATHS.has(pathname || "/") && router.canGoBack();

  return (
    <SafeAreaView edges={["top"]} style={styles.topSafe}>
      <View style={styles.topRow}>
        {showBack ? (
          <Pressable
            onPress={() => router.back()}
            style={({ pressed }) => [
              styles.backBtn,
              pressed && styles.pressedFade,
            ]}
            hitSlop={8}
            accessibilityLabel="Go back"
          >
            <Ionicons name="arrow-back" size={24} color={colors.navyDark} />
          </Pressable>
        ) : null}

        <Pressable
          onPress={() => router.navigate("/" as never)}
          style={({ pressed }) => [
            styles.logoBtn,
            pressed && styles.pressedFade,
          ]}
          accessibilityLabel="Highgate Home"
        >
          <Image
            source={require("../../assets/highgate-logo.png")}
            style={styles.logo}
            resizeMode="contain"
          />
        </Pressable>

        <View style={styles.searchWrap}>
          <PlayerSearchBar compact />
        </View>
      </View>
    </SafeAreaView>
  );
}

export function MobileBottomNav() {
  const router = useRouter();
  const pathname = usePathname() || "/";

  return (
    <SafeAreaView edges={["bottom"]} style={styles.bottomSafe}>
      <View style={styles.bottomBar}>
        {MOBILE_TABS.map((tab) => {
          const active = tab.isActive(pathname);
          const color = active ? colors.navy : colors.textMuted;
          return (
            <Pressable
              key={tab.key}
              onPress={() => router.navigate(tab.href as never)}
              style={({ pressed }) => [
                styles.tabBtn,
                pressed && styles.pressedFade,
              ]}
              accessibilityRole="tab"
              accessibilityLabel={tab.accessibilityLabel ?? tab.label}
              accessibilityState={{ selected: active }}
            >
              <Ionicons
                name={active ? tab.iconActive : tab.icon}
                size={22}
                color={color}
              />
              <Text
                style={[
                  styles.tabLabel,
                  { color },
                  active && styles.tabLabelActive,
                ]}
                numberOfLines={1}
              >
                {tab.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  topSafe: {
    backgroundColor: colors.clubBlue,
    borderBottomWidth: 1,
    borderBottomColor: "#8EA4CE",
    zIndex: 1000,
    elevation: 10,
    overflow: "visible",
  },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    overflow: "visible",
  },
  backBtn: {
    width: 34,
    height: 34,
    borderRadius: radii.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  logoBtn: {
    flexShrink: 0,
    paddingVertical: 2,
    paddingHorizontal: 2,
  },
  logo: {
    width: 34,
    height: 30,
  },
  searchWrap: {
    flex: 1,
    overflow: "visible",
  },
  bottomSafe: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    zIndex: 50,
  },
  bottomBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    height: 62,
    paddingHorizontal: spacing.xs,
  },
  tabBtn: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 6,
    gap: 2,
  },
  tabLabel: {
    fontSize: 12,
    fontWeight: "700",
  },
  tabLabelActive: {
    fontWeight: "800",
  },
  pressedFade: {
    opacity: 0.72,
  },
});
