import { api } from "@/lib/api";

export interface Account {
  id: number;
  name: string;
  account_type: string;
  currency_code: string;
  current_balance: string;
  transaction_count: number;
  is_active: boolean;
}

export interface AccountsSummary {
  base_currency: string;
  total_assets: string;
  by_account_type: { account_type: string; total: string }[];
  stale_fx_warning: boolean;
}

export interface PaginatedAccounts {
  results: Account[];
  count: number;
}

export const accountsApi = {
  list: () => api.get<PaginatedAccounts>("/accounts/").then((r) => r.data),
  summary: () => api.get<AccountsSummary>("/accounts/summary/").then((r) => r.data),
};
