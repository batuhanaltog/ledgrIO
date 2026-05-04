import { api } from "@/lib/api";
import type { AuthUser } from "@/stores/auth";

export interface TokenPair {
  access: string;
  refresh: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenPair>("/auth/login/", { email, password }).then((r) => r.data),
  register: (email: string, password: string, default_currency_code: string) =>
    api
      .post<AuthUser>("/auth/register/", { email, password, default_currency_code })
      .then((r) => r.data),
  logout: (refresh: string) =>
    api.post("/auth/logout/", { refresh }).then((r) => r.data),
  me: () => api.get<AuthUser>("/users/me/").then((r) => r.data),
  verifyEmail: (token: string) =>
    api
      .post<{ email: string; is_email_verified: boolean }>("/auth/verify-email/", { token })
      .then((r) => r.data),
  passwordResetRequest: (email: string) =>
    api.post<{ detail: string }>("/auth/password-reset/request/", { email }).then((r) => r.data),
  passwordResetConfirm: (token: string, new_password: string) =>
    api
      .post<{ detail: string }>("/auth/password-reset/confirm/", { token, new_password })
      .then((r) => r.data),
};
