import { Card, CardBody } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function StatCard({ title, value, subtitle, trend, className }: StatCardProps) {
  return (
    <Card className={cn("flex-1", className)}>
      <CardBody>
        <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">{title}</p>
        <p
          className={cn(
            "mt-2 text-2xl font-bold num tracking-tight",
            trend === "up" && "text-success",
            trend === "down" && "text-danger",
            !trend && "text-ink",
          )}
        >
          {value}
        </p>
        {subtitle ? <p className="mt-1 text-xs text-ink-muted">{subtitle}</p> : null}
      </CardBody>
    </Card>
  );
}
