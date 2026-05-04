import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useAccountsSummary, useAccounts } from "@/features/accounts/hooks";

function fmt(value: string, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function AccountsWidget() {
  const summary = useAccountsSummary();
  const accounts = useAccounts();

  if (summary.isPending || accounts.isPending) {
    return (
      <Card>
        <CardBody className="flex items-center justify-center py-10">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (summary.isError || accounts.isError) {
    return (
      <Card>
        <CardBody>
          <Alert tone="danger">Hesaplar yüklenemedi.</Alert>
        </CardBody>
      </Card>
    );
  }

  const { base_currency, total_assets, stale_fx_warning } = summary.data;
  const list = accounts.data.results.filter((a) => a.is_active);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hesaplar</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        {stale_fx_warning ? (
          <Alert tone="warn">FX kurları güncel olmayabilir.</Alert>
        ) : null}

        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold num text-ink">
            {fmt(total_assets, base_currency)}
          </span>
          <span className="text-xs text-ink-subtle">toplam net varlık</span>
        </div>

        {list.length === 0 ? (
          <p className="text-sm text-ink-muted">Henüz hesap eklenmedi.</p>
        ) : (
          <ul className="divide-y divide-hairline">
            {list.map((acc) => (
              <li key={acc.id} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-ink">{acc.name}</p>
                  <p className="text-xs text-ink-subtle capitalize">{acc.account_type}</p>
                </div>
                <span className="text-sm num font-semibold text-ink">
                  {fmt(acc.current_balance, acc.currency_code)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
