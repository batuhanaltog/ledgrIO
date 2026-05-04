import { api } from "@/lib/api";

export interface TransactionCategory {
  id: number;
  name: string;
  color: string;
  icon: string;
  parent_name: string | null;
}

export interface Transaction {
  id: number;
  account_id: number;
  type: "income" | "expense";
  amount: string;
  currency_code: string;
  amount_base: string;
  base_currency: string;
  fx_rate_snapshot: string;
  category: TransactionCategory | null;
  date: string;
  description: string;
  reference: string;
  created_at: string;
}

export interface CategorySummaryRow {
  category_id: number | null;
  category__name: string;
  total: string;
  count: number;
}

export interface TransactionSummary {
  total_income: string;
  total_expense: string;
  net: string;
  by_category: CategorySummaryRow[];
  running_balance: { period: string | null; cumulative_net: string }[];
}

export interface PaginatedTransactions {
  results: Transaction[];
  count: number;
}

export interface TransactionInput {
  account_id: number;
  type: "income" | "expense";
  amount: string;
  currency_code: string;
  category_id?: number | null;
  date: string;
  description?: string;
  reference?: string;
}

export const transactionsApi = {
  list: (params?: Record<string, string | number>) =>
    api.get<PaginatedTransactions>("/transactions/", { params }).then((r) => r.data),
  summary: (params?: Record<string, string>) =>
    api.get<TransactionSummary>("/transactions/summary/", { params }).then((r) => r.data),
  create: (data: TransactionInput) =>
    api.post<Transaction>("/transactions/", data).then((r) => r.data),
  update: (id: number, data: Partial<TransactionInput>) =>
    api.patch<Transaction>(`/transactions/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/transactions/${id}/`),
};
