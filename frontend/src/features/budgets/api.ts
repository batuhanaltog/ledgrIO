import { api } from "@/lib/api";

export interface Budget {
  id: number;
  name: string;
  category: { id: number; name: string; color: string } | null;
  amount: string;
  date_from: string;
  date_to: string;
  alert_threshold: string | null;
  alert_sent_at: string | null;
  spent: string;
  remaining: string;
  usage_pct: string | null;
  created_at: string;
}

export interface PaginatedBudgets {
  results: Budget[];
  count: number;
}

export const budgetsApi = {
  list: () => api.get<PaginatedBudgets>("/budgets/").then((r) => r.data),
};
