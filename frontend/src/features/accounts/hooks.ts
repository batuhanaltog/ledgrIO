import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { accountsApi, type AccountInput } from "./api";

export const ACCOUNTS_LIST_KEY = ["accounts", "list"];
export const ACCOUNTS_SUMMARY_KEY = ["accounts", "summary"];

export function useAccounts() {
  return useQuery({ queryKey: ACCOUNTS_LIST_KEY, queryFn: accountsApi.list });
}

export function useAccountsSummary() {
  return useQuery({ queryKey: ACCOUNTS_SUMMARY_KEY, queryFn: accountsApi.summary });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AccountInput) => accountsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}

export function useUpdateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<AccountInput> }) =>
      accountsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => accountsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}
