import { useQueryClient } from "@tanstack/react-query";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { Platform } from "react-native";

import {
  apiClient,
  clearSession,
  extractApiError,
  refreshSession,
  registerAuthListeners,
  setAccessToken,
} from "../api/client";
import type { UserMeOut } from "../api/types";
import { tokenStorage } from "./tokenStorage";

interface AuthContextValue {
  user: UserMeOut | null;
  isHydrating: boolean;
  login: (email: string, password: string) => Promise<UserMeOut>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<UserMeOut | null>(null);
  const [isHydrating, setIsHydrating] = useState(true);

  useEffect(() => {
    registerAuthListeners({
      onSessionUpdated: (updatedUser) => {
        setUser(updatedUser);
      },
      onAuthInvalidated: () => {
        setUser(null);
      },
    });
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const hasNativeToken =
          Platform.OS !== "web" ? Boolean(await tokenStorage.getRefreshToken()) : true;
        if (!hasNativeToken) {
          return;
        }
        const refreshed = await refreshSession();
        if (active && refreshed) {
          setUser(refreshed.user);
        }
      } finally {
        if (active) {
          setIsHydrating(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string): Promise<UserMeOut> => {
      const { data, error } = await apiClient.POST("/v1/auth/login", {
        body: {
          email: email.trim(),
          password,
          device_label: Platform.OS,
        },
      });
      if (error || !data) {
        throw new Error(extractApiError(error, "Invalid email or password."));
      }

      setAccessToken(data.access_token);
      if (data.refresh_token) {
        await tokenStorage.setRefreshToken(data.refresh_token);
      }
      setUser(data.user);
      await queryClient.invalidateQueries();
      return data.user;
    },
    [queryClient]
  );

  const logout = useCallback(async () => {
    try {
      const refreshToken = await tokenStorage.getRefreshToken();
      await apiClient.POST("/v1/auth/logout", {
        body: refreshToken ? { refresh_token: refreshToken } : undefined,
      });
    } catch {
      // Clear local state regardless of network failure.
    } finally {
      await clearSession();
      setUser(null);
      await queryClient.invalidateQueries();
    }
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    const { data } = await apiClient.GET("/v1/auth/me");
    if (data) {
      setUser(data);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isHydrating,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
