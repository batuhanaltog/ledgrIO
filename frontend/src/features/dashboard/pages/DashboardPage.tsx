import { useAuthStore } from "@/stores/auth";
import { useAccountsSummary } from "@/features/accounts/hooks";
import { useTransactionSummary } from "@/features/transactions/hooks";
import { useBudgets } from "@/features/budgets/hooks";
import { StatCard } from "../components/StatCard";
import { AccountsWidget } from "../components/AccountsWidget";
import { RecentTransactionsWidget } from "../components/RecentTransactionsWidget";
import { CategoryBreakdownWidget } from "../components/CategoryBreakdownWidget";
import { BudgetOverviewWidget } from "../components/BudgetOverviewWidget";

const thisMonth = () => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
};

function fmt(value: string | undefined, currency: string | undefined) {
  if (!value || !currency) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const currency = user?.default_currency_code ?? "USD";

  const { date_from, date_to } = thisMonth();
  const summary = useAccountsSummary();
  const txSummary = useTransactionSummary({ date_from, date_to });
  const budgets = useBudgets();

  const totalAssets = summary.data ? fmt(summary.data.total_assets, summary.data.base_currency) : "—";
  const netThisMonth = txSummary.data ? fmt(txSummary.data.net, currency) : "—";
  const netVal = txSummary.data ? Number(txSummary.data.net) : 0;

  const budgetList = budgets.data?.results ?? [];
  const okBudgets = budgetList.filter((b) => b.usage_pct == null || Number(b.usage_pct) < 1).length;
  const budgetStat = budgets.data ? `${okBudgets} / ${budgetList.length} normal` : "—";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Hoş geldin{user?.email ? `, ${user.email}` : ""}.
        </p>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Net Varlık" value={totalAssets} />
        <StatCard
          title="Bu Ay Net"
          value={netThisMonth}
          trend={netVal > 0 ? "up" : netVal < 0 ? "down" : "neutral"}
        />
        <StatCard title="Bütçe Durumu" value={budgetStat} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <CategoryBreakdownWidget />
        </div>
        <BudgetOverviewWidget />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AccountsWidget />
        <RecentTransactionsWidget />
      </div>
    </div>
  );
}
