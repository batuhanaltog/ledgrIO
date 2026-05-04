import { api } from "@/lib/api";

export interface Debt {
  id: number; name: string; category_id: number | null;
  original_amount: string; current_balance: string;
  expected_monthly_payment: string; currency_code: string;
  interest_rate_pct: string | null; due_day: number | null;
  is_settled: boolean; notes: string | null; created_at: string;
}

export interface PaginatedDebts { results: Debt[]; count: number; }

export interface DebtInput {
  name: string; category_id?: number | null; original_amount: string;
  expected_monthly_payment: string; currency_code: string;
  interest_rate_pct?: string | null; due_day?: number | null; notes?: string;
}

export interface DebtUpdateInput {
  name?: string; category_id?: number | null; expected_monthly_payment?: string;
  interest_rate_pct?: string | null; due_day?: number | null; notes?: string;
}

export interface PaymentInput {
  account_id: number; amount: string; paid_at: string; description?: string;
}

export const debtsApi = {
  list: () => api.get<PaginatedDebts>("/debts/").then((r) => r.data),
  create: (data: DebtInput) => api.post<Debt>("/debts/", data).then((r) => r.data),
  update: (id: number, data: DebtUpdateInput) =>
    api.patch<Debt>(`/debts/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/debts/${id}/`),
  addPayment: (debtId: number, data: PaymentInput) =>
    api.post(`/debts/${debtId}/payments/`, data).then((r) => r.data),
};
