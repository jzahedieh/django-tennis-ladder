import createClient from "openapi-fetch";
import { Platform } from "react-native";

import { tokenStorage } from "../auth/tokenStorage";
import { getApiBaseUrl } from "./config";
import type { paths } from "./schema";
import type { TokenOut, UserMeOut } from "./types";

let accessToken: string | null = null;
let refreshInFlight: Promise<TokenOut | null> | null = null;
let authInvalidatedListener: (() => void) | null = null;
let sessionUpdatedListener: ((user: UserMeOut) => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function registerAuthListeners(listeners: {
  onSessionUpdated?: (user: UserMeOut) => void;
  onAuthInvalidated?: () => void;
}): void {
  sessionUpdatedListener = listeners.onSessionUpdated ?? null;
  authInvalidatedListener = listeners.onAuthInvalidated ?? null;
}

async function readBodyText(req: Request): Promise<string | undefined> {
  if (req.method === "GET" || req.method === "HEAD") {
    return undefined;
  }
  try {
    const text = await req.clone().text();
    return text.length > 0 ? text : undefined;
  } catch {
    const raw = (req as unknown as { _bodyText?: string })._bodyText;
    return typeof raw === "string" && raw.length > 0 ? raw : undefined;
  }
}

function buildRequestWithAuth(
  original: Request,
  bodyText: string | undefined,
  token: string | null
): Request {
  const headers = new Headers(original.headers);
  if (Platform.OS === "web") {
    headers.set("X-Client-Platform", "web");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }

  return new Request(original.url, {
    method: original.method,
    headers,
    body: bodyText,
    credentials: Platform.OS === "web" ? "include" : "omit",
  });
}

export async function clearSession(): Promise<void> {
  accessToken = null;
  await tokenStorage.clearRefreshToken();
}

export async function refreshSession(): Promise<TokenOut | null> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const storedRefresh = await tokenStorage.getRefreshToken();

      if (Platform.OS !== "web" && !storedRefresh) {
        return null;
      }

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (Platform.OS === "web") {
        headers["X-Client-Platform"] = "web";
      }

      const res = await globalThis.fetch(`${baseUrl}/v1/auth/refresh`, {
        method: "POST",
        headers,
        body:
          Platform.OS !== "web" && storedRefresh
            ? JSON.stringify({ refresh_token: storedRefresh })
            : undefined,
        credentials: Platform.OS === "web" ? "include" : "omit",
      });

      if (!res.ok) {
        await clearSession();
        authInvalidatedListener?.();
        return null;
      }

      const data = (await res.json()) as TokenOut;
      accessToken = data.access_token;
      if (data.refresh_token) {
        await tokenStorage.setRefreshToken(data.refresh_token);
      }
      sessionUpdatedListener?.(data.user);
      return data;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

const customFetch = async (input: Request): Promise<Response> => {
  const bodyText = await readBodyText(input);
  const urlPath = input.url;
  const isAuthEndpoint =
    urlPath.includes("/v1/auth/login") ||
    urlPath.includes("/v1/auth/refresh") ||
    urlPath.includes("/v1/auth/logout");

  const hadToken = Boolean(accessToken);
  const initialReq = buildRequestWithAuth(input, bodyText, accessToken);
  const res = await globalThis.fetch(initialReq);

  if (res.status !== 401 || isAuthEndpoint || !hadToken) {
    return res;
  }

  const refreshed = await refreshSession();
  if (!refreshed?.access_token) {
    return res;
  }

  const retryReq = buildRequestWithAuth(
    input,
    bodyText,
    refreshed.access_token
  );
  return globalThis.fetch(retryReq);
};

export const apiClient = createClient<paths>({
  baseUrl: getApiBaseUrl(),
  fetch: customFetch,
});

export function extractApiError(
  error: unknown,
  fallback = "Something went wrong. Please try again."
): string {
  if (!error || typeof error !== "object") return fallback;
  const maybeDetail = (error as { detail?: unknown }).detail;
  if (typeof maybeDetail === "string" && maybeDetail.trim()) {
    return maybeDetail;
  }
  if (Array.isArray(maybeDetail) && maybeDetail.length > 0) {
    const first = maybeDetail[0] as { msg?: string };
    if (typeof first?.msg === "string") return first.msg;
  }
  return fallback;
}
