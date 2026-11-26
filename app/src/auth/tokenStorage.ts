import { Platform } from "react-native";

export interface TokenStorage {
  getRefreshToken(): Promise<string | null>;
  setRefreshToken(token: string): Promise<void>;
  clearRefreshToken(): Promise<void>;
}

const STORAGE_KEY = "hg_refresh_token";

export const tokenStorage: TokenStorage = {
  async getRefreshToken() {
    if (Platform.OS === "web") return null;
    const SecureStore = await import("expo-secure-store");
    return SecureStore.getItemAsync(STORAGE_KEY);
  },
  async setRefreshToken(token: string) {
    if (Platform.OS === "web") return;
    const SecureStore = await import("expo-secure-store");
    await SecureStore.setItemAsync(STORAGE_KEY, token);
  },
  async clearRefreshToken() {
    if (Platform.OS === "web") return;
    const SecureStore = await import("expo-secure-store");
    await SecureStore.deleteItemAsync(STORAGE_KEY);
  },
};
