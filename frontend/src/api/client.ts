import type { ErrorResponse } from "./types";

export class ApiError extends Error {
  status: number;
  payload: ErrorResponse | unknown;

  constructor(message: string, status: number, payload: ErrorResponse | unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const CSRF_COOKIE_NAME = "finance_csrf";
const CSRF_HEADER_NAME = "X-CSRF-Token";

function getCookie(name: string): string | null {
  if (typeof document === "undefined" || !document.cookie) {
    return null;
  }
  const encodedName = encodeURIComponent(name);
  const pairs = document.cookie.split("; ");
  for (const pair of pairs) {
    const [rawKey, ...rest] = pair.split("=");
    if (rawKey === encodedName) {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}

export function getCsrfToken(): string | null {
  return getCookie(CSRF_COOKIE_NAME);
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const isMutatingMethod = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
  const csrfToken = isMutatingMethod ? getCsrfToken() : null;
  const csrfHeaders = csrfToken ? { [CSRF_HEADER_NAME]: csrfToken } : {};

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...csrfHeaders,
      ...options.headers
    }
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text();
    }
    throw new ApiError("Request failed", response.status, payload);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
