import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, "body" | "method"> & {
  auth?: boolean;
  body?: unknown;
  retryOn401?: boolean;
};

type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    return null;
  }

  const nextTokens = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };

  setTokens(nextTokens.access_token, nextTokens.refresh_token);
  return nextTokens.access_token;
}

function handleAuthFailure() {
  clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

async function parseError(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string | { detail?: string } };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (data.detail && typeof data.detail === "object" && "detail" in data.detail) {
      return String(data.detail.detail);
    }
  } catch {
    return response.statusText || "Request failed";
  }
  return response.statusText || "Request failed";
}

async function request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, body, retryOn401 = true, headers, ...rest } = options;

  const requestHeaders = new Headers(headers);
  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    const accessToken = getAccessToken();
    if (accessToken) {
      requestHeaders.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    method,
    headers: requestHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && auth && retryOn401) {
    const nextAccessToken = await refreshAccessToken();
    if (!nextAccessToken) {
      handleAuthFailure();
      throw new ApiError("Unauthorized", 401);
    }

    return request<T>(method, path, {
      ...options,
      headers: {
        ...Object.fromEntries(requestHeaders.entries()),
        Authorization: `Bearer ${nextAccessToken}`,
      },
      retryOn401: false,
    });
  }

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get<T>(path: string, options?: RequestOptions) {
    return request<T>("GET", path, options);
  },
  post<T>(path: string, body?: unknown, options?: RequestOptions) {
    return request<T>("POST", path, { ...options, body });
  },
  patch<T>(path: string, body?: unknown, options?: RequestOptions) {
    return request<T>("PATCH", path, { ...options, body });
  },
  delete<T>(path: string, options?: RequestOptions) {
    return request<T>("DELETE", path, options);
  },
};
