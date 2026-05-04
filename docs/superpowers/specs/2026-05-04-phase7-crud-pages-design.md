# Phase 7 CRUD Pages — Design Spec

**Date:** 2026-05-04  
**Scope:** 6 sidebar pages (Accounts, Transactions, Categories, Budgets, Recurring, Debts) with List + Modal interaction model  
**Stack:** React 18 / Vite / TS / TanStack Query / React Hook Form + Zod / Tailwind

---

## 1. Shared Infrastructure

### New primitives (`frontend/src/components/ui/`)

**`Modal.tsx`**
- Props: `open: boolean`, `onClose: () => void`, `title: string`, `children: ReactNode`, `size?: "sm" | "md" | "lg"` (default `md`)
- Backdrop click closes modal
- ESC key closes modal
- Focus trap inside modal while open

**`ConfirmDialog.tsx`**
- Wraps `Modal` (size `sm`)
- Props: `open`, `onClose`, `onConfirm`, `loading: boolean`, `message?: string`
- Default message: "Bu kaydı silmek istediğine emin misin?"
- Confirm button shows spinner while `loading` is true

**`useModalState.ts`** (`frontend/src/hooks/`)
- Exports three composable hooks:
  - `useOpenClose()` → `{ isOpen, open, close }` — for create modal
  - `useEditModal<T>()` → `{ selected: T | null, open(item: T), close }` — for edit modal
  - `useDeleteConfirm()` → `{ pendingId: number | null, confirm(id), cancel }` — for delete confirmation

### Existing primitives (unchanged)
`Button`, `Input`, `Field`, `Select`, `Card`, `Alert`, `Spinner`

---

## 2. Page Designs

### 2.1 Accounts (`/accounts`)

**List columns:** Name | Type | Currency | Balance | Transactions | Actions (edit, delete)

**Create/Edit Modal (md):**
- Name (text, required)
- Account type (select: cash / bank / credit_card / savings)
- Currency code (text, default USD)
- Opening balance (decimal, required)
- Notes (textarea, optional)

**Delete:** ConfirmDialog. Backend returns error if account has transactions — surface as Alert inside dialog.

**New API methods:** `accounts.create`, `accounts.update`, `accounts.delete`

---

### 2.2 Transactions (`/transactions`)

**Filter bar (above table):**
- date_from / date_to (date inputs, default: current month)
- Account (select, nullable)
- Category (select, nullable)
- Type (select: all / income / expense)
- Description search (text, 300 ms debounce)

**List columns:** Date | Description | Category | Account | Type | Amount | Actions

**Create/Edit Modal (md):**
- Account (select, required)
- Type (income / expense toggle)
- Amount (decimal, required)
- Currency code (text, default USD)
- Category (select, nullable)
- Date (date, required, default today)
- Description (text, optional)
- Reference (text, optional)

**New API methods:** `transactions.create`, `transactions.update`, `transactions.delete`

---

### 2.3 Categories (`/categories`)

No hierarchy — parent_id always null.

**List columns:** Name | Icon | Color (swatch) | Type | Actions

**Create/Edit Modal (sm):**
- Name (text, required)
- Type (income / expense select, required)
- Icon (text, optional)
- Color (color input, optional)

**New files:** `features/categories/api.ts`, `features/categories/hooks.ts`

---

### 2.4 Budgets (`/budgets`)

**List columns:** Name | Category | Amount | Spent | Remaining | Usage bar | Period | Actions

**Create/Edit Modal (md):**
- Name (text, required)
- Category (select, nullable — null = all categories)
- Amount (decimal, required)
- Date from (date, required)
- Date to (date, required, must be ≥ date_from)
- Alert threshold (0–100% slider or decimal input, nullable)

**New API methods:** `budgets.create`, `budgets.update`, `budgets.delete`

---

### 2.5 Recurring (`/recurring`)

**List columns:** Name | Account | Category | Type | Amount | Frequency | Next date | Active | Actions

**Create/Edit Modal (md):**
- Name (text, required)
- Account (select, required)
- Category (select, nullable)
- Type (income / expense)
- Amount (decimal, required)
- Currency code (text)
- Frequency (select: daily / weekly / monthly / yearly)
- Next date (date, required)
- Active toggle

**New files:** `features/recurring/api.ts`, `features/recurring/hooks.ts`

---

### 2.6 Debts (`/debts`)

**List columns:** Name | Direction (owed-by / owed-to) | Total | Paid | Remaining | Status | Actions

**Row expand:** Click row body to expand. Shows:
- Debt category, notes
- Payment history table: Date | Amount | Description | Delete action
- "Add Payment" button → opens payment modal

**Create/Edit Debt Modal (md):**
- Name (text, required)
- Direction (select: owed_by_me / owed_to_me)
- Debt category (select from debt categories endpoint)
- Total amount (decimal, required)
- Currency code
- Due date (date, nullable)
- Notes (textarea, optional)

**Add Payment Modal (sm):**
- Amount (decimal, required)
- Date (date, required, default today)
- Description (text, optional)

**New files:** `features/debts/api.ts`, `features/debts/hooks.ts`

---

## 3. Router

6 new routes added under `AppShell` in `router.tsx`:

```
/accounts       → AccountsPage
/transactions   → TransactionsPage
/categories     → CategoriesPage
/budgets        → BudgetsPage
/recurring      → RecurringPage
/debts          → DebtsPage
```

`DashboardPlaceholder.tsx` deleted.

---

## 4. API Additions

| Feature | New methods |
|---|---|
| accounts | `create`, `update`, `delete` |
| transactions | `create`, `update`, `delete` |
| categories | `list`, `create`, `update`, `delete` (new file) |
| budgets | `create`, `update`, `delete` |
| recurring | `list`, `create`, `update`, `delete` (new file; toggle via `update` with `is_active`) |
| debts | `list`, `create`, `update`, `delete`, `addPayment`, `deletePayment`, `listCategories` (new file) |

---

## 5. Testing

- `useModalState.test.ts` — open/close/reset behavior, no mocks
- 6 smoke tests (one per page) — TanStack Query mocked, list renders, Add button opens modal
- Backend tests unchanged (225 tests, 84% coverage)

---

## 6. Out of Scope

- Pagination UI (backend is paginated; pages show first page only for now)
- Mobile hamburger menu / drawer nav
- Inline row editing
- Bulk delete
- Category hierarchy (parent_id)
