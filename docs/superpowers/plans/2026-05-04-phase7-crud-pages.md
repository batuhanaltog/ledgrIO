# Phase 7 CRUD Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 6 sidebar CRUD pages (Accounts, Transactions, Categories, Budgets, Recurring, Debts) using a shared Modal/ConfirmDialog/useModalState infrastructure and List + Modal interaction pattern.

**Architecture:** Shared primitives (Modal, ConfirmDialog, useModalState) live in `components/ui/` and `hooks/`. Each feature is self-contained with its own api.ts, hooks.ts, page, and modal components. Forms use react-hook-form + zod, following the existing auth page pattern. TanStack Query mutations invalidate relevant query keys on success.

**Tech Stack:** React 19 / Vite / TypeScript / TanStack Query v5 / react-hook-form v7 / zod v4 / Tailwind / lucide-react

---

## File Map

**Create:**
- `frontend/src/components/ui/Modal.tsx`
- `frontend/src/components/ui/ConfirmDialog.tsx`
- `frontend/src/hooks/useModalState.ts`
- `frontend/src/hooks/useModalState.test.ts`
- `frontend/src/features/accounts/pages/AccountsPage.tsx`
- `frontend/src/features/accounts/components/AccountModal.tsx`
- `frontend/src/features/transactions/pages/TransactionsPage.tsx`
- `frontend/src/features/transactions/components/TransactionModal.tsx`
- `frontend/src/features/transactions/components/TransactionFilters.tsx`
- `frontend/src/features/categories/api.ts`
- `frontend/src/features/categories/hooks.ts`
- `frontend/src/features/categories/pages/CategoriesPage.tsx`
- `frontend/src/features/categories/components/CategoryModal.tsx`
- `frontend/src/features/budgets/pages/BudgetsPage.tsx`
- `frontend/src/features/budgets/components/BudgetModal.tsx`
- `frontend/src/features/recurring/api.ts`
- `frontend/src/features/recurring/hooks.ts`
- `frontend/src/features/recurring/pages/RecurringPage.tsx`
- `frontend/src/features/recurring/components/RecurringModal.tsx`
- `frontend/src/features/debts/api.ts`
- `frontend/src/features/debts/hooks.ts`
- `frontend/src/features/debts/pages/DebtsPage.tsx`
- `frontend/src/features/debts/components/DebtModal.tsx`
- `frontend/src/features/debts/components/PaymentModal.tsx`

**Modify:**
- `frontend/src/features/accounts/api.ts` — add create/update/delete
- `frontend/src/features/accounts/hooks.ts` — add mutation hooks
- `frontend/src/features/transactions/api.ts` — add create/update/delete
- `frontend/src/features/transactions/hooks.ts` — add list + mutation hooks
- `frontend/src/features/budgets/api.ts` — add create/update/delete
- `frontend/src/features/budgets/hooks.ts` — add mutation hooks
- `frontend/src/router.tsx` — add 6 routes

**Delete:**
- `frontend/src/features/dashboard/pages/DashboardPlaceholder.tsx`

---

## Task 1: Shared Primitives

**Files:**
- Create: `frontend/src/components/ui/Modal.tsx`
- Create: `frontend/src/components/ui/ConfirmDialog.tsx`
- Create: `frontend/src/hooks/useModalState.ts`
- Create: `frontend/src/hooks/useModalState.test.ts`

- [ ] **Step 1: Write `Modal.tsx`**

```tsx
// frontend/src/components/ui/Modal.tsx
import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

const SIZES = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" } as const;

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  size?: keyof typeof SIZES;
}

export function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className={cn("relative w-full bg-surface rounded-xl shadow-xl border border-hairline", SIZES[size])}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-hairline">
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
```

- [ ] **Step 2: Write `ConfirmDialog.tsx`**

```tsx
// frontend/src/components/ui/ConfirmDialog.tsx
import { Modal } from "./Modal";
import { Button } from "./Button";
import { Spinner } from "./Spinner";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  message?: string;
}

export function ConfirmDialog({
  open, onClose, onConfirm, loading,
  message = "Bu kaydı silmek istediğine emin misin?",
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} title="Emin misin?" size="sm">
      <p className="text-sm text-ink mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onClose} disabled={loading}>İptal</Button>
        <Button variant="danger" onClick={onConfirm} disabled={loading}>
          {loading ? <Spinner /> : null} Sil
        </Button>
      </div>
    </Modal>
  );
}
```

- [ ] **Step 3: Write `useModalState.ts`**

```ts
// frontend/src/hooks/useModalState.ts
import { useState } from "react";

export function useOpenClose() {
  const [isOpen, setIsOpen] = useState(false);
  return { isOpen, open: () => setIsOpen(true), close: () => setIsOpen(false) };
}

export function useEditModal<T>() {
  const [selected, setSelected] = useState<T | null>(null);
  return { selected, open: (item: T) => setSelected(item), close: () => setSelected(null) };
}

export function useDeleteConfirm() {
  const [pendingId, setPendingId] = useState<number | null>(null);
  return { pendingId, confirm: (id: number) => setPendingId(id), cancel: () => setPendingId(null) };
}
```

- [ ] **Step 4: Write failing tests**

```ts
// frontend/src/hooks/useModalState.test.ts
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useOpenClose, useEditModal, useDeleteConfirm } from "./useModalState";

describe("useOpenClose", () => {
  it("starts closed", () => {
    const { result } = renderHook(() => useOpenClose());
    expect(result.current.isOpen).toBe(false);
  });
  it("opens and closes", () => {
    const { result } = renderHook(() => useOpenClose());
    act(() => result.current.open());
    expect(result.current.isOpen).toBe(true);
    act(() => result.current.close());
    expect(result.current.isOpen).toBe(false);
  });
});

describe("useEditModal", () => {
  it("starts null", () => {
    const { result } = renderHook(() => useEditModal<{ id: number }>());
    expect(result.current.selected).toBeNull();
  });
  it("opens with item and closes", () => {
    const { result } = renderHook(() => useEditModal<{ id: number }>());
    act(() => result.current.open({ id: 42 }));
    expect(result.current.selected).toEqual({ id: 42 });
    act(() => result.current.close());
    expect(result.current.selected).toBeNull();
  });
});

describe("useDeleteConfirm", () => {
  it("starts null", () => {
    const { result } = renderHook(() => useDeleteConfirm());
    expect(result.current.pendingId).toBeNull();
  });
  it("sets and clears pendingId", () => {
    const { result } = renderHook(() => useDeleteConfirm());
    act(() => result.current.confirm(7));
    expect(result.current.pendingId).toBe(7);
    act(() => result.current.cancel());
    expect(result.current.pendingId).toBeNull();
  });
});
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npm run test -- --reporter=verbose src/hooks/useModalState.test.ts
```

Expected: 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ui/Modal.tsx \
        frontend/src/components/ui/ConfirmDialog.tsx \
        frontend/src/hooks/useModalState.ts \
        frontend/src/hooks/useModalState.test.ts
