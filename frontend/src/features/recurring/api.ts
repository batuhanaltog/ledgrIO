import { api } from "@/lib/api";

export interface RecurringTemplate {
  id: number; type: "income" | "expense"; amount: string; currency_code: string;
  account: number; category: number | null; description: string;
  frequency: "weekly" | "monthly" | "yearly"; day_of_period: number;
  start_date: string; end_date: string | null; last_generated_date: string | null;
  is_active: boolean; created_at: string; next_due_date: string | null;
}

export interface PaginatedRecurring { results: RecurringTemplate[]; count: number; }

export interface RecurringInput {
  type: "income" | "expense"; amount: string; currency_code: string;
  account_id: number; category_id?: number | null; description: string;
  frequency: "weekly" | "monthly" | "yearly"; day_of_period: number;
  start_date: string; end_date?: string | null;
}

export const recurringApi = {
  list: () => api.get<PaginatedRecurring>("/recurring/").then((r) => r.data),
  create: (data: RecurringInput) => api.post<RecurringTemplate>("/recurring/", data).then((r) => r.data),
  update: (id: number, data: Partial<RecurringInput & { is_active: boolean }>) =>
    api.patch<RecurringTemplate>(`/recurring/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/recurring/${id}/`),
};
