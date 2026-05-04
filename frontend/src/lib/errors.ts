import axios, { type AxiosError } from "axios";

export type ApiErrorType =
  | "VALIDATION_ERROR"
  | "AUTHENTICATION_FAILED"
  | "NOT_FOUND"
  | "PERMISSION_DENIED"
  | "CONFLICT"
  | "RATE_LIMITED"
  | "STALE_FX_RATE"
  | "INTERNAL_ERROR"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export interface ParsedApiError {
  type: ApiErrorType;
  status: number;
  message: string;
  fieldErrors?: Record<string, string>;
  raw?: unknown;
}

interface BackendEnvelope {
  error?: {
    type?: string;
    detail?: unknown;
    status?: number;
  };
  detail?: unknown;
}

function flattenDetail(detail: unknown): {
  message: string;
  fieldErrors?: Record<string, string>;
} {
  if (typeof detail === "string") return { message: detail };
  if (Array.isArray(detail)) return { message: detail.map(String).join(" ") };
  if (detail && typeof detail === "object") {
    const fieldErrors: Record<string, string> = {};
    for (const [k, v] of Object.entries(detail)) {
      if (Array.isArray(v)) fieldErrors[k] = v.map(String).join(" ");
      else if (typeof v === "string") fieldErrors[k] = v;
      else fieldErrors[k] = JSON.stringify(v);
    }
    const message = Object.values(fieldErrors).join(" ") || "Request failed.";
    return { message, fieldErrors };
  }
  return { message: "Request failed." };
}

export function parseApiError(err: unknown): ParsedApiError {
  if (!axios.isAxiosError(err)) {
    return {
      type: "UNKNOWN",
      status: 0,
      message: err instanceof Error ? err.message : "Unexpected error.",
    };
  }
  const axiosErr = err as AxiosError<BackendEnvelope>;
  if (!axiosErr.response) {
    return {
      type: "NETWORK_ERROR",
      status: 0,
      message: "Network error. Please check your connection.",
    };
  }
  const { status, data } = axiosErr.response;
  const envelope = data?.error;
  const rawDetail = envelope?.detail ?? data?.detail ?? "Request failed.";
  const { message, fieldErrors } = flattenDetail(rawDetail);

  const type = (envelope?.type ?? statusToType(status)) as ApiErrorType;
  return { type, status, message, fieldErrors, raw: data };
}

function statusToType(status: number): ApiErrorType {
  if (status === 400) return "VALIDATION_ERROR";
  if (status === 401) return "AUTHENTICATION_FAILED";
  if (status === 403) return "PERMISSION_DENIED";
  if (status === 404) return "NOT_FOUND";
  if (status === 409) return "CONFLICT";
  if (status === 429) return "RATE_LIMITED";
  if (status >= 500) return "INTERNAL_ERROR";
  return "UNKNOWN";
}