git commit -m "feat: shared Modal, ConfirmDialog, useModalState primitives"
```

---

## Task 2: Accounts CRUD

**Files:**
- Modify: `frontend/src/features/accounts/api.ts`
- Modify: `frontend/src/features/accounts/hooks.ts`
- Create: `frontend/src/features/accounts/components/AccountModal.tsx`
- Create: `frontend/src/features/accounts/pages/AccountsPage.tsx`

- [ ] **Step 1: Extend `accounts/api.ts`**

Replace the file entirely:

```ts
// frontend/src/features/accounts/api.ts
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
  notes: string;
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
```

- [ ] **Step 2: Extend `accounts/hooks.ts`**

Replace the file entirely:

```ts
// frontend/src/features/accounts/hooks.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { accountsApi, type AccountInput } from "./api";

export const ACCOUNTS_LIST_KEY = ["accounts", "list"];
export const ACCOUNTS_SUMMARY_KEY = ["accounts", "summary"];

export function useAccounts() {
  return useQuery({ queryKey: ACCOUNTS_LIST_KEY, queryFn: accountsApi.list });
}

export function useAccountsSummary() {
  return useQuery({ queryKey: ACCOUNTS_SUMMARY_KEY, queryFn: accountsApi.summary });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AccountInput) => accountsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}

export function useUpdateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<AccountInput> }) =>
      accountsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => accountsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ACCOUNTS_LIST_KEY });
      qc.invalidateQueries({ queryKey: ACCOUNTS_SUMMARY_KEY });
    },
  });
}
```

- [ ] **Step 3: Write `AccountModal.tsx`**

```tsx
// frontend/src/features/accounts/components/AccountModal.tsx
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useCreateAccount, useUpdateAccount } from "../hooks";
import type { Account } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  account_type: z.enum(["cash", "bank", "credit_card", "savings"]),
  currency_code: z.string().length(3, "3-letter ISO code required.").regex(/^[A-Z]{3}$/, "Use uppercase (e.g. USD)."),
  opening_balance: z.string().regex(/^-?\d+(\.\d+)?$/, "Enter a valid number."),
  notes: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface AccountModalProps {
  account: Account | null;
  onClose: () => void;
}

