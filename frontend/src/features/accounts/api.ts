import { api } from "@/lib/api";

export interface Account {
  id: number;
  name: string;
  account_type: string;
  currency_code: string;
  opening_balance: string;
  current_balance: string;
  transaction_count: number;
  is_active: boolean;
  notes: string | null;
}

export interface AccountsSummary {
  base_currency: string;
  total_assets: string;
  by_account_type: { account_type: string; total: string }[];
  stale_fx_warning: boolean;
}

export interface PaginatedAccounts { results: Account[]; count: number; }

export interface AccountInput {
  name: string;
  account_type: string;
  currency_code: string;
  opening_balance: string;
  notes?: string;
}

export const accountsApi = {
  list: () => api.get<PaginatedAccounts>("/accounts/").then((r) => r.data),
  summary: () => api.get<AccountsSummary>("/accounts/summary/").then((r) => r.data),
  create: (data: AccountInput) => api.post<Account>("/accounts/", data).then((r) => r.data),
  update: (id: number, data: Partial<AccountInput>) =>
    api.patch<Account>(`/accounts/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/accounts/${id}/`),
};
