import Constants from "expo-constants";
import { Platform } from "react-native";

const PROD_API_URL = "https://api.highgate-ladder.co.uk";

export function getApiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }

  if (Platform.OS === "web") {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      if (host === "localhost" || host === "127.0.0.1") {
        return "http://localhost:8000";
      }
      if (/^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[0-1])\./.test(host)) {
        return `http://${host}:8000`;
      }
    }
    return PROD_API_URL;
  }

  if (!__DEV__) {
    return PROD_API_URL;
  }

  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as unknown as { expoGoConfig?: { debuggerHost?: string } })
      .expoGoConfig?.debuggerHost;

  if (hostUri) {
    const lanHost = hostUri.split(":")[0];
    if (lanHost) {
      return `http://${lanHost}:8000`;
    }
  }

  return "http://localhost:8000";
}
