import { Platform, useWindowDimensions } from "react-native";

export const DESKTOP_BREAKPOINT = 768;
export const MAX_CONTENT_WIDTH = 1180;

export const colors = {
  navy: "#1D3557",
  navyDark: "#12233B",
  clubBlue: "#A2B5D7",
  clubBlueSoft: "#EBF0F8",
  courtGreen: "#1F7A4C",
  courtGreenSoft: "#E6F4EC",
  bg: "#F8FAFC",
  surface: "#FFFFFF",
  surfaceMuted: "#F1F5F9",
  border: "#E2E8F0",
  borderStrong: "#CBD5E1",
  text: "#0F172A",
  textSecondary: "#1E293B",
  textMuted: "#475569",
  winBg: "#DCFCE7",
  winText: "#166534",
  lossBg: "#F1F5F9",
  lossText: "#475569",
  incompleteBg: "#FEF3C7",
  incompleteText: "#B45309",
  retiredBg: "#FEE2E2",
  retiredText: "#B91C1C",
  danger: "#DC2626",
  dangerSoft: "#FEF2F2",
  linkBlue: "#0066B2",
  highlightRow: "#E8F0FE",
  diagonalCell: "#808080",
  white: "#FFFFFF",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radii = {
  sm: 6,
  md: 10,
  lg: 14,
  pill: 999,
} as const;

export const cardShadow = Platform.select({
  web: {
    boxShadow: "0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)",
  },
  default: {
    shadowColor: "#0F172A",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
});

export function useResponsive() {
  const { width, height } = useWindowDimensions();
  const isDesktop = width >= DESKTOP_BREAKPOINT;
  return { width, height, isDesktop };
}
