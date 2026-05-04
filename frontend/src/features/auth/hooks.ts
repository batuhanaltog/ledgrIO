import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "./api";
import { useAuthStore } from "@/stores/auth";

export const ME_QUERY_KEY = ["auth", "me"] as const;

export function useMe(enabled = true) {
  const access = useAuthStore((s) => s.access);
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: authApi.me,
    enabled: enabled && Boolean(access),
    staleTime: 60_000,
  });
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: async (tokens) => {
      setTokens(tokens);
      const me = await authApi.me();
      setUser(me);
      qc.setQueryData(ME_QUERY_KEY, me);
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (input: {
      email: string;
      password: string;
      default_currency_code: string;
    }) => authApi.register(input.email, input.password, input.default_currency_code),
  });
}

export function useLogout() {
  const { refresh, clear } = useAuthStore.getState();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (refresh) {
        try {
          await authApi.logout(refresh);
        } catch {
          // logout best-effort; tokens are still cleared client-side.
        }
      }
    },
    onSettled: () => {
      clear();
      qc.removeQueries({ queryKey: ME_QUERY_KEY });
    },
  });
}
