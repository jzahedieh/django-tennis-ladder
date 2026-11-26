import type { ConfigContext, ExpoConfig } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "Highgate Competitions",
  slug: "highgate-competitions",
  scheme: "highgate",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light",
  runtimeVersion: {
    policy: "appVersion",
  },
  plugins: ["expo-router", "expo-secure-store"],
  experiments: {
    typedRoutes: true,
  },
  ios: {
    supportsTablet: true,
    bundleIdentifier: "uk.co.highgateladder.competitions",
  },
  android: {
    package: "uk.co.highgateladder.competitions",
    adaptiveIcon: {
      foregroundImage: "./assets/icon.png",
      backgroundColor: "#1D3557",
    },
  },
  web: {
    bundler: "metro",
    output: "single",
    favicon: "./assets/highgate-logo.png",
    name: "Highgate Competitions",
    shortName: "Highgate",
    display: "standalone",
    backgroundColor: "#F8FAFC",
    themeColor: "#1D3557",
  },
});
