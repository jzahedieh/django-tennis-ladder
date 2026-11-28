import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { DivisionGridOut, GridCellOut, GridRowOut } from "../api/types";
import { colors, radii, spacing, useResponsive } from "../theme/tokens";
import type { H2HTarget } from "./H2HSheet";

type SortKey = "default" | "total" | "average";
type SortDir = "desc" | "asc";

const ROW_HEIGHT = 36;
const DESKTOP_ROW_HEIGHT = 46;
const DESKTOP_RANK_W = 50;
const DESKTOP_NAME_W = 205;
const DESKTOP_STAT_W = 92;
const DESKTOP_MIN_CELL_W = 40;

function parseAverage(val: string | number): number {
  const n = parseFloat(String(val));
  return Number.isFinite(n) ? n : 0;
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
  const { width, height, isDesktop } = useResponsive();
  const insets = useSafeAreaInsets();
  const [sortBy, setSortBy] = useState<SortKey>("default");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [landscapeOpen, setLandscapeOpen] = useState(false);
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

  // Mobile layout (clean matrix directly, matching web)
  const nameColWidth = 144;
  const cellWidth = 36;
  const statColWidth = 54;

  const renderMobileCell = (
    row: GridRowOut,
    colRow: GridRowOut,
    colCellW: number,
    rowH: number,
    closeBeforeAction: boolean
  ) => {
    if (row.player_id === colRow.player_id) {
      return (
        <View
          key={`self-${row.player_id}-${colRow.player_id}`}
          style={[
            styles.cell,
            { width: colCellW, height: rowH },
            styles.selfCell,
          ]}
        />
      );
    }

    const cell = cellMapsByPlayer.get(row.player_id)?.get(colRow.player_id);
    const score = cell?.result;
    const isWin = score === 9;

    return (
      <Pressable
        key={`${row.player_id}-${colRow.player_id}`}
        onPress={() => {
          if (closeBeforeAction) setLandscapeOpen(false);
          onPressCell({
            playerId: row.player_id,
            opponentId: colRow.player_id,
            title: `${row.player_name} vs ${colRow.player_name}`,
          });
        }}
        style={({ pressed }) => [
          styles.cell,
          { width: colCellW, height: rowH },
          row.is_current_user && styles.currentUserCell,
          pressed && styles.pressedCell,
        ]}
      >
        {score !== null && score !== undefined ? (
          <Text style={[styles.cellText, isWin && styles.winScoreBold]}>
            {String(score)}
          </Text>
        ) : null}
      </Pressable>
    );
  };

  const renderMatrix = ({
    colNameW,
    colCellW,
    colStatW,
    rowH,
    closeBeforeAction = false,
  }: {
    colNameW: number;
    colCellW: number;
    colStatW: number;
    rowH: number;
    closeBeforeAction?: boolean;
  }) => (
    <View style={styles.matrixOuter}>
      {/* Fixed sticky left player column */}
      <View style={[styles.stickyCol, { width: colNameW }]}>
        <Pressable
          onPress={() => handleSort("default")}
          style={[styles.stickyHeader, styles.headerBg, { height: rowH }]}
          accessibilityLabel="Sort by ladder order"
        >
          <SortGlyph active={sortBy === "default"} dir="asc" />
          <Text style={styles.headerText} numberOfLines={1}>
            Name
          </Text>
        </Pressable>

        {sortedRows.map((row, idx) => (
          <Pressable
            key={row.player_id}
            onPress={() => {
              if (closeBeforeAction) setLandscapeOpen(false);
              router.push(`/player/${row.player_id}`);
            }}
            style={[
              styles.stickyNameCell,
              { height: rowH },
              row.is_current_user && styles.currentUserRowBg,
            ]}
          >
            <Text style={styles.posBadge}>{idx + 1}</Text>
            <Text
              style={[
                styles.playerLinkText,
                row.is_current_user && styles.currentUserNameText,
              ]}
              numberOfLines={1}
            >
              {row.player_name}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Scrollable matrix columns + clickable Avg / Total */}
      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View>
          <View
            style={[styles.scrollHeaderRow, styles.headerBg, { height: rowH }]}
          >
            {sortedRows.map((colRow, colIdx) => (
              <View
                key={`hdr-${colRow.player_id}`}
                style={[styles.colHeaderCell, { width: colCellW, height: rowH }]}
              >
                <Text style={styles.headerText} numberOfLines={1}>
                  {String(colIdx + 1)}
                </Text>
              </View>
            ))}
            <Pressable
              onPress={() => handleSort("average")}
              style={[styles.statHeaderCell, { width: colStatW, height: rowH }]}
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
              style={[styles.statHeaderCell, { width: colStatW, height: rowH }]}
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
            <View
              key={`row-${row.player_id}`}
              style={[styles.scrollDataRow, { height: rowH }]}
            >
              {sortedRows.map((colRow) =>
                renderMobileCell(row, colRow, colCellW, rowH, closeBeforeAction)
              )}
              <View
                style={[
                  styles.statCell,
                  { width: colStatW, height: rowH },
                  row.is_current_user && styles.currentUserCell,
                ]}
              >
                <Text style={styles.statText}>{String(row.average)}</Text>
              </View>
              <View
                style={[
                  styles.statCell,
                  { width: colStatW, height: rowH },
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
  );

  // Landscape modal dimensions (rotated 90deg so long axis is horizontal)
  const landscapeW = Math.max(320, height - insets.top - insets.bottom - 16);
  const landscapeH = Math.max(280, width - insets.left - insets.right - 8);
  const lNameW = 148;
  const lStatW = 54;
  const lInnerW = landscapeW - spacing.md * 2;
  const lCellW = Math.max(
    34,
    Math.floor((lInnerW - lNameW - lStatW * 2 - 2) / Math.max(1, sortedRows.length))
  );

  return (
    <View>
      {renderMatrix({
        colNameW: nameColWidth,
        colCellW: cellWidth,
        colStatW: statColWidth,
        rowH: ROW_HEIGHT,
      })}

      <View style={styles.landscapeBtnRow}>
        <Pressable
          onPress={() => setLandscapeOpen(true)}
          style={styles.landscapeBtn}
        >
          <Ionicons
            name="phone-landscape-outline"
            size={15}
            color={colors.navy}
          />
          <Text style={styles.landscapeBtnText}>Horizontal View</Text>
        </Pressable>
      </View>

      <Modal
        visible={landscapeOpen}
        animationType="fade"
        statusBarTranslucent
        onRequestClose={() => setLandscapeOpen(false)}
      >
        <View style={styles.landscapeBackdrop}>
          <View
            style={[
              styles.landscapeStage,
              {
                width: landscapeW,
                height: landscapeH,
                transform: [{ rotate: "90deg" }],
              },
            ]}
          >
            <View style={styles.landscapeTopBar}>
              <Text style={styles.landscapeTitle}>
                Division {grid.division}
              </Text>
              <Pressable
                onPress={() => setLandscapeOpen(false)}
                style={styles.landscapeCloseBtn}
              >
                <Ionicons name="close" size={18} color={colors.navy} />
                <Text style={styles.landscapeCloseText}>Close</Text>
              </Pressable>
            </View>
            <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator>
              {renderMatrix({
                colNameW: lNameW,
                colCellW: lCellW,
                colStatW: lStatW,
                rowH: 32,
                closeBeforeAction: true,
              })}
            </ScrollView>
          </View>
        </View>
      </Modal>
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
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
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
  landscapeBtnRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: spacing.xs,
  },
  landscapeBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radii.sm,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  landscapeBtnText: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.navy,
  },
  landscapeBackdrop: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: "center",
    justifyContent: "center",
  },
  landscapeStage: {
    backgroundColor: colors.bg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  landscapeTopBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.xs,
  },
  landscapeTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.text,
  },
  landscapeCloseBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radii.sm,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
  },
  landscapeCloseText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.navy,
  },
});
