import React, { useState } from "react";
import { LayoutChangeEvent, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Polyline, Text as SvgText } from "react-native-svg";

import type { CentilePointOut } from "../api/types";
import { colors, radii, spacing } from "../theme/tokens";

export function CentileHistoryChart({
  data,
}: {
  data: CentilePointOut[];
}) {
  const [chartWidth, setChartWidth] = useState(320);
  const [selectedIdx, setSelectedIdx] = useState<number>(Math.max(0, data.length - 1));

  if (!data.length) return null;

  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    if (w > 120) setChartWidth(w);
  };

  const height = 200;
  const padL = 44;
  const padR = 16;
  const padT = 18;
  const padB = 28;
  const plotW = Math.max(80, chartWidth - padL - padR);
  const plotH = height - padT - padB;

  const xForIdx = (idx: number) => {
    if (data.length === 1) return padL + plotW / 2;
    return padL + (idx / (data.length - 1)) * plotW;
  };
  const yForCentile = (c: number) => padT + plotH - (c / 100) * plotH;

  const points = data
    .map((pt, idx) => `${xForIdx(idx).toFixed(1)},${yForCentile(pt.centile).toFixed(1)}`)
    .join(" ");

  const safeIdx = Math.min(selectedIdx, data.length - 1);
  const active = data[safeIdx];

  return (
    <View onLayout={onLayout} style={styles.wrap}>
      <View style={styles.selectedPill}>
        <Text style={styles.selectedText}>
          {active.season_label} · Div {active.division} · Rank #{active.rank} /{" "}
          {active.total_players} ({active.centile}%)
        </Text>
      </View>

      <Svg width={chartWidth} height={height}>
        {[0, 25, 50, 75, 100].map((val) => {
          const y = yForCentile(val);
          return (
            <React.Fragment key={`y-${val}`}>
              <Line
                x1={padL}
                y1={y}
                x2={padL + plotW}
                y2={y}
                stroke={colors.border}
                strokeWidth={1}
              />
              <SvgText
                x={padL - 6}
                y={y + 4}
                fontSize={12}
                fontWeight="600"
                fill={colors.textMuted}
                textAnchor="end"
              >
                {val}%
              </SvgText>
            </React.Fragment>
          );
        })}

        {data.length > 1 ? (
          <Polyline
            points={points}
            fill="none"
            stroke={colors.courtGreen}
            strokeWidth={2.5}
          />
        ) : null}

        {data.map((pt, idx) => {
          const cx = xForIdx(idx);
          const cy = yForCentile(pt.centile);
          const isActive = idx === safeIdx;
          return (
            <Circle
              key={`${pt.league_id}-${idx}`}
              cx={cx}
              cy={cy}
              r={isActive ? 6 : 4}
              fill={isActive ? colors.navy : colors.courtGreen}
              stroke={colors.white}
              strokeWidth={1.5}
              onPress={() => setSelectedIdx(idx)}
            />
          );
        })}

        {data.length > 0 ? (
          <>
            <SvgText
              x={xForIdx(0)}
              y={height - 8}
              fontSize={12}
              fontWeight="600"
              fill={colors.textMuted}
              textAnchor="start"
            >
              {data[0].season_label}
            </SvgText>
            {data.length > 1 ? (
              <SvgText
                x={xForIdx(data.length - 1)}
                y={height - 8}
                fontSize={12}
                fontWeight="600"
                fill={colors.textMuted}
                textAnchor="end"
              >
                {data[data.length - 1].season_label}
              </SvgText>
            ) : null}
          </>
        ) : null}
      </Svg>

      {data.length > 1 ? (
        <View style={styles.chipRow}>
          {data.slice(-6).map((pt) => {
            const idx = data.findIndex((item) => item.league_id === pt.league_id);
            const activeChip = idx === safeIdx;
            return (
              <Pressable
                key={pt.league_id}
                onPress={() => setSelectedIdx(idx)}
                style={[styles.chip, activeChip && styles.chipActive]}
              >
                <Text style={[styles.chipText, activeChip && styles.chipTextActive]}>
                  {pt.season_label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
  },
  selectedPill: {
    alignSelf: "flex-start",
    backgroundColor: colors.clubBlueSoft,
    paddingHorizontal: spacing.md,
    paddingVertical: 5,
    borderRadius: radii.pill,
    marginBottom: spacing.xs,
  },
  selectedText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.navy,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: spacing.xs,
  },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
  },
  chipActive: {
    backgroundColor: colors.navy,
  },
  chipText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: colors.white,
  },
});
