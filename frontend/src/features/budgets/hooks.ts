import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { budgetsApi, type BudgetInput } from "./api";

export const BUDGETS_KEY = ["budgets"];

export function useBudgets() {
  return useQuery({ queryKey: BUDGETS_KEY, queryFn: budgetsApi.list });
}

export function useCreateBudget() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (data: BudgetInput) => budgetsApi.create(data), onSuccess: () => qc.invalidateQueries({ queryKey: BUDGETS_KEY }) });
}

export function useUpdateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BudgetInput> }) => budgetsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BUDGETS_KEY }),
  });
}

export function useDeleteBudget() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => budgetsApi.delete(id), onSuccess: () => qc.invalidateQueries({ queryKey: BUDGETS_KEY }) });
}
