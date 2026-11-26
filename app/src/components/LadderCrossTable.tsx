import { useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import type { DivisionGridOut, GridCellOut, GridRowOut } from "../api/types";
import { colors, radii, spacing, useResponsive } from "../theme/tokens";
import type { H2HTarget } from "./H2HSheet";

type SortKey = "default" | "total" | "average";
type SortDir = "desc" | "asc";

const ROW_HEIGHT = 44;
const DESKTOP_ROW_HEIGHT = 46;
const DESKTOP_RANK_W = 50;
const DESKTOP_NAME_W = 205;
const DESKTOP_STAT_W = 92;
const DESKTOP_MIN_CELL_W = 40;

function parseAverage(val: string | number): number {
  const n = parseFloat(String(val));
  return Number.isFinite(n) ? n : 0;
}

function buildPlayerInitials(rows: GridRowOut[]): Map<number, string> {
  const baseCandidates = rows.map((row) => {
    const parts = row.player_name.trim().split(/\s+/).filter(Boolean);
    const first = (parts[0] || "?").replace(/[^a-zA-Z]/g, "");
    const last = (parts.length > 1 ? parts[parts.length - 1] : "").replace(
      /[^a-zA-Z]/g,
      ""
    );
    const f1 = (first[0] || "?").toUpperCase();
    const l1 = (last[0] || first[1] || "").toUpperCase();
    const l2 = (last[1] || "").toLowerCase();
    return {
      playerId: row.player_id,
      base: `${f1}${l1}`,
      extended: l2 ? `${f1}${l1}${l2}` : `${f1}${l1}`,
    };
  });

  const baseCounts = new Map<string, number>();
  for (const item of baseCandidates) {
    baseCounts.set(item.base, (baseCounts.get(item.base) ?? 0) + 1);
  }

  const used = new Set<string>();
  const result = new Map<number, string>();

  for (const item of baseCandidates) {
    let label =
      (baseCounts.get(item.base) ?? 0) > 1 ? item.extended : item.base;
    if (used.has(label)) {
      let suffix = 2;
      while (used.has(`${item.base}${suffix}`)) {
        suffix += 1;
      }
      label = `${item.base}${suffix}`;
    }
    used.add(label);
    result.set(item.playerId, label);
  }

  return result;
}

function SortGlyph({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) {
    return <Text style={styles.sortGlyphIdle}>⇅</Text>;
  }
  return (
    <Text style={styles.sortGlyphActive}>{dir === "desc" ? "▼" : "▲"}</Text>
  );
}

export function LadderCrossTable({
  grid,
  onPressCell,
}: {
  grid: DivisionGridOut;
  onPressCell: (target: H2HTarget) => void;
}) {
  const router = useRouter();
  const { width, isDesktop } = useResponsive();
  const [mobileMode, setMobileMode] = useState<"standings" | "matrix">(
    "matrix"
  );
  const [compactNames, setCompactNames] = useState(false);
  const [sortBy, setSortBy] = useState<SortKey>("default");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [hoveredPair, setHoveredPair] = useState<{
    playerId: number;
    opponentId: number;
  } | null>(null);

  const handleSort = (key: SortKey) => {
    if (key === "default") {
      setSortBy("default");
      setSortDir("desc");
      return;
    }
    if (sortBy === key) {
      setSortDir((prev) => (prev === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  const sortedRows = useMemo(() => {
    const copy = [...grid.rows];
    if (sortBy === "default") {
      return copy.sort((a, b) => a.position - b.position);
    }
    const dir = sortDir === "desc" ? 1 : -1;
    if (sortBy === "total") {
      return copy.sort(
        (a, b) =>
          (b.total - a.total) * dir ||
          (parseAverage(b.average) - parseAverage(a.average)) * dir ||
          a.position - b.position
      );
    }
    return copy.sort(
      (a, b) =>
        (parseAverage(b.average) - parseAverage(a.average)) * dir ||
        (b.total - a.total) * dir ||
        a.position - b.position
    );
  }, [grid.rows, sortBy, sortDir]);

  const initialsMap = useMemo(
    () => buildPlayerInitials(grid.rows),
    [grid.rows]
  );

  const cellMapsByPlayer = useMemo(() => {
    const outer = new Map<number, Map<number, GridCellOut>>();
    for (const row of grid.rows) {
      const inner = new Map<number, GridCellOut>();
      for (const cell of row.cells) {
        inner.set(cell.opponent_id, cell);
      }
      outer.set(row.player_id, inner);
    }
    return outer;
  }, [grid.rows]);

  const sortArrow = (key: "total" | "average") =>
    sortBy === key ? (sortDir === "desc" ? " ▼" : " ▲") : "";

  if (isDesktop) {
    const minTableWidth =
      DESKTOP_RANK_W +
      DESKTOP_NAME_W +
      sortedRows.length * DESKTOP_MIN_CELL_W +
      DESKTOP_STAT_W * 2;
    const needsHorizontalScroll = minTableWidth > width - spacing.xl * 2;

    const desktopTable = (
      <View
        style={[
          styles.desktopTable,
          needsHorizontalScroll && { minWidth: minTableWidth },
        ]}
      >
        {/* Header Row */}
        <View style={styles.desktopHeaderRow}>
          <Pressable
            onPress={() => handleSort("default")}
            style={[styles.desktopRankHeader, styles.desktopCellBorder]}
            accessibilityLabel="Sort by ladder order"
          >
            <SortGlyph active={sortBy === "default"} dir="asc" />
          </Pressable>

          <View style={[styles.desktopNameHeader, styles.desktopCellBorder]}>
            <Text style={styles.desktopHeaderText}>Name</Text>
          </View>

          {sortedRows.map((colRow, colIdx) => (
            <View
              key={`dh-${colRow.player_id}`}
              style={[styles.desktopOppHeader, styles.desktopCellBorder]}
            >
              <Text style={styles.desktopHeaderText}>{colIdx + 1}</Text>
            </View>
          ))}

          <Pressable
            onPress={() => handleSort("average")}
            style={[styles.desktopStatHeader, styles.desktopCellBorder]}
          >
            <SortGlyph active={sortBy === "average"} dir={sortDir} />
            <Text
              style={[
                styles.desktopHeaderText,
                sortBy === "average" && styles.activeHeaderText,
              ]}
            >
              Avg
            </Text>
          </Pressable>

          <Pressable
            onPress={() => handleSort("total")}
            style={styles.desktopStatHeader}
          >
            <SortGlyph active={sortBy === "total"} dir={sortDir} />
            <Text
              style={[
                styles.desktopHeaderText,
                sortBy === "total" && styles.activeHeaderText,
              ]}
            >
              Total
            </Text>
          </Pressable>
        </View>

        {/* Data Rows */}
        {sortedRows.map((row, rowIdx) => {
          const isLastRow = rowIdx === sortedRows.length - 1;
          const rowHighlight = row.is_current_user
            ? styles.currentUserRowBg
            : undefined;
          const borderStyle = isLastRow
            ? styles.desktopBorderRightOnly
            : styles.desktopCellBorder;

          return (
            <View
              key={`dr-${row.player_id}`}
              style={[styles.desktopDataRow, rowHighlight]}
            >
              <View style={[styles.desktopRankCell, borderStyle]}>
                <Text style={styles.desktopRankText}>{rowIdx + 1}</Text>
              </View>

              <Pressable
                onPress={() => router.push(`/player/${row.player_id}`)}
                style={[styles.desktopNameCell, borderStyle]}
              >
                <Text
                  style={[
                    styles.desktopPlayerLink,
                    row.is_current_user && styles.currentUserNameText,
                  ]}
                  numberOfLines={1}
                >
                  {row.player_name}
                </Text>
              </Pressable>

              {sortedRows.map((colRow) => {
                if (row.player_id === colRow.player_id) {
                  return (
                    <View
                      key={`dc-self-${row.player_id}-${colRow.player_id}`}
                      style={[
                        styles.desktopScoreCell,
                        borderStyle,
                        styles.selfCellDesktop,
                      ]}
                    />
                  );
                }

                const cell = cellMapsByPlayer
                  .get(row.player_id)
                  ?.get(colRow.player_id);
                const score = cell?.result;
                const isWin = score === 9;
                const isMirrorOrHovered =
                  hoveredPair !== null &&
                  ((hoveredPair.playerId === row.player_id &&
                    hoveredPair.opponentId === colRow.player_id) ||
                    (hoveredPair.playerId === colRow.player_id &&
                      hoveredPair.opponentId === row.player_id));

                return (
                  <Pressable
                    key={`dc-${row.player_id}-${colRow.player_id}`}
                    onHoverIn={() =>
                      setHoveredPair({
                        playerId: row.player_id,
                        opponentId: colRow.player_id,
                      })
                    }
                    onHoverOut={() =>
                      setHoveredPair((curr) =>
                        curr &&
                        curr.playerId === row.player_id &&
                        curr.opponentId === colRow.player_id
                          ? null
                          : curr
                      )
                    }
                    onPress={() =>
                      onPressCell({
                        playerId: row.player_id,
                        opponentId: colRow.player_id,
                        title: `${row.player_name} vs ${colRow.player_name}`,
                      })
                    }
                    style={({ pressed }) => [
                      styles.desktopScoreCell,
                      borderStyle,
                      isMirrorOrHovered && styles.mirrorHoverCell,
                      pressed && styles.pressedCell,
                    ]}
                  >
                    {score !== null && score !== undefined ? (
                      <Text
                        style={[
                          styles.desktopScoreText,
                          isWin && styles.winScoreBold,
                        ]}
                      >
                        {String(score)}
                      </Text>
                    ) : null}
                  </Pressable>
                );
              })}

              <View style={[styles.desktopStatCell, borderStyle]}>
                <Text style={styles.desktopStatText}>
                  {String(row.average)}
                </Text>
              </View>

              <View
                style={[
                  styles.desktopStatCell,
                  !isLastRow && styles.desktopBorderBottomOnly,
                ]}
              >
                <Text style={styles.desktopTotalText}>{row.total}</Text>
              </View>
            </View>
          );
        })}
      </View>
    );

    return needsHorizontalScroll ? (
      <ScrollView horizontal showsHorizontalScrollIndicator>
        {desktopTable}
      </ScrollView>
    ) : (
      desktopTable
    );
  }

  // Mobile layout
  const showStandings = mobileMode === "standings";
  const nameColWidth = compactNames ? 66 : 138;
  const cellWidth = compactNames ? 38 : 44;
  const statColWidth = compactNames ? 50 : 58;

  const renderMobileCell = (row: GridRowOut, colRow: GridRowOut) => {
    if (row.player_id === colRow.player_id) {
      return (
        <View
          key={`self-${row.player_id}-${colRow.player_id}`}
          style={[styles.cell, { width: cellWidth }, styles.selfCell]}
        />
      );
    }

    const cell = cellMapsByPlayer.get(row.player_id)?.get(colRow.player_id);
    const score = cell?.result;
    const isWin = score === 9;

    return (
      <Pressable
        key={`${row.player_id}-${colRow.player_id}`}
        onPress={() =>
          onPressCell({
            playerId: row.player_id,
            opponentId: colRow.player_id,
            title: `${row.player_name} vs ${colRow.player_name}`,
          })
        }
        style={({ pressed }) => [
          styles.cell,
          { width: cellWidth },
          row.is_current_user && styles.currentUserCell,
          pressed && styles.pressedCell,
        ]}
      >
        {score !== null && score !== undefined ? (
          <Text
            style={[
              styles.cellText,
              compactNames && styles.cellTextCompact,
              isWin && styles.winScoreBold,
            ]}
          >
            {String(score)}
          </Text>
        ) : null}
      </Pressable>
    );
  };

  return (
    <View>
      {/* Mobile Controls Toolbar */}
      <View style={styles.toolbar}>
        <View style={styles.toggleWrap}>
          <Pressable
            onPress={() => setMobileMode("matrix")}
            style={[
              styles.toggleBtn,
              mobileMode === "matrix" && styles.toggleBtnActive,
            ]}
          >
            <Text
              style={[
                styles.toggleText,
                mobileMode === "matrix" && styles.toggleTextActive,
              ]}
            >
              Matrix
            </Text>
          </Pressable>
          <Pressable
            onPress={() => setMobileMode("standings")}
            style={[
              styles.toggleBtn,
              mobileMode === "standings" && styles.toggleBtnActive,
            ]}
          >
            <Text
              style={[
                styles.toggleText,
                mobileMode === "standings" && styles.toggleTextActive,
              ]}
            >
              Standings
            </Text>
          </Pressable>
        </View>

        {!showStandings ? (
          <View style={styles.toggleWrap}>
            <Pressable
              onPress={() => setCompactNames(false)}
              style={[
                styles.toggleBtn,
                !compactNames && styles.toggleBtnActive,
              ]}
            >
              <Text
                style={[
                  styles.toggleText,
                  !compactNames && styles.toggleTextActive,
                ]}
              >
                Names
              </Text>
            </Pressable>
            <Pressable
              onPress={() => setCompactNames(true)}
              style={[
                styles.toggleBtn,
                compactNames && styles.toggleBtnActive,
              ]}
            >
              <Text
                style={[
                  styles.toggleText,
                  compactNames && styles.toggleTextActive,
                ]}
              >
                Initials
              </Text>
            </Pressable>
          </View>
        ) : null}

        <View style={styles.sortPills}>
          {(
            [
              ["default", "Order"],
              ["average", `Avg${sortArrow("average")}`],
              ["total", `Total${sortArrow("total")}`],
            ] as const
          ).map(([key, label]) => {
            const active = sortBy === key;
            return (
              <Pressable
                key={key}
                onPress={() => handleSort(key)}
                style={[styles.sortPill, active && styles.sortPillActive]}
              >
                <Text
                  style={[
                    styles.sortPillText,
                    active && styles.sortPillTextActive,
                  ]}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {showStandings ? (
        <View style={styles.standingsTable}>
          <View style={[styles.standingsRow, styles.headerBg]}>
            <Text style={[styles.headerText, { width: 28 }]}>#</Text>
            <Text style={[styles.headerText, { flex: 1 }]}>Name</Text>
            <Text style={[styles.headerText, styles.numCol]}>Pl</Text>
            <Pressable
              onPress={() => handleSort("average")}
              style={styles.numColBtn}
            >
              <Text
                style={[
                  styles.headerText,
                  sortBy === "average" && styles.activeHeaderText,
                ]}
              >
                Avg{sortArrow("average")}
              </Text>
            </Pressable>
            <Pressable
              onPress={() => handleSort("total")}
              style={styles.numColBtn}
            >
              <Text
                style={[
                  styles.headerText,
                  sortBy === "total" && styles.activeHeaderText,
                ]}
              >
                Total{sortArrow("total")}
              </Text>
            </Pressable>
          </View>

          {sortedRows.map((row, idx) => (
            <Pressable
              key={row.player_id}
              onPress={() => router.push(`/player/${row.player_id}`)}
              style={[
                styles.standingsRow,
                row.is_current_user && styles.currentUserRowBg,
              ]}
            >
              <Text style={[styles.rankText, { width: 28 }]}>{idx + 1}</Text>
              <Text
                style={[
                  styles.playerLinkText,
                  row.is_current_user && styles.currentUserNameText,
                  { flex: 1 },
                ]}
                numberOfLines={1}
              >
                {row.player_name}
              </Text>
              <Text style={[styles.statText, styles.numCol]}>
                {row.matches_played}
              </Text>
              <Text style={[styles.statText, styles.numCol]}>
                {String(row.average)}
              </Text>
              <Text style={[styles.ptsText, styles.numCol]}>{row.total}</Text>
            </Pressable>
          ))}
        </View>
      ) : (
        <View style={styles.matrixOuter}>
          {/* Fixed sticky left player column */}
          <View style={[styles.stickyCol, { width: nameColWidth }]}>
            <Pressable
              onPress={() => setCompactNames((prev) => !prev)}
              style={[styles.stickyHeader, styles.headerBg]}
            >
              <Text style={styles.headerText} numberOfLines={1}>
                {compactNames ? "Init ▶" : "Name ◀"}
              </Text>
            </Pressable>

            {sortedRows.map((row, idx) => (
              <Pressable
                key={row.player_id}
                onPress={() => router.push(`/player/${row.player_id}`)}
                style={[
                  styles.stickyNameCell,
                  row.is_current_user && styles.currentUserRowBg,
                ]}
              >
                <Text style={styles.posBadge}>{idx + 1}</Text>
                <Text
                  style={[
                    styles.playerLinkText,
                    row.is_current_user && styles.currentUserNameText,
                    compactNames && styles.compactInitialText,
                  ]}
                  numberOfLines={1}
                >
                  {compactNames
                    ? initialsMap.get(row.player_id)
                    : row.player_name}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Scrollable matrix columns + clickable Avg / Total */}
          <ScrollView horizontal showsHorizontalScrollIndicator>
            <View>
              <View style={[styles.scrollHeaderRow, styles.headerBg]}>
                {sortedRows.map((colRow, colIdx) => (
                  <View
                    key={`hdr-${colRow.player_id}`}
                    style={[styles.colHeaderCell, { width: cellWidth }]}
                  >
                    <Text style={styles.headerText} numberOfLines={1}>
                      {String(colIdx + 1)}
                    </Text>
                  </View>
                ))}
                <Pressable
                  onPress={() => handleSort("average")}
                  style={[styles.statHeaderCell, { width: statColWidth }]}
                >
                  <Text
                    style={[
                      styles.headerText,
                      sortBy === "average" && styles.activeHeaderText,
                    ]}
                    numberOfLines={1}
                  >
                    Avg{sortArrow("average")}
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => handleSort("total")}
                  style={[styles.statHeaderCell, { width: statColWidth }]}
                >
                  <Text
                    style={[
                      styles.headerText,
                      sortBy === "total" && styles.activeHeaderText,
                    ]}
                    numberOfLines={1}
                  >
                    Total{sortArrow("total")}
                  </Text>
                </Pressable>
              </View>

              {sortedRows.map((row) => (
                <View key={`row-${row.player_id}`} style={styles.scrollDataRow}>
                  {sortedRows.map((colRow) => renderMobileCell(row, colRow))}
                  <View
                    style={[
                      styles.statCell,
                      { width: statColWidth },
                      row.is_current_user && styles.currentUserCell,
                    ]}
                  >
                    <Text style={styles.statText}>{String(row.average)}</Text>
                  </View>
                  <View
                    style={[
                      styles.statCell,
                      { width: statColWidth },
                      row.is_current_user && styles.currentUserCell,
                    ]}
                  >
                    <Text style={styles.ptsText}>{row.total}</Text>
                  </View>
                </View>
              ))}
            </View>
          </ScrollView>
        </View>
      )}
    </View>
  );
}

const GRID_BORDER = "#DEE2E6";

const styles = StyleSheet.create({
  // Desktop crisp 100%-width cross-table (aligned with live Bootstrap table)
  desktopTable: {
    width: "100%",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: GRID_BORDER,
  },
  desktopCellBorder: {
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: GRID_BORDER,
  },
  desktopBorderRightOnly: {
    borderRightWidth: 1,
    borderColor: GRID_BORDER,
  },
  desktopBorderBottomOnly: {
    borderBottomWidth: 1,
    borderColor: GRID_BORDER,
  },
  desktopHeaderRow: {
    flexDirection: "row",
    height: DESKTOP_ROW_HEIGHT,
    backgroundColor: colors.surface,
  },
  desktopDataRow: {
    flexDirection: "row",
    height: DESKTOP_ROW_HEIGHT,
    backgroundColor: colors.surface,
  },
  desktopRankHeader: {
    width: DESKTOP_RANK_W,
    justifyContent: "center",
    alignItems: "flex-end",
    paddingRight: 8,
  },
  desktopNameHeader: {
    width: DESKTOP_NAME_W,
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  desktopOppHeader: {
    flex: 1,
    minWidth: DESKTOP_MIN_CELL_W,
    justifyContent: "center",
    alignItems: "center",
  },
  desktopStatHeader: {
    width: DESKTOP_STAT_W,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 6,
  },
  desktopHeaderText: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
  },
  sortGlyphIdle: {
    fontSize: 13,
    color: "#64748B",
  },
  sortGlyphActive: {
    fontSize: 12,
    color: colors.navy,
    fontWeight: "800",
  },
  desktopRankCell: {
    width: DESKTOP_RANK_W,
    justifyContent: "center",
    alignItems: "flex-end",
    paddingRight: 10,
  },
  desktopRankText: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  desktopNameCell: {
    width: DESKTOP_NAME_W,
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  desktopPlayerLink: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.linkBlue,
  },
  desktopScoreCell: {
    flex: 1,
    minWidth: DESKTOP_MIN_CELL_W,
    justifyContent: "center",
    alignItems: "center",
  },
  selfCellDesktop: {
    backgroundColor: colors.diagonalCell,
  },
  mirrorHoverCell: {
    backgroundColor: "#DCE4EE",
  },
  desktopScoreText: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  desktopStatCell: {
    width: DESKTOP_STAT_W,
    justifyContent: "center",
    alignItems: "center",
  },
  desktopStatText: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  desktopTotalText: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  currentUserNameText: {
    fontWeight: "800",
  },
  winScoreBold: {
    fontWeight: "800",
  },

  // Mobile toolbar + matrix/standings styles
  toolbar: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  toggleWrap: {
    flexDirection: "row",
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    padding: 3,
  },
  toggleBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.sm,
  },
  toggleBtnActive: {
    backgroundColor: colors.surface,
  },
  toggleText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
  },
  toggleTextActive: {
    color: colors.navy,
    fontWeight: "700",
  },
  sortPills: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginLeft: "auto",
  },
  sortPill: {
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sortPillActive: {
    backgroundColor: colors.navy,
    borderColor: colors.navy,
  },
  sortPillText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  sortPillTextActive: {
    color: colors.white,
  },
  matrixOuter: {
    flexDirection: "row",
    borderWidth: 1,
    borderColor: GRID_BORDER,
    borderRadius: radii.sm,
    overflow: "hidden",
    backgroundColor: colors.surface,
  },
  stickyCol: {
    borderRightWidth: 1,
    borderRightColor: GRID_BORDER,
    zIndex: 2,
  },
  headerBg: {
    backgroundColor: colors.surfaceMuted,
  },
  stickyHeader: {
    height: ROW_HEIGHT,
    justifyContent: "center",
    paddingHorizontal: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: GRID_BORDER,
  },
  stickyNameCell: {
    height: ROW_HEIGHT,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 6,
    borderBottomWidth: 1,
    borderBottomColor: GRID_BORDER,
  },
  posBadge: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    width: 18,
    textAlign: "center",
  },
  playerLinkText: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.linkBlue,
    flex: 1,
  },
  compactInitialText: {
    fontSize: 13,
    fontWeight: "800",
    textAlign: "center",
  },
  scrollHeaderRow: {
    flexDirection: "row",
    height: ROW_HEIGHT,
    borderBottomWidth: 1,
    borderBottomColor: GRID_BORDER,
  },
  colHeaderCell: {
    justifyContent: "center",
    alignItems: "center",
    borderRightWidth: 1,
    borderRightColor: GRID_BORDER,
    paddingHorizontal: 2,
  },
  statHeaderCell: {
    justifyContent: "center",
    alignItems: "center",
    borderRightWidth: 1,
    borderRightColor: GRID_BORDER,
    paddingHorizontal: 2,
  },
  headerText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.text,
  },
  activeHeaderText: {
    color: colors.navy,
    fontWeight: "800",
  },
  scrollDataRow: {
    flexDirection: "row",
    height: ROW_HEIGHT,
  },
  cell: {
    height: ROW_HEIGHT,
    justifyContent: "center",
    alignItems: "center",
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: GRID_BORDER,
    backgroundColor: colors.surface,
  },
  selfCell: {
    backgroundColor: colors.diagonalCell,
    borderColor: "#6B7280",
  },
  currentUserRowBg: {
    backgroundColor: colors.highlightRow,
  },
  currentUserCell: {
    backgroundColor: colors.highlightRow,
  },
  pressedCell: {
    backgroundColor: colors.clubBlueSoft,
  },
  cellText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  cellTextCompact: {
    fontSize: 14,
  },
  statCell: {
    height: ROW_HEIGHT,
    justifyContent: "center",
    alignItems: "center",
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: GRID_BORDER,
    backgroundColor: colors.surface,
  },
  ptsText: {
    fontSize: 14,
    fontWeight: "800",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  statText: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  standingsTable: {
    borderWidth: 1,
    borderColor: GRID_BORDER,
    borderRadius: radii.sm,
    overflow: "hidden",
    backgroundColor: colors.surface,
  },
  standingsRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: 11,
    borderBottomWidth: 1,
    borderBottomColor: GRID_BORDER,
    gap: spacing.sm,
  },
  rankText: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.text,
  },
  numCol: {
    width: 54,
    textAlign: "right",
  },
  numColBtn: {
    width: 54,
    alignItems: "flex-end",
  },
});
