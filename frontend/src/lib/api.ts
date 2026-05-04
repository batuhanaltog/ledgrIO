import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/stores/auth";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// --- Request interceptor: attach access token ----------------------------
api.interceptors.request.use((config) => {
  const access = useAuthStore.getState().access;
  if (access && !config.headers["Authorization"]) {
    config.headers["Authorization"] = `Bearer ${access}`;
  }
  return config;
});

// --- Response interceptor: refresh-queue on 401 --------------------------
type Retryable = InternalAxiosRequestConfig & { _retried?: boolean };

let refreshing: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const { refresh, setAccess, clear } = useAuthStore.getState();
  if (!refresh) {
    clear();
    return null;
  }
  try {
    const r = await axios.post<{ access: string }>(`${baseURL}/auth/refresh/`, { refresh });
    setAccess(r.data.access);
    return r.data.access;
  } catch {
    clear();
    return null;
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as Retryable | undefined;
    const status = error.response?.status;

    // Don't try to refresh on the refresh endpoint itself, or auth endpoints.
    const url = original?.url ?? "";
    const isAuthEndpoint =
      url.includes("/auth/login") ||
      url.includes("/auth/refresh") ||
      url.includes("/auth/register");

    if (status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true;
      refreshing = refreshing ?? performRefresh();
      const newAccess = await refreshing;
      refreshing = null;
      if (newAccess) {
        original.headers = original.headers ?? {};
        original.headers["Authorization"] = `Bearer ${newAccess}`;
        return api.request(original);
      }
      // Refresh failed: bubble the original 401 up; UI redirects to /login.
    }
    return Promise.reject(error);
  },
);

export type { AxiosRequestConfig };
