import { useQuery } from "@tanstack/react-query";
import { transactionsApi } from "./api";

export const RECENT_TRANSACTIONS_KEY = ["transactions", "recent"];
export const TRANSACTION_SUMMARY_KEY = ["transactions", "summary"];

export function useRecentTransactions() {
  return useQuery({
    queryKey: RECENT_TRANSACTIONS_KEY,
    queryFn: () => transactionsApi.list({ ordering: "-date", page_size: 10 }),
  });
}

export function useTransactionSummary(params?: Record<string, string>) {
  return useQuery({
    queryKey: [...TRANSACTION_SUMMARY_KEY, params],
    queryFn: () => transactionsApi.summary(params),
  });
}
