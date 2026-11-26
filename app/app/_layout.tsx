import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { StyleSheet, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "../src/auth/AuthContext";
import { DesktopNavBar } from "../src/components/DesktopNavBar";
import { MobileBottomNav, MobileTopBar } from "../src/components/MobileNavChrome";
import { colors, useResponsive } from "../src/theme/tokens";

function RootShell() {
  const { isDesktop } = useResponsive();

  return (
    <View style={styles.root}>
      <StatusBar style="dark" />
      {isDesktop ? <DesktopNavBar /> : <MobileTopBar />}
      <View style={styles.stackWrap}>
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.bg },
          }}
        >
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="list/index" options={{ title: "Previous Ladders" }} />
          <Stack.Screen name="current" options={{ title: "Current Ladder" }} />
          <Stack.Screen name="result/entry" options={{ title: "Enter Result" }} />
          <Stack.Screen
            name="[year]/round/[round]/index"
            options={{ title: "Season Overview" }}
          />
          <Stack.Screen
            name="[year]/round/[round]/division/[division]"
            options={{ title: "Division" }}
          />
          <Stack.Screen name="player/[id]" options={{ title: "Player Profile" }} />
          <Stack.Screen
            name="head_to_head/[playerId]/vs/[opponentId]"
            options={{ title: "Head-to-Head" }}
          />
          <Stack.Screen name="accounts/login" options={{ title: "Sign In" }} />
          <Stack.Screen name="login" options={{ title: "Sign In" }} />
          <Stack.Screen
            name="reset-password"
            options={{ title: "Set / Reset Password" }}
          />
        </Stack>
      </View>
      {!isDesktop ? <MobileBottomNav /> : null}
    </View>
  );
}

export default function RootLayout() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      })
  );

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <RootShell />
          </AuthProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  stackWrap: {
    flex: 1,
    minHeight: 0,
    zIndex: 1,
  },
});
