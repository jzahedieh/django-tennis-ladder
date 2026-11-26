import * as SecureStore from "expo-secure-store";

import type { TokenStorage } from "./tokenStorage";

const STORAGE_KEY = "hg_refresh_token";

export const tokenStorage: TokenStorage = {
  async getRefreshToken() {
    return SecureStore.getItemAsync(STORAGE_KEY);
  },
  async setRefreshToken(token: string) {
    await SecureStore.setItemAsync(STORAGE_KEY, token);
  },
  async clearRefreshToken() {
    await SecureStore.deleteItemAsync(STORAGE_KEY);
  },
};
