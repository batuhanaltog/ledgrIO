import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { transactionsApi, type TransactionInput } from "./api";

export const TRANSACTIONS_LIST_KEY = ["transactions", "list"];
export const RECENT_TRANSACTIONS_KEY = ["transactions", "recent"];
export const TRANSACTION_SUMMARY_KEY = ["transactions", "summary"];

export function useTransactions(params?: Record<string, string | number>) {
  return useQuery({
    queryKey: [...TRANSACTIONS_LIST_KEY, params],
    queryFn: () => transactionsApi.list(params),
  });
}

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

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: TRANSACTIONS_LIST_KEY });
  qc.invalidateQueries({ queryKey: RECENT_TRANSACTIONS_KEY });
  qc.invalidateQueries({ queryKey: TRANSACTION_SUMMARY_KEY });
  qc.invalidateQueries({ queryKey: ["accounts", "list"] });
  qc.invalidateQueries({ queryKey: ["accounts", "summary"] });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TransactionInput) => transactionsApi.create(data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: Partial<TransactionInput>;
    }) => transactionsApi.update(id, data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => transactionsApi.delete(id),
    onSuccess: () => invalidateAll(qc),
  });
}
