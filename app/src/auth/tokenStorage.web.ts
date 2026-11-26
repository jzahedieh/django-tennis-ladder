import type { TokenStorage } from "./tokenStorage";

export const tokenStorage: TokenStorage = {
  async getRefreshToken() {
    return null;
  },
  async setRefreshToken(_token: string) {
    // Web refresh tokens live in HttpOnly cookies managed by the API.
  },
  async clearRefreshToken() {
    // Cleared server-side via POST /v1/auth/logout.
  },
};
