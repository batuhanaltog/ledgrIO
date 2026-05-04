import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { recurringApi, type RecurringInput } from "./api";

export const RECURRING_KEY = ["recurring"];

export function useRecurring() {
  return useQuery({ queryKey: RECURRING_KEY, queryFn: recurringApi.list });
}

export function useCreateRecurring() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (data: RecurringInput) => recurringApi.create(data), onSuccess: () => qc.invalidateQueries({ queryKey: RECURRING_KEY }) });
}

export function useUpdateRecurring() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<RecurringInput & { is_active: boolean }> }) => recurringApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: RECURRING_KEY }),
  });
}

export function useDeleteRecurring() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => recurringApi.delete(id), onSuccess: () => qc.invalidateQueries({ queryKey: RECURRING_KEY }) });
}