export function AccountModal({ account, onClose }: AccountModalProps) {
  const isEdit = account !== null;
  const [topError, setTopError] = useState<string | null>(null);

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", account_type: "bank", currency_code: "USD", opening_balance: "0", notes: "" },
    });

  useEffect(() => {
    reset(isEdit
      ? { name: account.name, account_type: account.account_type as FormInput["account_type"], currency_code: account.currency_code, opening_balance: account.opening_balance, notes: account.notes }
      : { name: "", account_type: "bank", currency_code: "USD", opening_balance: "0", notes: "" }
    );
  }, [account, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateAccount();
  const update = useUpdateAccount();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      if (isEdit) await update.mutateAsync({ id: account.id, data: values });
      else await create.mutateAsync(values);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Account" : "New Account"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <Field label="Type" htmlFor="account_type" error={errors.account_type?.message}>
          <Select id="account_type" {...register("account_type")}>
            <option value="bank">Bank</option>
            <option value="cash">Cash</option>
            <option value="credit_card">Credit Card</option>
            <option value="savings">Savings</option>
          </Select>
        </Field>
        <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
          <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
        </Field>
        <Field label="Opening Balance" htmlFor="opening_balance" error={errors.opening_balance?.message}>
          <Input id="opening_balance" inputMode="decimal" invalid={Boolean(errors.opening_balance)} {...register("opening_balance")} />
        </Field>
        <Field label="Notes" htmlFor="notes">
          <Input id="notes" {...register("notes")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 4: Write `AccountsPage.tsx`**

```tsx
// frontend/src/features/accounts/pages/AccountsPage.tsx
import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useAccounts, useDeleteAccount } from "../hooks";
import { AccountModal } from "../components/AccountModal";
import type { Account } from "../api";

function fmt(v: string) {
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function AccountsPage() {
  const { data, isPending, isError } = useAccounts();
  const createModal = useOpenClose();
  const editModal = useEditModal<Account>();
  const deleteConfirm = useDeleteConfirm();
  const deleteAccount = useDeleteAccount();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError) return <Alert tone="danger">Hesaplar yüklenemedi.</Alert>;

  const handleDelete = async () => {
    if (deleteConfirm.pendingId === null) return;
    setDeleteError(null);
    try {
      await deleteAccount.mutateAsync(deleteConfirm.pendingId);
      deleteConfirm.cancel();
    } catch {
      setDeleteError("Hesap silinemedi. İşlem içeren hesaplar silinemez.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Accounts</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} account{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Account</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No accounts yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Name", "Type", "Currency", "Balance", "Transactions", ""].map((h) => (
                  <th key={h} className={`px-4 py-3 text-left font-medium ${h === "Balance" || h === "Transactions" ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((acc) => (
                <tr key={acc.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 font-medium text-ink">{acc.name}</td>
                  <td className="px-4 py-3 text-ink-muted capitalize">{acc.account_type.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-ink-muted">{acc.currency_code}</td>
                  <td className="px-4 py-3 text-right num font-medium text-ink">{fmt(acc.current_balance)}</td>
                  <td className="px-4 py-3 text-right text-ink-muted">{acc.transaction_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => editModal.open(acc)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(acc.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && <AccountModal account={null} onClose={createModal.close} />}
      {editModal.selected && <AccountModal account={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={() => { setDeleteError(null); deleteConfirm.cancel(); }}
        onConfirm={handleDelete}
        loading={deleteAccount.isPending}
        message={deleteError ?? "Bu hesabı silmek istediğine emin misin?"}
      />
    </div>
  );
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/accounts/
git commit -m "feat: Accounts CRUD page with modal"
```

---

## Task 3: Transactions CRUD

**Files:**
- Modify: `frontend/src/features/transactions/api.ts`
- Modify: `frontend/src/features/transactions/hooks.ts`
- Create: `frontend/src/features/transactions/components/TransactionFilters.tsx`
- Create: `frontend/src/features/transactions/components/TransactionModal.tsx`
- Create: `frontend/src/features/transactions/pages/TransactionsPage.tsx`

- [ ] **Step 1: Extend `transactions/api.ts`**

Replace entirely:

```ts
// frontend/src/features/transactions/api.ts
import { api } from "@/lib/api";

export interface TransactionCategory {
  id: number; name: string; color: string; icon: string; parent_name: string | null;
}

export interface Transaction {
  id: number; account_id: number; type: "income" | "expense";
  amount: string; currency_code: string; amount_base: string; base_currency: string;
  fx_rate_snapshot: string; category: TransactionCategory | null;
  date: string; description: string; reference: string; created_at: string;
}

export interface CategorySummaryRow {
  category_id: number | null; category__name: string; total: string; count: number;
}

export interface TransactionSummary {
  total_income: string; total_expense: string; net: string;
  by_category: CategorySummaryRow[];
  running_balance: { period: string | null; cumulative_net: string }[];
}

export interface PaginatedTransactions { results: Transaction[]; count: number; }

export interface TransactionInput {
  account_id: number; type: "income" | "expense"; amount: string;
  currency_code: string; category_id?: number | null;
  date: string; description?: string; reference?: string;
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
```

- [ ] **Step 2: Extend `transactions/hooks.ts`**

Replace entirely:

```ts
// frontend/src/features/transactions/hooks.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { transactionsApi, type TransactionInput } from "./api";

export const TRANSACTIONS_LIST_KEY = ["transactions", "list"];
export const RECENT_TRANSACTIONS_KEY = ["transactions", "recent"];
export const TRANSACTION_SUMMARY_KEY = ["transactions", "summary"];

export function useTransactions(params?: Record<string, string | number>) {
  return useQuery({
    queryKey: [...TRANSACTIONS_LIST_KEY, params],
    queryFn: () => transactionsApi.list(params),
  });
}

export function useRecentTransactions() {
  return useQuery({
    queryKey: RECENT_TRANSACTIONS_KEY,
    queryFn: () => transactionsApi.list({ ordering: "-date", page_size: 10 }),
  });
}

export function useTransactionSummary(params?: Record<string, string>) {
  return useQuery({
    queryKey: [...TRANSACTION_SUMMARY_KEY, params],
    queryFn: () => transactionsApi.summary(params),
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: TRANSACTIONS_LIST_KEY });
  qc.invalidateQueries({ queryKey: RECENT_TRANSACTIONS_KEY });
  qc.invalidateQueries({ queryKey: TRANSACTION_SUMMARY_KEY });
  qc.invalidateQueries({ queryKey: ["accounts", "list"] });
  qc.invalidateQueries({ queryKey: ["accounts", "summary"] });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (data: TransactionInput) => transactionsApi.create(data), onSuccess: () => invalidateAll(qc) });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<TransactionInput> }) => transactionsApi.update(id, data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => transactionsApi.delete(id), onSuccess: () => invalidateAll(qc) });
}
```

- [ ] **Step 3: Write `TransactionFilters.tsx`**

```tsx
// frontend/src/features/transactions/components/TransactionFilters.tsx
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAccounts } from "@/features/accounts/hooks";
import { useCategories } from "@/features/categories/hooks";

export interface FilterValues {
  date_from: string; date_to: string;
  account_id: string; category_id: string;
  type: string; description: string;
}

function todayMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
}

interface Props { onChange: (f: FilterValues) => void; }

export function TransactionFilters({ onChange }: Props) {
  const { date_from: df, date_to: dt } = todayMonthRange();
  const [filters, setFilters] = useState<FilterValues>({
    date_from: df, date_to: dt, account_id: "", category_id: "", type: "", description: "",
  });
  const accounts = useAccounts();
  const categories = useCategories();

  useEffect(() => {
    const timer = setTimeout(() => onChange(filters), 300);
    return () => clearTimeout(timer);
  }, [filters, onChange]);

  const set = (key: keyof FilterValues) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFilters((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <div className="flex flex-wrap gap-3">
      <Input type="date" value={filters.date_from} onChange={set("date_from")} className="w-36" />
      <Input type="date" value={filters.date_to} onChange={set("date_to")} className="w-36" />
      <Select value={filters.account_id} onChange={set("account_id")} className="w-40">
        <option value="">All Accounts</option>
        {accounts.data?.results.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
      </Select>
      <Select value={filters.category_id} onChange={set("category_id")} className="w-40">
        <option value="">All Categories</option>
        {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </Select>
      <Select value={filters.type} onChange={set("type")} className="w-36">
        <option value="">All Types</option>
        <option value="income">Income</option>
        <option value="expense">Expense</option>
      </Select>
      <Input placeholder="Search description…" value={filters.description} onChange={set("description")} className="w-48" />
    </div>
  );
}
```

- [ ] **Step 4: Write `TransactionModal.tsx`**

```tsx
// frontend/src/features/transactions/components/TransactionModal.tsx
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useAccounts } from "@/features/accounts/hooks";
import { useCategories } from "@/features/categories/hooks";
import { useCreateTransaction, useUpdateTransaction } from "../hooks";
import type { Transaction } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  account_id: z.string().min(1, "Account is required."),
  type: z.enum(["income", "expense"]),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  currency_code: z.string().length(3).regex(/^[A-Z]{3}$/),
  category_id: z.string().optional(),
  date: z.string().min(1, "Date is required."),
  description: z.string().optional(),
  reference: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface TransactionModalProps { transaction: Transaction | null; onClose: () => void; }

export function TransactionModal({ transaction, onClose }: TransactionModalProps) {
  const isEdit = transaction !== null;
  const [topError, setTopError] = useState<string | null>(null);
  const accounts = useAccounts();
  const categories = useCategories();

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { account_id: "", type: "expense", amount: "", currency_code: "USD", category_id: "", date: today(), description: "", reference: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      account_id: String(transaction.account_id),
      type: transaction.type, amount: String(Number(transaction.amount)),
      currency_code: transaction.currency_code,
      category_id: transaction.category ? String(transaction.category.id) : "",
      date: transaction.date, description: transaction.description, reference: transaction.reference,
    } : { account_id: "", type: "expense", amount: "", currency_code: "USD", category_id: "", date: today(), description: "", reference: "" });
  }, [transaction, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateTransaction();
  const update = useUpdateTransaction();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    const payload = {
      account_id: Number(values.account_id),
      type: values.type,
      amount: values.amount,
      currency_code: values.currency_code,
      category_id: values.category_id ? Number(values.category_id) : null,
      date: values.date,
      description: values.description ?? "",
      reference: values.reference ?? "",
    };
    try {
      if (isEdit) await update.mutateAsync({ id: transaction.id, data: payload });
      else await create.mutateAsync(payload);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Transaction" : "New Transaction"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Account" htmlFor="account_id" error={errors.account_id?.message} className="col-span-2">
            <Select id="account_id" invalid={Boolean(errors.account_id)} {...register("account_id")}>
              <option value="">Select account…</option>
              {accounts.data?.results.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </Select>
          </Field>
          <Field label="Type" htmlFor="type">
            <Select id="type" {...register("type")}>
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </Select>
          </Field>
          <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
            <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
          </Field>
          <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
            <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
          </Field>
          <Field label="Date" htmlFor="date" error={errors.date?.message}>
            <Input id="date" type="date" invalid={Boolean(errors.date)} {...register("date")} />
          </Field>
          <Field label="Category" htmlFor="category_id" className="col-span-2">
            <Select id="category_id" {...register("category_id")}>
              <option value="">No category</option>
              {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
          <Field label="Description" htmlFor="description" className="col-span-2">
            <Input id="description" {...register("description")} />
          </Field>
          <Field label="Reference" htmlFor="reference" className="col-span-2">
            <Input id="reference" {...register("reference")} />
          </Field>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 5: Write `TransactionsPage.tsx`**

```tsx
// frontend/src/features/transactions/pages/TransactionsPage.tsx
import { useCallback, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useTransactions, useDeleteTransaction } from "../hooks";
import { TransactionFilters, type FilterValues } from "../components/TransactionFilters";
import { TransactionModal } from "../components/TransactionModal";
import type { Transaction } from "../api";

function todayMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
}

export function TransactionsPage() {
  const { date_from, date_to } = todayMonthRange();
  const [params, setParams] = useState<Record<string, string>>({ date_from, date_to });
  const { data, isPending, isError } = useTransactions(params);
  const createModal = useOpenClose();
  const editModal = useEditModal<Transaction>();
  const deleteConfirm = useDeleteConfirm();
  const deleteTransaction = useDeleteTransaction();

  const handleFilterChange = useCallback((f: FilterValues) => {
    const p: Record<string, string> = {};
    if (f.date_from) p.date_from = f.date_from;
    if (f.date_to) p.date_to = f.date_to;
    if (f.account_id) p.account_id = f.account_id;
    if (f.category_id) p.category_id = f.category_id;
    if (f.type) p.type = f.type;
    if (f.description) p.description = f.description;
    setParams(p);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Transactions</h1>
          {data && <p className="text-sm text-ink-muted mt-1">{data.count} transaction{data.count !== 1 ? "s" : ""}</p>}
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Transaction</Button>
      </div>

      <TransactionFilters onChange={handleFilterChange} />

      {isPending ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : isError ? (
        <Alert tone="danger">İşlemler yüklenemedi.</Alert>
      ) : data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">Bu dönemde işlem bulunamadı.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Date", "Description", "Category", "Type", "Amount", ""].map((h) => (
                  <th key={h} className={`px-4 py-3 text-left font-medium ${h === "Amount" ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((tx) => (
                <tr key={tx.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 text-ink-muted">{tx.date}</td>
                  <td className="px-4 py-3 text-ink">{tx.description || "—"}</td>
                  <td className="px-4 py-3 text-ink-muted">{tx.category?.name ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${tx.type === "income" ? "bg-success/15 text-success" : "bg-danger/15 text-danger"}`}>
                      {tx.type}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-right num font-medium ${tx.type === "income" ? "text-success" : "text-danger"}`}>
                    {tx.type === "expense" ? "−" : "+"}{Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {tx.currency_code}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => editModal.open(tx)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(tx.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && <TransactionModal transaction={null} onClose={createModal.close} />}
      {editModal.selected && <TransactionModal transaction={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId) { await deleteTransaction.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteTransaction.isPending}
      />
    </div>
  );
}
```

- [ ] **Step 6: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors. (Note: `useCategories` is imported but not yet defined — TS will error. Proceed to Task 4 immediately and return to verify.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/transactions/
git commit -m "feat: Transactions CRUD page with filters and modal"
```

---

## Task 4: Categories CRUD

**Files:**
- Create: `frontend/src/features/categories/api.ts`
- Create: `frontend/src/features/categories/hooks.ts`
- Create: `frontend/src/features/categories/components/CategoryModal.tsx`
- Create: `frontend/src/features/categories/pages/CategoriesPage.tsx`

- [ ] **Step 1: Write `categories/api.ts`**

```ts
// frontend/src/features/categories/api.ts
import { api } from "@/lib/api";

export interface Category {
  id: number; name: string; icon: string; color: string;
  is_system: boolean; owner_id: number | null; parent_id: number | null;
  ordering: number; created_at: string;
}

export interface PaginatedCategories { results: Category[]; count: number; }

export interface CategoryInput {
  name: string; category_type: "income" | "expense"; icon?: string; color?: string;
}

export const categoriesApi = {
  list: () => api.get<PaginatedCategories>("/categories/").then((r) => r.data),
  create: (data: CategoryInput) => api.post<Category>("/categories/", data).then((r) => r.data),
  update: (id: number, data: Partial<CategoryInput>) =>
    api.patch<Category>(`/categories/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/categories/${id}/`),
};
```

- [ ] **Step 2: Write `categories/hooks.ts`**

```ts
// frontend/src/features/categories/hooks.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { categoriesApi, type CategoryInput } from "./api";

export const CATEGORIES_KEY = ["categories"];

export function useCategories() {
  return useQuery({ queryKey: CATEGORIES_KEY, queryFn: categoriesApi.list });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (data: CategoryInput) => categoriesApi.create(data), onSuccess: () => qc.invalidateQueries({ queryKey: CATEGORIES_KEY }) });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CategoryInput> }) => categoriesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: CATEGORIES_KEY }),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => categoriesApi.delete(id), onSuccess: () => qc.invalidateQueries({ queryKey: CATEGORIES_KEY }) });
}
```

- [ ] **Step 3: Write `CategoryModal.tsx`**

```tsx
// frontend/src/features/categories/components/CategoryModal.tsx
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useCreateCategory, useUpdateCategory } from "../hooks";
import type { Category } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  category_type: z.enum(["income", "expense"]),
  icon: z.string().optional(),
  color: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface CategoryModalProps { category: Category | null; onClose: () => void; }

export function CategoryModal({ category, onClose }: CategoryModalProps) {
  const isEdit = category !== null;
  const [topError, setTopError] = useState<string | null>(null);

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", category_type: "expense", icon: "", color: "" },
    });

  useEffect(() => {
    reset(isEdit
      ? { name: category.name, category_type: "expense", icon: category.icon, color: category.color }
      : { name: "", category_type: "expense", icon: "", color: "" }
    );
  }, [category, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateCategory();
  const update = useUpdateCategory();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      if (isEdit) await update.mutateAsync({ id: category.id, data: values });
      else await create.mutateAsync(values);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Category" : "New Category"} size="sm">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <Field label="Type" htmlFor="category_type">
          <Select id="category_type" {...register("category_type")}>
            <option value="expense">Expense</option>
            <option value="income">Income</option>
          </Select>
        </Field>
        <Field label="Icon" htmlFor="icon" hint="e.g. 🛒 or leave blank">
          <Input id="icon" {...register("icon")} />
        </Field>
        <Field label="Color" htmlFor="color">
          <Input id="color" type="color" className="h-10 p-1 cursor-pointer" {...register("color")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 4: Write `CategoriesPage.tsx`**

```tsx
// frontend/src/features/categories/pages/CategoriesPage.tsx
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useCategories, useDeleteCategory } from "../hooks";
import { CategoryModal } from "../components/CategoryModal";
import type { Category } from "../api";

export function CategoriesPage() {
  const { data, isPending, isError } = useCategories();
  const createModal = useOpenClose();
  const editModal = useEditModal<Category>();
  const deleteConfirm = useDeleteConfirm();
  const deleteCategory = useDeleteCategory();

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError) return <Alert tone="danger">Kategoriler yüklenemedi.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Categories</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} categories</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Category</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No categories yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Icon", "Name", "Color", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((cat) => (
                <tr key={cat.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 text-xl">{cat.icon || "—"}</td>
                  <td className="px-4 py-3 font-medium text-ink">{cat.name}</td>
                  <td className="px-4 py-3">
                    {cat.color ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="w-4 h-4 rounded-full border border-hairline" style={{ background: cat.color }} />
                        <span className="text-ink-muted text-xs">{cat.color}</span>
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => editModal.open(cat)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(cat.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && <CategoryModal category={null} onClose={createModal.close} />}
      {editModal.selected && <CategoryModal category={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId) { await deleteCategory.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteCategory.isPending}
      />
    </div>
  );
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/categories/
git commit -m "feat: Categories CRUD page with modal"
```

---

## Task 5: Budgets CRUD

**Files:**
- Modify: `frontend/src/features/budgets/api.ts`
- Modify: `frontend/src/features/budgets/hooks.ts`
- Create: `frontend/src/features/budgets/components/BudgetModal.tsx`
- Create: `frontend/src/features/budgets/pages/BudgetsPage.tsx`

- [ ] **Step 1: Extend `budgets/api.ts`**

Replace entirely:

```ts
// frontend/src/features/budgets/api.ts
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
```

- [ ] **Step 2: Extend `budgets/hooks.ts`**

Replace entirely:

```ts
// frontend/src/features/budgets/hooks.ts
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
```

- [ ] **Step 3: Write `BudgetModal.tsx`**

```tsx
// frontend/src/features/budgets/components/BudgetModal.tsx
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useCategories } from "@/features/categories/hooks";
import { useCreateBudget, useUpdateBudget } from "../hooks";
import type { Budget } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  category_id: z.string().optional(),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  date_from: z.string().min(1, "Date from is required."),
  date_to: z.string().min(1, "Date to is required."),
  alert_threshold: z.string().optional(),
}).refine((d) => !d.date_to || !d.date_from || d.date_to >= d.date_from, {
  message: "Date to must be on or after date from.", path: ["date_to"],
});
type FormInput = z.infer<typeof schema>;

function thisMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
}

interface BudgetModalProps { budget: Budget | null; onClose: () => void; }

export function BudgetModal({ budget, onClose }: BudgetModalProps) {
  const isEdit = budget !== null;
  const [topError, setTopError] = useState<string | null>(null);
  const categories = useCategories();
  const { date_from, date_to } = thisMonthRange();

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", category_id: "", amount: "", date_from, date_to, alert_threshold: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      name: budget.name,
      category_id: budget.category ? String(budget.category.id) : "",
      amount: String(Number(budget.amount)),
      date_from: budget.date_from, date_to: budget.date_to,
      alert_threshold: budget.alert_threshold ? String(Number(budget.alert_threshold) * 100) : "",
    } : { name: "", category_id: "", amount: "", date_from, date_to, alert_threshold: "" });
  }, [budget, isEdit, reset, date_from, date_to]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateBudget();
  const update = useUpdateBudget();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    const payload = {
      name: values.name,
      category_id: values.category_id ? Number(values.category_id) : null,
      amount: values.amount,
      date_from: values.date_from,
      date_to: values.date_to,
      alert_threshold: values.alert_threshold
        ? String(Number(values.alert_threshold) / 100)
        : null,
    };
    try {
      if (isEdit) await update.mutateAsync({ id: budget.id, data: payload });
      else await create.mutateAsync(payload);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Budget" : "New Budget"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <Field label="Category" htmlFor="category_id" hint="Leave empty to track all categories.">
          <Select id="category_id" {...register("category_id")}>
            <option value="">All categories</option>
            {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
          <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Date From" htmlFor="date_from" error={errors.date_from?.message}>
            <Input id="date_from" type="date" invalid={Boolean(errors.date_from)} {...register("date_from")} />
          </Field>
          <Field label="Date To" htmlFor="date_to" error={errors.date_to?.message}>
            <Input id="date_to" type="date" invalid={Boolean(errors.date_to)} {...register("date_to")} />
          </Field>
        </div>
        <Field label="Alert Threshold (%)" htmlFor="alert_threshold" hint="e.g. 80 to alert at 80% spent. Leave empty to disable.">
          <Input id="alert_threshold" inputMode="decimal" placeholder="80" {...register("alert_threshold")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 4: Write `BudgetsPage.tsx`**

```tsx
// frontend/src/features/budgets/pages/BudgetsPage.tsx
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useBudgets, useDeleteBudget } from "../hooks";
import { BudgetModal } from "../components/BudgetModal";
import { cn } from "@/lib/cn";
import type { Budget } from "../api";

function usageColor(pct: number) {
  if (pct >= 100) return "bg-danger";
  if (pct >= 75) return "bg-warn";
  return "bg-success";
}

export function BudgetsPage() {
  const { data, isPending, isError } = useBudgets();
  const createModal = useOpenClose();
  const editModal = useEditModal<Budget>();
  const deleteConfirm = useDeleteConfirm();
  const deleteBudget = useDeleteBudget();

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError) return <Alert tone="danger">Bütçeler yüklenemedi.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Budgets</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} budget{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Budget</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No budgets yet.</p>
      ) : (
        <div className="space-y-3">
          {data.results.map((b) => {
            const pct = b.usage_pct ? Math.min(Number(b.usage_pct) * 100, 100) : 0;
            return (
              <div key={b.id} className="rounded-lg border border-hairline bg-surface p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-ink">{b.name}</p>
                      <p className="text-xs text-ink-muted">{b.date_from} → {b.date_to}</p>
                    </div>
                    {b.category && <p className="text-xs text-ink-muted mb-2">{b.category.name}</p>}
                    <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden mb-2">
                      <div className={cn("h-full rounded-full transition-all", usageColor(pct))} style={{ width: `${pct}%` }} />
                    </div>
                    <div className="flex justify-between text-xs text-ink-muted">
                      <span>{Number(b.spent).toLocaleString(undefined, { maximumFractionDigits: 2 })} spent</span>
                      <span>{Number(b.amount).toLocaleString(undefined, { maximumFractionDigits: 2 })} budget · {pct.toFixed(0)}%</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => editModal.open(b)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(b.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {createModal.isOpen && <BudgetModal budget={null} onClose={createModal.close} />}
      {editModal.selected && <BudgetModal budget={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId) { await deleteBudget.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteBudget.isPending}
      />
    </div>
  );
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/budgets/
git commit -m "feat: Budgets CRUD page with progress bars and modal"
```

---

## Task 6: Recurring CRUD

**Backend field reference:**
- Create: `type` (income/expense), `amount`, `currency_code`, `account_id`, `category_id?`, `description`, `frequency` (weekly/monthly/yearly), `day_of_period` (int 1–366), `start_date`, `end_date?`
- Update: same fields, all optional + `is_active`
- List response fields: same + `id`, `is_active`, `last_generated_date`, `next_due_date`, `created_at`

**Files:**
- Create: `frontend/src/features/recurring/api.ts`
- Create: `frontend/src/features/recurring/hooks.ts`
- Create: `frontend/src/features/recurring/components/RecurringModal.tsx`
- Create: `frontend/src/features/recurring/pages/RecurringPage.tsx`

- [ ] **Step 1: Write `recurring/api.ts`**

```ts
// frontend/src/features/recurring/api.ts
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
```

- [ ] **Step 2: Write `recurring/hooks.ts`**

```ts
// frontend/src/features/recurring/hooks.ts
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
```

- [ ] **Step 3: Write `RecurringModal.tsx`**

```tsx
// frontend/src/features/recurring/components/RecurringModal.tsx
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useAccounts } from "@/features/accounts/hooks";
import { useCategories } from "@/features/categories/hooks";
import { useCreateRecurring, useUpdateRecurring } from "../hooks";
import type { RecurringTemplate } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  type: z.enum(["income", "expense"]),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  currency_code: z.string().length(3).regex(/^[A-Z]{3}$/),
  account_id: z.string().min(1, "Account is required."),
  category_id: z.string().optional(),
  description: z.string().min(1, "Description is required."),
  frequency: z.enum(["weekly", "monthly", "yearly"]),
  day_of_period: z.string().regex(/^\d+$/, "Enter a number."),
  start_date: z.string().min(1, "Start date is required."),
  end_date: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface RecurringModalProps { template: RecurringTemplate | null; onClose: () => void; }

export function RecurringModal({ template, onClose }: RecurringModalProps) {
  const isEdit = template !== null;
  const [topError, setTopError] = useState<string | null>(null);
  const accounts = useAccounts();
  const categories = useCategories();

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { type: "expense", amount: "", currency_code: "USD", account_id: "", category_id: "", description: "", frequency: "monthly", day_of_period: "1", start_date: today(), end_date: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      type: template.type, amount: String(Number(template.amount)),
      currency_code: template.currency_code, account_id: String(template.account),
      category_id: template.category ? String(template.category) : "",
      description: template.description, frequency: template.frequency,
      day_of_period: String(template.day_of_period), start_date: template.start_date,
      end_date: template.end_date ?? "",
    } : { type: "expense", amount: "", currency_code: "USD", account_id: "", category_id: "", description: "", frequency: "monthly", day_of_period: "1", start_date: today(), end_date: "" });
  }, [template, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateRecurring();
  const update = useUpdateRecurring();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    const payload = {
      type: values.type, amount: values.amount, currency_code: values.currency_code,
      account_id: Number(values.account_id),
      category_id: values.category_id ? Number(values.category_id) : null,
      description: values.description, frequency: values.frequency,
      day_of_period: Number(values.day_of_period), start_date: values.start_date,
      end_date: values.end_date || null,
    };
    try {
      if (isEdit) await update.mutateAsync({ id: template.id, data: payload });
      else await create.mutateAsync(payload);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Recurring" : "New Recurring Template"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Description" htmlFor="description" error={errors.description?.message}>
          <Input id="description" invalid={Boolean(errors.description)} {...register("description")} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Type" htmlFor="type">
            <Select id="type" {...register("type")}>
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </Select>
          </Field>
          <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
            <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
          </Field>
          <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
            <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
          </Field>
          <Field label="Account" htmlFor="account_id" error={errors.account_id?.message}>
            <Select id="account_id" invalid={Boolean(errors.account_id)} {...register("account_id")}>
              <option value="">Select…</option>
              {accounts.data?.results.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </Select>
          </Field>
          <Field label="Category" htmlFor="category_id">
            <Select id="category_id" {...register("category_id")}>
              <option value="">No category</option>
              {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
          <Field label="Frequency" htmlFor="frequency">
            <Select id="frequency" {...register("frequency")}>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </Select>
          </Field>
          <Field label="Day of Period" htmlFor="day_of_period" error={errors.day_of_period?.message} hint="1–31 for monthly, 1–7 for weekly">
            <Input id="day_of_period" inputMode="numeric" invalid={Boolean(errors.day_of_period)} {...register("day_of_period")} />
          </Field>
          <Field label="Start Date" htmlFor="start_date" error={errors.start_date?.message}>
            <Input id="start_date" type="date" invalid={Boolean(errors.start_date)} {...register("start_date")} />
          </Field>
          <Field label="End Date" htmlFor="end_date" hint="Optional">
            <Input id="end_date" type="date" {...register("end_date")} />
          </Field>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 4: Write `RecurringPage.tsx`**

```tsx
// frontend/src/features/recurring/pages/RecurringPage.tsx
import { Plus, Pencil, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useRecurring, useDeleteRecurring, useUpdateRecurring } from "../hooks";
import { RecurringModal } from "../components/RecurringModal";
import type { RecurringTemplate } from "../api";

export function RecurringPage() {
  const { data, isPending, isError } = useRecurring();
  const createModal = useOpenClose();
  const editModal = useEditModal<RecurringTemplate>();
  const deleteConfirm = useDeleteConfirm();
  const deleteRecurring = useDeleteRecurring();
  const updateRecurring = useUpdateRecurring();

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError) return <Alert tone="danger">Tekrar eden işlemler yüklenemedi.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Recurring</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} template{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Template</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No recurring templates yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Description", "Type", "Amount", "Frequency", "Next Due", "Active", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((t) => (
                <tr key={t.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 font-medium text-ink">{t.description}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${t.type === "income" ? "bg-success/15 text-success" : "bg-danger/15 text-danger"}`}>{t.type}</span>
                  </td>
                  <td className="px-4 py-3 num text-ink">{Number(t.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {t.currency_code}</td>
                  <td className="px-4 py-3 text-ink-muted capitalize">{t.frequency}</td>
                  <td className="px-4 py-3 text-ink-muted">{t.next_due_date ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost" size="icon"
                      onClick={() => updateRecurring.mutate({ id: t.id, data: { is_active: !t.is_active } })}
                      aria-label={t.is_active ? "Deactivate" : "Activate"}
                    >
                      {t.is_active ? <ToggleRight className="h-5 w-5 text-success" /> : <ToggleLeft className="h-5 w-5 text-ink-muted" />}
                    </Button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => editModal.open(t)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(t.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && <RecurringModal template={null} onClose={createModal.close} />}
      {editModal.selected && <RecurringModal template={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId) { await deleteRecurring.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteRecurring.isPending}
      />
    </div>
  );
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/recurring/
git commit -m "feat: Recurring templates CRUD page with active toggle"
```

---

## Task 7: Debts CRUD

**Backend field reference:**
- Debt create: `name`, `category_id?`, `original_amount`, `expected_monthly_payment`, `currency_code`, `interest_rate_pct?`, `due_day?`, `notes?`
- Debt update: same except `original_amount` is not updatable — only `expected_monthly_payment`, `interest_rate_pct`, `due_day`, `notes`, `category_id`, `name`
- Debt list response: `id`, `name`, `category_id`, `original_amount`, `current_balance`, `expected_monthly_payment`, `currency_code`, `interest_rate_pct`, `due_day`, `is_settled`, `notes`, `created_at`
- Payment create: `account_id`, `amount`, `paid_at`, `description?`
- Payment list: via `GET /debts/<id>/` which shows debt detail (no separate payments list endpoint — payments are on DebtPayment model but no list endpoint exists; fetch debt payments via the monthly-summary or load on expand)

**Note:** There is no payments list endpoint. For the expandable row, we'll call `GET /debts/<id>/` for the individual debt which doesn't include payments either. The simplest approach: after adding/deleting a payment, refetch the debts list (balance changes). For the payment history in the expanded row, add a per-debt payments endpoint call. Check if there's a detail endpoint that returns payments.

Actually, `GET /debts/<pk>/` returns the Debt serializer which does not include payments. Since there's no payments list endpoint, we'll track payments via the `DebtPayment` create/delete endpoints and show payment history only after a fresh load won't work. **Simplification:** The expanded row shows current_balance progress only. The "Add Payment" button opens a modal. After payment, refetch debts list. Payment history display is deferred (no backend endpoint supports it efficiently).

**Files:**
- Create: `frontend/src/features/debts/api.ts`
- Create: `frontend/src/features/debts/hooks.ts`
- Create: `frontend/src/features/debts/components/DebtModal.tsx`
- Create: `frontend/src/features/debts/components/PaymentModal.tsx`
- Create: `frontend/src/features/debts/pages/DebtsPage.tsx`

- [ ] **Step 1: Write `debts/api.ts`**

```ts
// frontend/src/features/debts/api.ts
import { api } from "@/lib/api";

export interface Debt {
  id: number; name: string; category_id: number | null;
  original_amount: string; current_balance: string;
  expected_monthly_payment: string; currency_code: string;
  interest_rate_pct: string | null; due_day: number | null;
  is_settled: boolean; notes: string; created_at: string;
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
  deletePayment: (debtId: number, paymentId: number) =>
    api.delete(`/debts/${debtId}/payments/${paymentId}/`),
};
```

- [ ] **Step 2: Write `debts/hooks.ts`**

```ts
// frontend/src/features/debts/hooks.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { debtsApi, type DebtInput, type DebtUpdateInput, type PaymentInput } from "./api";

export const DEBTS_KEY = ["debts"];

export function useDebts() {
  return useQuery({ queryKey: DEBTS_KEY, queryFn: debtsApi.list });
}

export function useCreateDebt() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (data: DebtInput) => debtsApi.create(data), onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }) });
}

export function useUpdateDebt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DebtUpdateInput }) => debtsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }),
  });
}

export function useDeleteDebt() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => debtsApi.delete(id), onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }) });
}

