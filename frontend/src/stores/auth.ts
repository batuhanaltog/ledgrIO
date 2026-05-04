import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface AuthUser {
  id: number;
  email: string;
  default_currency_code: string;
  is_email_verified: boolean;
  profile?: {
    timezone: string;
    locale: string;
    monthly_income: string | null;
  };
}

interface AuthState {
  access: string | null;
  refresh: string | null;
  user: AuthUser | null;
  setTokens: (tokens: { access: string; refresh: string }) => void;
  setAccess: (access: string) => void;
  setUser: (user: AuthUser | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      access: null,
      refresh: null,
      user: null,
      setTokens: ({ access, refresh }) => set({ access, refresh }),
      setAccess: (access) => set({ access }),
      setUser: (user) => set({ user }),
      clear: () => set({ access: null, refresh: null, user: null }),
    }),
    {
      name: "ledgrio.auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ access: s.access, refresh: s.refresh, user: s.user }),
    },
  ),
);
