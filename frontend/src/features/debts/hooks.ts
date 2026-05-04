import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { debtsApi, type DebtInput, type DebtUpdateInput, type PaymentInput } from "./api";
import { ACCOUNTS_LIST_KEY, ACCOUNTS_SUMMARY_KEY } from "@/features/accounts/hooks";

export const DEBTS_KEY = ["debts"];

export function useDebts() {
  return useQuery({ queryKey: DEBTS_KEY, queryFn: debtsApi.list });
}

export function useCreateDebt() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (data: DebtInput) => debtsApi.create(data), onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }) });
}

export function useUpdateDebt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DebtUpdateInput }) => debtsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }),
  });
}

export function useDeleteDebt() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => debtsApi.delete(id), onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }) });
}

export function useAddPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ debtId, data }: { debtId: number; data: PaymentInput }) => debtsApi.addPayment(debtId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DEBTS_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}
