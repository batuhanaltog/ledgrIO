import { Card, CardBody, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { useAuthStore } from "@/stores/auth";

export function DashboardPlaceholder() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm text-ink-muted">Welcome back</p>
        <h1 className="text-2xl font-semibold tracking-tight text-ink mt-1">
          {user?.email ?? "your ledger"}
        </h1>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: "Net worth", hint: "Coming in Phase 7" },
          { label: "This month", hint: "Income vs. expense" },
          { label: "Open budgets", hint: "Subquery-backed usage" },
        ].map((c) => (
          <Card key={c.label}>
            <CardHeader>
              <CardTitle className="text-sm text-ink-muted font-medium">
                {c.label}
              </CardTitle>
            </CardHeader>
            <CardBody>
              <div className="num text-3xl font-semibold tracking-tight text-ink">
                —
              </div>
              <div className="text-xs text-ink-subtle mt-1">{c.hint}</div>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Frontend skeleton — Phase 6</CardTitle>
          <CardDescription>
            Auth flow is wired up against the existing API. Phase 7 brings the
            transactions, accounts, and budgets dashboards.
          </CardDescription>
        </CardHeader>
        <CardBody>
          <ul className="text-sm text-ink-muted space-y-1.5 list-disc pl-5">
            <li>Brand tokens sourced from the Ledgr.io logo (navy + cyan).</li>
            <li>Axios refresh-queue on 401, RHF + Zod forms with envelope mapping.</li>
            <li>Default currency: <span className="num font-medium">{user?.default_currency_code}</span></li>
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
