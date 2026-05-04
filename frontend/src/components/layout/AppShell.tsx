import { type ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Wallet,
  ArrowLeftRight,
  Tags,
  Repeat,
  Receipt,
  PieChart,
  LogOut,
} from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/stores/auth";
import { useLogout, useMe } from "@/features/auth/hooks";
import { cn } from "@/lib/cn";

const NAV: { to: string; label: string; icon: typeof LayoutDashboard }[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/accounts", label: "Accounts", icon: Wallet },
  { to: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { to: "/categories", label: "Categories", icon: Tags },
  { to: "/recurring", label: "Recurring", icon: Repeat },
  { to: "/debts", label: "Debts", icon: Receipt },
  { to: "/budgets", label: "Budgets", icon: PieChart },
];

function SidebarLink({
  to,
  label,
  icon: Icon,
}: {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150",
          "text-white/70 hover:text-white hover:bg-white/5",
          isActive && "bg-brand-cyan/15 text-white ring-1 ring-brand-cyan/30",
        )
      }
    >
      <Icon className="h-4 w-4" />
      {label}
    </NavLink>
  );
}

export function AppShell({ children }: { children?: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  useMe();
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[260px_1fr] bg-canvas">
      <aside className="hidden lg:flex flex-col bg-brand-navy text-white">
        <div className="px-5 py-6">
          <Logo
            variant="full"
            className="[&_span:first-child>span:first-child]:text-white [&_span:first-child>span:last-child]:text-brand-cyan"
          />
        </div>
        <nav className="flex-1 px-3 space-y-1">
          {NAV.map((n) => (
            <SidebarLink key={n.to} {...n} />
          ))}
        </nav>
        <div className="p-4 border-t border-white/10">
          <div className="text-xs text-white/50 mb-1">Signed in as</div>
          <div className="text-sm font-medium truncate">{user?.email ?? "—"}</div>
          <Button
            variant="ghost"
            size="sm"
            className="mt-3 w-full justify-start text-white/80 hover:bg-white/5 hover:text-white"
            onClick={async () => {
              await logout.mutateAsync();
              navigate("/login", { replace: true });
            }}
          >
            <LogOut className="h-4 w-4" /> Sign out
          </Button>
        </div>
      </aside>

      <main className="min-h-screen">
        <header className="lg:hidden flex items-center justify-between px-5 py-4 border-b border-hairline bg-surface">
          <Logo variant="full" />
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              await logout.mutateAsync();
              navigate("/login", { replace: true });
            }}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </header>
        <div className="px-6 py-8 lg:px-10 lg:py-10 max-w-6xl mx-auto">
          {children ?? <Outlet />}
        </div>
      </main>
    </div>
  );
}
