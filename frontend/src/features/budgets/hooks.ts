import { useQuery } from "@tanstack/react-query";
import { budgetsApi } from "./api";

export const BUDGETS_KEY = ["budgets"];

export function useBudgets() {
  return useQuery({ queryKey: BUDGETS_KEY, queryFn: budgetsApi.list });
}
