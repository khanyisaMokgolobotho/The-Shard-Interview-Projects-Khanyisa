const ACCESS_TOKEN_KEY = "resolveza.access_token";
const REFRESH_TOKEN_KEY = "resolveza.refresh_token";

export type DecodedToken = {
  sub: string;
  role: string;
  exp: number;
};

function hasWindow() {
  return typeof window !== "undefined";
}

function decodeBase64Url(value: string) {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = `${base64}${"=".repeat((4 - (base64.length % 4)) % 4)}`;
  return atob(padded);
}

export function setAuthMarkerCookie() {
  if (!hasWindow()) {
    return;
  }
  document.cookie = "rzauth=1; path=/; SameSite=Strict";
}

export function clearAuthMarkerCookie() {
  if (!hasWindow()) {
    return;
  }
  document.cookie = "rzauth=; path=/; Max-Age=0; SameSite=Strict";
}

export function setTokens(access: string, refresh: string) {
  if (!hasWindow()) {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  setAuthMarkerCookie();
}

export function getAccessToken() {
  if (!hasWindow()) {
    return null;
  }
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  if (!hasWindow()) {
    return null;
  }
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearTokens() {
  if (!hasWindow()) {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  clearAuthMarkerCookie();
}

export function decodeToken(token: string): DecodedToken | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) {
      return null;
    }
    return JSON.parse(decodeBase64Url(payload)) as DecodedToken;
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  const token = getAccessToken();
  if (!token) {
    return false;
  }
  const decoded = decodeToken(token);
  if (!decoded?.exp) {
    return false;
  }
  return decoded.exp * 1000 > Date.now();
}

export function getCurrentUser() {
  const token = getAccessToken();
  if (!token) {
    return null;
  }
  const decoded = decodeToken(token);
  if (!decoded) {
    return null;
  }
  return {
    id: decoded.sub,
    role: decoded.role,
  };
}
