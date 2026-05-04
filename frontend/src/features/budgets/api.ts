import { api } from "@/lib/api";

export interface BudgetCategory { id: number; name: string; color: string; icon: string; }

export interface Budget {
  id: number; name: string; category: BudgetCategory | null;
  amount: string; date_from: string; date_to: string;
  alert_threshold: string | null; alert_sent_at: string | null;
  spent: string; remaining: string; usage_pct: string | null;
  created_at: string;
}

export interface PaginatedBudgets { results: Budget[]; count: number; }

export interface BudgetInput {
  name: string; category_id?: number | null; amount: string;
  date_from: string; date_to: string; alert_threshold?: string | null;
}

export const budgetsApi = {
  list: () => api.get<PaginatedBudgets>("/budgets/").then((r) => r.data),
  create: (data: BudgetInput) => api.post<Budget>("/budgets/", data).then((r) => r.data),
  update: (id: number, data: Partial<BudgetInput>) =>
    api.patch<Budget>(`/budgets/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/budgets/${id}/`),
};
