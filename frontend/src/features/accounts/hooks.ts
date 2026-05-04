import { useQuery } from "@tanstack/react-query";
import { accountsApi } from "./api";

export const ACCOUNTS_LIST_KEY = ["accounts", "list"];
export const ACCOUNTS_SUMMARY_KEY = ["accounts", "summary"];

export function useAccounts() {
  return useQuery({ queryKey: ACCOUNTS_LIST_KEY, queryFn: accountsApi.list });
}

export function useAccountsSummary() {
  return useQuery({ queryKey: ACCOUNTS_SUMMARY_KEY, queryFn: accountsApi.summary });
}
