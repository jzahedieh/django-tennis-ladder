import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../../../src/api/client";
import { useAuth } from "../../../../src/auth/AuthContext";
import { H2HSheet, type H2HTarget } from "../../../../src/components/H2HSheet";
import { LadderCrossTable } from "../../../../src/components/LadderCrossTable";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  LoadingState,
  PageScroll,
  SectionHeader,
} from "../../../../src/components/ui";
import { colors, radii, spacing, useResponsive } from "../../../../src/theme/tokens";
import { formatDateRange } from "../../../../src/utils/dates";

function paramNum(v: string | string[] | undefined): number {
  const s = Array.isArray(v) ? v[0] : v;
  return Number(s || 0);
}

export default function SeasonDetailScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { isDesktop } = useResponsive();
  const params = useLocalSearchParams<{ year: string; round: string }>();
  const year = paramNum(params.year);
  const seasonRound = paramNum(params.round);
  const [selectedDiv, setSelectedDiv] = useState<number | null>(null);
  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["season-detail", year, seasonRound, user?.id ?? "anon"],
    enabled: year > 0 && seasonRound > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/v1/ladder/seasons/{year}/round/{season_round}/",
        {
          params: { path: { year, season_round: seasonRound } },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load season."));
      }
      return data;
    },
  });

  if (isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading season grids..." />
      </PageScroll>
    );
  }

  if (error || !data) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Season not found."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  const { season, divisions } = data;
  const visibleDivisions =
    selectedDiv === null
      ? divisions
      : divisions.filter((d) => d.division === selectedDiv);

  const headerContent = (
    <>
      <View style={styles.headerRow}>
        <View style={{ flex: 1, minWidth: 200 }}>
          <Text style={[styles.title, isDesktop && styles.titleDesktop]}>
            {season.year} Round {season.season_round}
          </Text>
          <Text style={[styles.subtitle, isDesktop && styles.subtitleDesktop]}>
            {formatDateRange(season.start_date, season.end_date)}
            {!isDesktop ? ` · ${divisions.length} Divisions` : ""}
          </Text>
        </View>
        <View style={styles.actions}>
          {season.is_closed ? (
            <Badge label="Closed" variant="amber" />
          ) : (
            <Badge label="Active" variant="green" />
          )}
          <Button
            label="Round Stats"
            variant="outline"
            size="sm"
            onPress={() => router.push(`/stats?season=${season.id}`)}
          />
        </View>
      </View>

      {divisions.length > 1 ? (
        <View style={styles.jumpRow}>
          <Pressable
            onPress={() => setSelectedDiv(null)}
            style={[
              styles.jumpChip,
              selectedDiv === null && styles.jumpChipActive,
            ]}
          >
            <Text
              style={[
                styles.jumpText,
                selectedDiv === null && styles.jumpTextActive,
              ]}
            >
              All ({divisions.length})
            </Text>
          </Pressable>
          {divisions.map((div) => (
            <Pressable
              key={div.ladder_id}
              onPress={() => setSelectedDiv(div.division)}
              style={[
                styles.jumpChip,
                selectedDiv === div.division && styles.jumpChipActive,
              ]}
            >
              <Text
                style={[
                  styles.jumpText,
                  selectedDiv === div.division && styles.jumpTextActive,
                ]}
              >
                Div {div.division}
              </Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </>
  );

  return (
    <PageScroll desktopClean={isDesktop}>
      {isDesktop ? (
        <View style={styles.desktopHeader}>{headerContent}</View>
      ) : (
        <Card>{headerContent}</Card>
      )}

      {visibleDivisions.map((div) =>
        isDesktop ? (
          <View key={div.ladder_id} style={styles.desktopDivSection}>
            <Pressable
              onPress={() =>
                router.push(
                  `/${year}/round/${seasonRound}/division/${div.division}`
                )
              }
              style={styles.desktopDivLinkRow}
            >
              <Text style={styles.desktopDivLink}>
                Division: {div.division}
              </Text>
            </Pressable>
            <LadderCrossTable grid={div} onPressCell={setH2HTarget} />
          </View>
        ) : (
          <Card key={div.ladder_id}>
            <SectionHeader
              title={`Division ${div.division}`}
              subtitle={div.ladder_type || undefined}
              right={
                <Pressable
                  onPress={() =>
                    router.push(
                      `/${year}/round/${seasonRound}/division/${div.division}`
                    )
                  }
                >
                  <Badge label="Division Details →" variant="blue" />
                </Pressable>
              }
            />
            <LadderCrossTable grid={div} onPressCell={setH2HTarget} />
          </Card>
        )
      )}

      <H2HSheet target={h2hTarget} onClose={() => setH2HTarget(null)} />
    </PageScroll>
  );
}

const styles = StyleSheet.create({
  desktopHeader: {
    paddingBottom: spacing.xs,
  },
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
  titleDesktop: {
    fontSize: 32,
    fontWeight: "700",
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.textMuted,
    marginTop: 2,
  },
  subtitleDesktop: {
    fontSize: 17,
    fontWeight: "500",
    marginTop: 4,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  jumpRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: spacing.md,
  },
  jumpChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
  },
  jumpChipActive: {
    backgroundColor: colors.navy,
    borderColor: colors.navy,
  },
  jumpText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  jumpTextActive: {
    color: colors.white,
  },
  desktopDivSection: {
    marginBottom: spacing.md,
    gap: 6,
  },
  desktopDivLinkRow: {
    alignSelf: "flex-start",
  },
  desktopDivLink: {
    fontSize: 20,
    fontWeight: "700",
    color: colors.linkBlue,
  },
});
