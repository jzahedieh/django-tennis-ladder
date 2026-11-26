import React, { useEffect, useMemo, useState } from "react";
import {
  GestureResponderEvent,
  LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import Svg, {
  Circle,
  Line,
  Path,
  Polyline,
  Rect,
  Text as SvgText,
} from "react-native-svg";

import type { SeasonProgressOut } from "../api/types";
import { colors, radii, spacing } from "../theme/tokens";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function parseDateOnly(iso: string): Date {
  const parts = iso.split(/[-T]/);
  if (parts.length >= 3) {
    return new Date(
      parseInt(parts[0], 10),
      parseInt(parts[1], 10) - 1,
      parseInt(parts[2], 10)
    );
  }
  const dt = new Date(iso);
  return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
}

function addDays(base: Date, days: number): Date {
  const dt = new Date(base.getFullYear(), base.getMonth(), base.getDate());
  dt.setDate(dt.getDate() + days);
  return dt;
}

function formatShortDate(dt: Date): string {
  return `${dt.getDate()} ${MONTHS[dt.getMonth()]}`;
}

function formatWeekdayDate(dt: Date): string {
  return `${WEEKDAYS[dt.getDay()]} ${dt.getDate()} ${MONTHS[dt.getMonth()]}`;
}

interface DayEntry {
  day: number;
  daily: number;
  cumulative: number;
  dateLabel: string;
  shortDate: string;
}

export function SeasonProgressChart({
  progress,
}: {
  progress: SeasonProgressOut;
}) {
  const { width: windowWidth } = useWindowDimensions();
  const [chartWidth, setChartWidth] = useState(() =>
    Math.max(220, Math.min(windowWidth - 64, 600))
  );

  const entries = useMemo<DayEntry[]>(() => {
    const start = parseDateOnly(progress.season_start);
    const list: DayEntry[] = [];
    for (let i = 0; i < progress.played_days.length; i += 1) {
      const day = progress.played_days[i];
      const dt = addDays(start, day);
      list.push({
        day,
        daily: progress.played[i] ?? 0,
        cumulative: progress.played_cumulative[i] ?? 0,
        dateLabel: formatWeekdayDate(dt),
        shortDate: formatShortDate(dt),
      });
    }
    return list;
  }, [progress]);

  const [selectedIdx, setSelectedIdx] = useState<number | null>(() =>
    entries.length > 0 ? entries.length - 1 : null
  );

  useEffect(() => {
    setSelectedIdx(entries.length > 0 ? entries.length - 1 : null);
  }, [entries.length]);

  const onLayout = (e: LayoutChangeEvent) => {
    const w = Math.floor(e.nativeEvent.layout.width);
    if (w > 120) setChartWidth(w);
  };

  const height = 224;
  const padL = 44;
  const padR = 34;
  const padT = 28;
  const padB = 30;
  const plotW = Math.max(80, chartWidth - padL - padR);
  const plotH = height - padT - padB;

  const maxDay = Math.max(1, progress.season_days[1] ?? 60);
  const totalSeasonMatches = Math.max(
    1,
    progress.season_total_matches[1] ?? 1
  );
  const maxMatches = Math.max(
    totalSeasonMatches,
    ...(progress.played_cumulative.length ? progress.played_cumulative : [0])
  );

  const maxDaily = Math.max(
    1,
    ...(progress.played.length ? progress.played : [0])
  );
  const maxDailyAxis = Math.max(4, Math.ceil(maxDaily * 1.6));

  const xForDay = (day: number) =>
    padL + (Math.max(0, Math.min(day, maxDay)) / maxDay) * plotW;
  const yForVal = (val: number) =>
    padT + plotH - (Math.max(0, val) / maxMatches) * plotH;
  const yForDaily = (val: number) =>
    padT + plotH - (Math.max(0, val) / maxDailyAxis) * plotH;

  const cumulativePoints = entries
    .map((e) => `${xForDay(e.day).toFixed(1)},${yForVal(e.cumulative).toFixed(1)}`)
    .join(" ");

  const areaPath =
    entries.length > 0
      ? `M ${xForDay(entries[0].day).toFixed(1)} ${yForVal(0).toFixed(1)} ` +
        entries
          .map(
            (e) =>
              `L ${xForDay(e.day).toFixed(1)} ${yForVal(e.cumulative).toFixed(1)}`
          )
          .join(" ") +
        ` L ${xForDay(entries[entries.length - 1].day).toFixed(1)} ${yForVal(
          0
        ).toFixed(1)} Z`
      : "";

  const todayX = xForDay(progress.today_day);
  const todayLabelX = Math.min(
    padL + plotW - 22,
    Math.max(padL + 22, todayX)
  );
  const barWidth = Math.max(4, Math.min(10, plotW / Math.max(maxDay, 14)));

  const startDt = parseDateOnly(progress.season_start);
  const midDay = Math.round(maxDay / 2);
  const xTicks = [
    { day: 0, label: formatShortDate(startDt), anchor: "start" as const },
    {
      day: midDay,
      label: formatShortDate(addDays(startDt, midDay)),
      anchor: "middle" as const,
    },
    {
      day: maxDay,
      label: formatShortDate(addDays(startDt, maxDay)),
      anchor: "end" as const,
    },
  ];

  const y2Ticks = [0, Math.round(maxDailyAxis / 2), maxDailyAxis];

  const selectNearestFromLocationX = (locX: number) => {
    if (entries.length === 0) return;
    const clampedX = Math.max(0, Math.min(plotW, locX));
    const targetDay = (clampedX / plotW) * maxDay;
    let bestIdx = 0;
    let bestDist = Infinity;
    for (let i = 0; i < entries.length; i += 1) {
      const dist = Math.abs(entries[i].day - targetDay);
      if (dist < bestDist) {
        bestDist = dist;
        bestIdx = i;
      }
    }
    setSelectedIdx(bestIdx);
  };

  const handleTouch = (e: GestureResponderEvent) => {
    selectNearestFromLocationX(e.nativeEvent.locationX ?? 0);
  };

  const safeIdx =
    selectedIdx !== null && selectedIdx >= 0 && selectedIdx < entries.length
      ? selectedIdx
      : null;
  const activeEntry = safeIdx !== null ? entries[safeIdx] : null;

  return (
    <View onLayout={onLayout} style={styles.wrap}>
      {/* Interactive Readout Strip */}
      {activeEntry ? (
        <View style={styles.readoutBar}>
          <View style={styles.readoutLeft}>
            <Pressable
              onPress={() =>
                setSelectedIdx((prev) =>
                  prev !== null ? Math.max(0, prev - 1) : 0
                )
              }
              disabled={safeIdx === 0}
              style={[styles.stepBtn, safeIdx === 0 && styles.stepBtnDisabled]}
            >
              <Text style={styles.stepBtnText}>‹</Text>
            </Pressable>
            <View>
              <Text style={styles.readoutDate}>{activeEntry.dateLabel}</Text>
              <Text style={styles.readoutHint}>
                Day {activeEntry.day} · Tap or drag chart
              </Text>
            </View>
            <Pressable
              onPress={() =>
                setSelectedIdx((prev) =>
                  prev !== null
                    ? Math.min(entries.length - 1, prev + 1)
                    : entries.length - 1
                )
              }
              disabled={safeIdx === entries.length - 1}
              style={[
                styles.stepBtn,
                safeIdx === entries.length - 1 && styles.stepBtnDisabled,
              ]}
            >
              <Text style={styles.stepBtnText}>›</Text>
            </Pressable>
          </View>

          <View style={styles.readoutBadges}>
            <View style={styles.dailyPill}>
              <Text style={styles.dailyPillText}>
                +{activeEntry.daily}{" "}
                {activeEntry.daily === 1 ? "match" : "matches"}
              </Text>
            </View>
            <View style={styles.cumPill}>
              <Text style={styles.cumPillText}>
                {activeEntry.cumulative} / {totalSeasonMatches}
              </Text>
            </View>
          </View>
        </View>
      ) : (
        <View style={styles.readoutEmpty}>
          <Text style={styles.readoutHint}>
            No daily match totals recorded yet in this round.
          </Text>
        </View>
      )}

      {/* Clipped Responsive Chart */}
      <View style={styles.svgContainer}>
        <Svg
          width={chartWidth}
          height={height}
          viewBox={`0 0 ${chartWidth} ${height}`}
        >
          {/* Left Y Gridlines + Cumulative Labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
            const val = Math.round(maxMatches * frac);
            const y = yForVal(val);
            return (
              <React.Fragment key={`grid-${frac}`}>
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
                  {val}
                </SvgText>
              </React.Fragment>
            );
          })}

          {/* Right Y2 Daily Labels */}
          {y2Ticks.map((val, idx) => (
            <SvgText
              key={`y2-${idx}-${val}`}
              x={padL + plotW + 6}
              y={yForDaily(val) + 4}
              fontSize={12}
              fontWeight="600"
              fill={colors.textMuted}
              textAnchor="start"
            >
              {val}
            </SvgText>
          ))}

          {/* Target Pace Diagonal */}
          <Line
            x1={xForDay(0)}
            y1={yForVal(0)}
            x2={xForDay(maxDay)}
            y2={yForVal(totalSeasonMatches)}
            stroke={colors.clubBlue}
            strokeWidth={1.5}
            strokeDasharray="5,4"
          />

          {/* Today Marker */}
          <Line
            x1={todayX}
            y1={padT - 4}
            x2={todayX}
            y2={padT + plotH}
            stroke={colors.incompleteText}
            strokeWidth={1.25}
            strokeDasharray="3,3"
          />
          <SvgText
            x={todayLabelX}
            y={padT - 10}
            fontSize={12}
            fontWeight="bold"
            fill={colors.incompleteText}
            textAnchor="middle"
          >
            Today
          </SvgText>

          {/* Daily Match Bars (Y2 Scaled) */}
          {entries.map((e, idx) => {
            if (e.daily <= 0) return null;
            const barTop = yForDaily(e.daily);
            const barH = Math.max(3, padT + plotH - barTop);
            const isActive = idx === safeIdx;
            return (
              <Rect
                key={`bar-${e.day}-${idx}`}
                x={xForDay(e.day) - barWidth / 2}
                y={barTop}
                width={barWidth}
                height={barH}
                rx={2}
                fill={colors.navy}
                opacity={isActive ? 1 : 0.38}
              />
            );
          })}

          {/* Cumulative Area & Polyline */}
          {areaPath ? (
            <Path d={areaPath} fill="rgba(31, 122, 76, 0.12)" />
          ) : null}
          {cumulativePoints ? (
            <Polyline
              points={cumulativePoints}
              fill="none"
              stroke={colors.courtGreen}
              strokeWidth={2.5}
            />
          ) : null}

          {/* Selected Day Crosshair & Active Dot */}
          {activeEntry ? (
            <>
              <Line
                x1={xForDay(activeEntry.day)}
                y1={padT}
                x2={xForDay(activeEntry.day)}
                y2={padT + plotH}
                stroke={colors.navy}
                strokeWidth={1}
                strokeDasharray="2,2"
                opacity={0.5}
              />
              <Circle
                cx={xForDay(activeEntry.day)}
                cy={yForVal(activeEntry.cumulative)}
                r={5.5}
                fill={colors.courtGreen}
                stroke={colors.white}
                strokeWidth={2}
              />
            </>
          ) : null}

          {/* X Axis Date Ticks */}
          {xTicks.map((t, idx) => (
            <SvgText
              key={`x-${idx}-${t.day}`}
              x={xForDay(t.day)}
              y={height - 8}
              fontSize={12}
              fontWeight="600"
              fill={colors.textMuted}
              textAnchor={t.anchor}
            >
              {t.label}
            </SvgText>
          ))}
        </Svg>

        {/* Interactive Touch/Drag Overlay */}
        {entries.length > 0 ? (
          <View
            style={[
              styles.touchOverlay,
              { left: padL, top: padT, width: plotW, height: plotH },
            ]}
            onStartShouldSetResponder={() => true}
            onMoveShouldSetResponder={() => true}
            onResponderGrant={handleTouch}
            onResponderMove={handleTouch}
          />
        ) : null}
      </View>

      <View style={styles.legend}>
        <LegendItem color={colors.courtGreen} label="Cumulative played" />
        <LegendItem color={colors.clubBlue} label="Target pace" dashed />
        <LegendItem color={colors.navy} label="Daily matches (right)" />
      </View>
    </View>
  );
}

function LegendItem({
  color,
  label,
  dashed = false,
}: {
  color: string;
  label: string;
  dashed?: boolean;
}) {
  return (
    <View style={styles.legendItem}>
      <View
        style={[
          styles.legendSwatch,
          { backgroundColor: dashed ? "transparent" : color, borderColor: color },
          dashed && styles.legendDashed,
        ]}
      />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: "100%",
  },
  readoutBar: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    paddingHorizontal: spacing.sm,
    paddingVertical: 7,
    marginBottom: spacing.xs,
  },
  readoutLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  stepBtn: {
    width: 28,
    height: 28,
    borderRadius: radii.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  stepBtnDisabled: {
    opacity: 0.4,
  },
  stepBtnText: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.navy,
    lineHeight: 18,
  },
  readoutDate: {
    fontSize: 15,
    fontWeight: "800",
    color: colors.text,
  },
  readoutHint: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.textMuted,
  },
  readoutEmpty: {
    marginBottom: spacing.xs,
  },
  readoutBadges: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  dailyPill: {
    backgroundColor: colors.navy,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.pill,
  },
  dailyPillText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.white,
  },
  cumPill: {
    backgroundColor: colors.courtGreenSoft,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.pill,
  },
  cumPillText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.courtGreen,
  },
  svgContainer: {
    position: "relative",
    width: "100%",
    overflow: "hidden",
  },
  touchOverlay: {
    position: "absolute",
    backgroundColor: "transparent",
  },
  legend: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    justifyContent: "center",
    marginTop: spacing.xs,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  legendSwatch: {
    width: 14,
    height: 4,
    borderRadius: 2,
  },
  legendDashed: {
    borderTopWidth: 2,
    borderStyle: "dashed",
    height: 0,
  },
  legendText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textMuted,
  },
});