export function useAddPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ debtId, data }: { debtId: number; data: PaymentInput }) => debtsApi.addPayment(debtId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEBTS_KEY }),
  });
}
```

- [ ] **Step 3: Write `DebtModal.tsx`**

```tsx
// frontend/src/features/debts/components/DebtModal.tsx
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useCreateDebt, useUpdateDebt } from "../hooks";
import type { Debt } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  original_amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  expected_monthly_payment: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  currency_code: z.string().length(3).regex(/^[A-Z]{3}$/),
  interest_rate_pct: z.string().optional(),
  due_day: z.string().optional(),
  notes: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface DebtModalProps { debt: Debt | null; onClose: () => void; }

export function DebtModal({ debt, onClose }: DebtModalProps) {
  const isEdit = debt !== null;
  const [topError, setTopError] = useState<string | null>(null);

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", original_amount: "", expected_monthly_payment: "", currency_code: "USD", interest_rate_pct: "", due_day: "", notes: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      name: debt.name, original_amount: String(Number(debt.original_amount)),
      expected_monthly_payment: String(Number(debt.expected_monthly_payment)),
      currency_code: debt.currency_code,
      interest_rate_pct: debt.interest_rate_pct ? String(Number(debt.interest_rate_pct)) : "",
      due_day: debt.due_day ? String(debt.due_day) : "", notes: debt.notes,
    } : { name: "", original_amount: "", expected_monthly_payment: "", currency_code: "USD", interest_rate_pct: "", due_day: "", notes: "" });
  }, [debt, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateDebt();
  const update = useUpdateDebt();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      if (isEdit) {
        await update.mutateAsync({ id: debt.id, data: {
          name: values.name, expected_monthly_payment: values.expected_monthly_payment,
          interest_rate_pct: values.interest_rate_pct || null,
          due_day: values.due_day ? Number(values.due_day) : null, notes: values.notes,
        }});
      } else {
        await create.mutateAsync({
          name: values.name, original_amount: values.original_amount,
          expected_monthly_payment: values.expected_monthly_payment,
          currency_code: values.currency_code,
          interest_rate_pct: values.interest_rate_pct || null,
          due_day: values.due_day ? Number(values.due_day) : null, notes: values.notes,
        });
      }
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Debt" : "New Debt"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          {!isEdit && (
            <Field label="Original Amount" htmlFor="original_amount" error={errors.original_amount?.message} className="col-span-2">
              <Input id="original_amount" inputMode="decimal" invalid={Boolean(errors.original_amount)} {...register("original_amount")} />
            </Field>
          )}
          <Field label="Monthly Payment" htmlFor="expected_monthly_payment" error={errors.expected_monthly_payment?.message}>
            <Input id="expected_monthly_payment" inputMode="decimal" invalid={Boolean(errors.expected_monthly_payment)} {...register("expected_monthly_payment")} />
          </Field>
          {!isEdit && (
            <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
              <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
            </Field>
          )}
          <Field label="Interest Rate (%)" htmlFor="interest_rate_pct" hint="Optional">
            <Input id="interest_rate_pct" inputMode="decimal" {...register("interest_rate_pct")} />
          </Field>
          <Field label="Due Day" htmlFor="due_day" hint="Day of month (1–31), optional">
            <Input id="due_day" inputMode="numeric" {...register("due_day")} />
          </Field>
        </div>
        <Field label="Notes" htmlFor="notes">
          <Input id="notes" {...register("notes")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 4: Write `PaymentModal.tsx`**

```tsx
// frontend/src/features/debts/components/PaymentModal.tsx
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useAccounts } from "@/features/accounts/hooks";
import { useAddPayment } from "../hooks";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  account_id: z.string().min(1, "Account is required."),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  paid_at: z.string().min(1, "Date is required."),
  description: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface PaymentModalProps { debtId: number; debtName: string; onClose: () => void; }

export function PaymentModal({ debtId, debtName, onClose }: PaymentModalProps) {
  const [topError, setTopError] = useState<string | null>(null);
  const accounts = useAccounts();

  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { account_id: "", amount: "", paid_at: today(), description: "" },
    });

  const apiToForm = useApiErrorToForm(setError);
  const addPayment = useAddPayment();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      await addPayment.mutateAsync({ debtId, data: { account_id: Number(values.account_id), amount: values.amount, paid_at: values.paid_at, description: values.description ?? "" } });
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={`Add Payment — ${debtName}`} size="sm">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Account" htmlFor="account_id" error={errors.account_id?.message}>
          <Select id="account_id" invalid={Boolean(errors.account_id)} {...register("account_id")}>
            <option value="">Select account…</option>
            {accounts.data?.results.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </Select>
        </Field>
        <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
          <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
        </Field>
        <Field label="Date" htmlFor="paid_at" error={errors.paid_at?.message}>
          <Input id="paid_at" type="date" invalid={Boolean(errors.paid_at)} {...register("paid_at")} />
        </Field>
        <Field label="Description" htmlFor="description">
          <Input id="description" {...register("description")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null} Add Payment
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

- [ ] **Step 5: Write `DebtsPage.tsx`**

```tsx
// frontend/src/features/debts/pages/DebtsPage.tsx
import { useState } from "react";
import { Plus, Pencil, Trash2, ChevronDown, ChevronRight, CreditCard } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useDebts, useDeleteDebt } from "../hooks";
import { DebtModal } from "../components/DebtModal";
import { PaymentModal } from "../components/PaymentModal";
import type { Debt } from "../api";

