import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useRecentTransactions } from "@/features/transactions/hooks";
import { cn } from "@/lib/cn";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}

export function RecentTransactionsWidget() {
  const { data, isPending, isError } = useRecentTransactions();

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
          <Alert tone="danger">İşlemler yüklenemedi.</Alert>
        </CardBody>
      </Card>
    );
  }

  const txns = data.results;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Son İşlemler</CardTitle>
      </CardHeader>
      <CardBody>
        {txns.length === 0 ? (
          <p className="text-sm text-ink-muted">Henüz işlem eklenmedi.</p>
        ) : (
          <ul className="divide-y divide-hairline">
            {txns.map((tx) => (
              <li key={tx.id} className="flex items-center gap-3 py-2">
                <span className="text-xs text-ink-subtle num w-12 shrink-0">
                  {fmtDate(tx.date)}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink truncate">
                    {tx.description || tx.category?.name || "—"}
                  </p>
                  {tx.category ? (
                    <p className="text-xs text-ink-subtle">{tx.category.name}</p>
                  ) : null}
                </div>
                <span
                  className={cn(
                    "text-sm num font-semibold shrink-0",
                    tx.type === "income" ? "text-success" : "text-danger",
                  )}
                >
                  {tx.type === "income" ? "+" : "−"}
                  {Number(tx.amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}{" "}
                  {tx.currency_code}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
