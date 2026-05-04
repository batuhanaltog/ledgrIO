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