interface PaymentTarget { debtId: number; debtName: string; }

export function DebtsPage() {
  const { data, isPending, isError } = useDebts();
  const createModal = useOpenClose();
  const editModal = useEditModal<Debt>();
  const deleteConfirm = useDeleteConfirm();
  const deleteDebt = useDeleteDebt();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [paymentTarget, setPaymentTarget] = useState<PaymentTarget | null>(null);

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError) return <Alert tone="danger">Borçlar yüklenemedi.</Alert>;

  const toggle = (id: number) => setExpandedId((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Debts</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} debt{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Debt</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No debts recorded.</p>
      ) : (
        <div className="space-y-2">
          {data.results.map((debt) => {
            const paidPct = debt.original_amount !== "0.00000000"
              ? Math.min(100, (1 - Number(debt.current_balance) / Number(debt.original_amount)) * 100)
              : 100;
            const isExpanded = expandedId === debt.id;

            return (
              <div key={debt.id} className="rounded-lg border border-hairline bg-surface overflow-hidden">
                <div
                  className="flex items-center gap-3 px-5 py-4 cursor-pointer hover:bg-surface-2/50"
                  onClick={() => toggle(debt.id)}
                >
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-ink-muted shrink-0" /> : <ChevronRight className="h-4 w-4 text-ink-muted shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-medium text-ink">{debt.name}</p>
                      <div className="flex items-center gap-4 text-sm shrink-0">
                        <span className="text-ink-muted num">
                          {Number(debt.current_balance).toLocaleString(undefined, { maximumFractionDigits: 2 })} / {Number(debt.original_amount).toLocaleString(undefined, { maximumFractionDigits: 2 })} {debt.currency_code}
                        </span>
                        {debt.is_settled && <span className="text-xs px-2 py-0.5 rounded-full bg-success/15 text-success font-medium">Settled</span>}
                      </div>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-surface-2 overflow-hidden">
                      <div className="h-full rounded-full bg-brand-cyan transition-all" style={{ width: `${paidPct}%` }} />
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="icon" onClick={() => editModal.open(debt)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(debt.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-hairline px-5 py-4 space-y-3 bg-surface-2/30">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                      <div><p className="text-xs text-ink-muted mb-0.5">Monthly Payment</p><p className="font-medium num text-ink">{Number(debt.expected_monthly_payment).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p></div>
                      {debt.interest_rate_pct && <div><p className="text-xs text-ink-muted mb-0.5">Interest</p><p className="font-medium num text-ink">{debt.interest_rate_pct}%</p></div>}
                      {debt.due_day && <div><p className="text-xs text-ink-muted mb-0.5">Due Day</p><p className="font-medium text-ink">Day {debt.due_day}</p></div>}
                      {debt.notes && <div className="col-span-2"><p className="text-xs text-ink-muted mb-0.5">Notes</p><p className="text-ink">{debt.notes}</p></div>}
                    </div>
                    <Button
                      variant="outline" size="sm"
                      onClick={() => setPaymentTarget({ debtId: debt.id, debtName: debt.name })}
                    >
                      <CreditCard className="h-4 w-4" /> Add Payment
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {createModal.isOpen && <DebtModal debt={null} onClose={createModal.close} />}
      {editModal.selected && <DebtModal debt={editModal.selected} onClose={editModal.close} />}
      {paymentTarget && (
        <PaymentModal
          debtId={paymentTarget.debtId}
          debtName={paymentTarget.debtName}
          onClose={() => setPaymentTarget(null)}
        />
      )}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId) { await deleteDebt.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteDebt.isPending}
      />
    </div>
  );
}
```

- [ ] **Step 6: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/debts/
git commit -m "feat: Debts CRUD page with expandable rows and payment modal"
```

---

## Task 8: Router Wiring + Cleanup

**Files:**
- Modify: `frontend/src/router.tsx`
- Delete: `frontend/src/features/dashboard/pages/DashboardPlaceholder.tsx`

- [ ] **Step 1: Update `router.tsx`**

Replace entirely:

```tsx
// frontend/src/router.tsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { PublicOnlyRoute } from "./routes/PublicOnlyRoute";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./features/auth/pages/LoginPage";
import { RegisterPage } from "./features/auth/pages/RegisterPage";
import { VerifyEmailPage } from "./features/auth/pages/VerifyEmailPage";
import { PasswordResetRequestPage } from "./features/auth/pages/PasswordResetRequestPage";
import { PasswordResetConfirmPage } from "./features/auth/pages/PasswordResetConfirmPage";
import { DashboardPage } from "./features/dashboard/pages/DashboardPage";
import { AccountsPage } from "./features/accounts/pages/AccountsPage";
import { TransactionsPage } from "./features/transactions/pages/TransactionsPage";
import { CategoriesPage } from "./features/categories/pages/CategoriesPage";
import { BudgetsPage } from "./features/budgets/pages/BudgetsPage";
import { RecurringPage } from "./features/recurring/pages/RecurringPage";
import { DebtsPage } from "./features/debts/pages/DebtsPage";

export const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      { path: "/password-reset", element: <PasswordResetRequestPage /> },
      { path: "/password-reset/confirm", element: <PasswordResetConfirmPage /> },
    ],
  },
  { path: "/verify-email", element: <VerifyEmailPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <Navigate to="/dashboard" replace /> },
          { path: "/dashboard", element: <DashboardPage /> },
          { path: "/accounts", element: <AccountsPage /> },
          { path: "/transactions", element: <TransactionsPage /> },
          { path: "/categories", element: <CategoriesPage /> },
          { path: "/budgets", element: <BudgetsPage /> },
          { path: "/recurring", element: <RecurringPage /> },
          { path: "/debts", element: <DebtsPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
]);
```

- [ ] **Step 2: Delete DashboardPlaceholder**

```bash
rm frontend/src/features/dashboard/pages/DashboardPlaceholder.tsx
```

- [ ] **Step 3: Final TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Run all tests**

```bash
cd frontend && npm run test
```

Expected: all tests pass including `useModalState.test.ts`.

- [ ] **Step 5: Start dev server and smoke test each page**

```bash
cd frontend && npm run dev
```

Visit each route and verify:
- `/accounts` — table renders, Add button opens modal, edit/delete work
- `/transactions` — filter bar shows, table renders, Add button opens modal
- `/categories` — table renders, Add/edit/delete work
- `/budgets` — progress cards render, Add/edit/delete work
- `/recurring` — table renders, toggle changes active state, Add/edit/delete work
- `/debts` — rows expand on click, Add Payment opens modal, Add/edit/delete work

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router.tsx
git rm frontend/src/features/dashboard/pages/DashboardPlaceholder.tsx
git commit -m "feat: wire 6 CRUD pages into router, remove DashboardPlaceholder"
```
