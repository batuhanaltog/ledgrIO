import { type ReactNode } from "react";
import { ShieldCheck, Lock, LineChart } from "lucide-react";
import { Logo } from "@/components/brand/Logo";

interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}

const TRUST_POINTS = [
  {
    icon: LineChart,
    text: "Multi-currency, multi-account ledger with FX snapshots — no spreadsheet drift.",
  },
  {
    icon: Lock,
    text: "Your data lives in your Postgres. No third-party financial connectors.",
  },
  {
    icon: ShieldCheck,
    text: "Decimal precision (banker's rounding), atomic writes, daily off-site backups.",
  },
];

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* Brand panel */}
      <aside className="hidden lg:flex flex-col justify-between bg-brand-navy text-white relative overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "radial-gradient(1200px 600px at 110% -10%, rgb(47 176 222 / 0.45), transparent 60%), radial-gradient(700px 400px at -10% 110%, rgb(27 110 140 / 0.45), transparent 60%)",
          }}
        />
        <div className="relative p-10">
          <Logo variant="full" onDark />
        </div>

        <div className="relative px-10 pb-12 max-w-xl">
          <h2 className="text-3xl font-semibold tracking-tight leading-tight">
            Personal finance,
            <br />
            <span className="text-brand-cyan">without the spreadsheet.</span>
          </h2>
          <p className="mt-4 text-white/70 text-base leading-relaxed">
            Built for households, not SaaS dashboards. Track income, expenses, debts and
            recurring entries across accounts and currencies — with the precision
            accountants expect.
          </p>

          <ul className="mt-10 space-y-5">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex gap-3">
                <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand-cyan/15 text-brand-cyan ring-1 ring-brand-cyan/30">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="text-sm text-white/85 leading-relaxed">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative p-10 text-xs text-white/50">
          © {new Date().getFullYear()} Ledgr.io · Self-hosted personal finance
        </div>
      </aside>

      {/* Form panel */}
      <main className="flex flex-col px-6 py-10 sm:px-12 lg:px-16">
        <div className="lg:hidden mb-10">
          <Logo variant="full" />
        </div>

        <div className="flex-1 flex items-center">
          <div className="w-full max-w-md">
            <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
            {subtitle ? (
              <p className="mt-2 text-sm text-ink-muted leading-relaxed">{subtitle}</p>
            ) : null}
            <div className="mt-8">{children}</div>
            {footer ? <div className="mt-8 text-sm text-ink-muted">{footer}</div> : null}
          </div>
        </div>
      </main>
    </div>
  );
}
