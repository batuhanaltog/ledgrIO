import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useTransactionSummary } from "@/features/transactions/hooks";

const thisMonth = () => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
};

export function CategoryBreakdownWidget() {
  const { date_from, date_to } = thisMonth();
  const { data, isPending, isError } = useTransactionSummary({ date_from, date_to });

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
          <Alert tone="danger">Kategori verileri yüklenemedi.</Alert>
        </CardBody>
      </Card>
    );
  }

  const rows = data.by_category
    .filter((r) => Number(r.total) > 0)
    .sort((a, b) => Number(b.total) - Number(a.total))
    .slice(0, 8)
    .map((r) => ({ name: r.category__name || "Kategorisiz", total: Number(r.total) }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bu Ay — Kategori Dağılımı</CardTitle>
      </CardHeader>
      <CardBody>
        {rows.length === 0 ? (
          <p className="text-sm text-ink-muted">Bu ay için işlem bulunamadı.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={rows}
              layout="vertical"
              margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
            >
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: "#4B5B75" }}
                tickFormatter={(v) =>
                  new Intl.NumberFormat(undefined, {
                    notation: "compact",
                    maximumFractionDigits: 1,
                  }).format(v)
                }
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11, fill: "#4B5B75" }}
                axisLine={false}
                tickLine={false}
                width={90}
              />
              <Tooltip
                formatter={(v: number) =>
                  new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(v)
                }
                contentStyle={{
                  fontSize: 12,
                  border: "1px solid #E0E6EE",
                  borderRadius: 6,
                  color: "#0F2547",
                }}
              />
              <Bar dataKey="total" radius={[0, 4, 4, 0]} maxBarSize={20}>
                {rows.map((_, i) => (
                  <Cell
                    key={i}
                    fill={i === 0 ? "rgb(47 176 222)" : `rgb(47 176 222 / ${1 - i * 0.1})`}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardBody>
    </Card>
  );
}
