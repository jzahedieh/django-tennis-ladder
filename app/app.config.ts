import type { ConfigContext, ExpoConfig } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  owner: "jz-apps",
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
  updates: {
    url: "https://u.expo.dev/1b1a5f8a-4327-439c-a4dd-1f599f8b0cb9",
  },
  extra: {
    ...(config.extra ?? {}),
    eas: {
      projectId: "1b1a5f8a-4327-439c-a4dd-1f599f8b0cb9",
    },
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
