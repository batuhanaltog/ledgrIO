import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useBudgets } from "@/features/budgets/hooks";
import { cn } from "@/lib/cn";
import type { Budget } from "@/features/budgets/api";

function usageColor(pct: number) {
  if (pct >= 100) return "bg-danger";
  if (pct >= 75) return "bg-warn";
  return "bg-success";
}

function BudgetRow({ budget }: { budget: Budget }) {
  const pct = budget.usage_pct != null ? Math.min(Number(budget.usage_pct) * 100, 100) : 0;
  const remaining = Number(budget.remaining);

  return (
    <li className="space-y-1">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-ink">{budget.name}</p>
        <p className={cn("text-xs num font-semibold", remaining < 0 ? "text-danger" : "text-ink-muted")}>
          {remaining < 0 ? "−" : ""}
          {Math.abs(remaining).toLocaleString(undefined, { maximumFractionDigits: 2 })} kalan
        </p>
      </div>
      <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", usageColor(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-ink-subtle">
        {Number(budget.spent).toLocaleString(undefined, { maximumFractionDigits: 2 })} /{" "}
        {Number(budget.amount).toLocaleString(undefined, { maximumFractionDigits: 2 })} harcandı
      </p>
    </li>
  );
}

export function BudgetOverviewWidget() {
  const { data, isPending, isError } = useBudgets();

  if (isPending) {
    return (
      <Card>
        <CardBody className="flex items-center justify-center py-10">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardBody>
          <Alert tone="danger">Bütçeler yüklenemedi.</Alert>
        </CardBody>
      </Card>
    );
  }

  const budgets = data.results;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bütçe Durumu</CardTitle>
      </CardHeader>
      <CardBody>
        {budgets.length === 0 ? (
          <p className="text-sm text-ink-muted">Henüz bütçe oluşturulmadı.</p>
        ) : (
          <ul className="space-y-4">
            {budgets.map((b) => (
              <BudgetRow key={b.id} budget={b} />
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
