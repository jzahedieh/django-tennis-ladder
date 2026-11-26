import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { apiClient, extractApiError } from "../../src/api/client";
import { useAuth } from "../../src/auth/AuthContext";
import { H2HSheet, type H2HTarget } from "../../src/components/H2HSheet";
import { LadderCrossTable } from "../../src/components/LadderCrossTable";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  LoadingState,
  PageScroll,
  SectionHeader,
} from "../../src/components/ui";
import { colors, radii, spacing } from "../../src/theme/tokens";
import { formatDateRange } from "../../src/utils/dates";

export default function CurrentLadderScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [selectedDiv, setSelectedDiv] = useState<number | null>(null);
  const [h2hTarget, setH2HTarget] = useState<H2HTarget | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["current-overview", user?.id ?? "anon"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/v1/ladder/seasons/current/overview"
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load current ladder."));
      }
      return data;
    },
  });

  const seasonMeta = overviewQuery.data?.season;

  const seasonQuery = useQuery({
    queryKey: [
      "season-detail",
      seasonMeta?.year,
      seasonMeta?.season_round,
      user?.id ?? "anon",
    ],
    enabled: Boolean(seasonMeta),
    queryFn: async () => {
      if (!seasonMeta) throw new Error("No active season");
      const { data, error } = await apiClient.GET(
        "/v1/ladder/seasons/{year}/round/{season_round}/",
        {
          params: {
            path: {
              year: seasonMeta.year,
              season_round: seasonMeta.season_round,
            },
          },
        }
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load divisions."));
      }
      return data;
    },
  });

  if (overviewQuery.isLoading || seasonQuery.isLoading) {
    return (
      <PageScroll>
        <LoadingState label="Loading divisions..." />
      </PageScroll>
    );
  }

  const err = overviewQuery.error || seasonQuery.error;
  if (err || !seasonQuery.data) {
    return (
      <PageScroll>
        <ErrorState
          message={(err as Error)?.message || "Could not load divisions."}
          onRetry={() => {
            void overviewQuery.refetch();
            void seasonQuery.refetch();
          }}
        />
      </PageScroll>
    );
  }

  const { season, divisions } = seasonQuery.data;
  const visibleDivisions =
    selectedDiv === null
      ? divisions
      : divisions.filter((d) => d.division === selectedDiv);

  return (
    <PageScroll>
      <Card>
        <View style={styles.headerRow}>
          <View style={{ flex: 1, minWidth: 200 }}>
            <Text style={styles.title}>{season.name}</Text>
            <Text style={styles.subtitle}>
              {formatDateRange(season.start_date, season.end_date)}
            </Text>
          </View>
          <Button
            label="Previous Ladders →"
            variant="outline"
            size="sm"
            onPress={() => router.push("/list")}
          />
        </View>

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
      </Card>

      {visibleDivisions.map((div) => (
        <Card key={div.ladder_id}>
          <SectionHeader
            title={`Division ${div.division}`}
            subtitle={div.ladder_type || undefined}
            right={
              <Pressable
                onPress={() =>
                  router.push(
                    `/${season.year}/round/${season.season_round}/division/${div.division}`
                  )
                }
              >
                <Badge label="Division Details →" variant="blue" />
              </Pressable>
            }
          />
          <LadderCrossTable grid={div} onPressCell={setH2HTarget} />
        </Card>
      ))}

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
    marginBottom: spacing.md,
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
  jumpRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  jumpChip: {
    paddingHorizontal: spacing.md,
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
});
