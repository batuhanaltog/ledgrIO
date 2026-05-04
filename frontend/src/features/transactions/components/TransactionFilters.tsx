import { useEffect, useState } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAccounts } from "@/features/accounts/hooks";
import { useCategories } from "@/features/categories/hooks";
import { todayMonthRange } from "../utils";

export interface FilterValues {
  date_from: string;
  date_to: string;
  account_id: string;
  category_id: string;
  type: string;
  description: string;
}

interface Props {
  onChange: (f: FilterValues) => void;
}

export function TransactionFilters({ onChange }: Props) {
  const { date_from: df, date_to: dt } = todayMonthRange();
  const [filters, setFilters] = useState<FilterValues>({
    date_from: df,
    date_to: dt,
    account_id: "",
    category_id: "",
    type: "",
    description: "",
  });
  const accounts = useAccounts();
  const categories = useCategories();

  useEffect(() => {
    const timer = setTimeout(() => onChange(filters), 300);
    return () => clearTimeout(timer);
  }, [filters, onChange]);

  const set =
    (key: keyof FilterValues) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setFilters((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <div className="flex flex-wrap gap-3">
      <Input
        type="date"
        value={filters.date_from}
        onChange={set("date_from")}
        className="w-36"
      />
      <Input
        type="date"
        value={filters.date_to}
        onChange={set("date_to")}
        className="w-36"
      />
      <Select
        value={filters.account_id}
        onChange={set("account_id")}
        className="w-40"
      >
        <option value="">All Accounts</option>
        {accounts.data?.results.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </Select>
      <Select
        value={filters.category_id}
        onChange={set("category_id")}
        className="w-40"
      >
        <option value="">All Categories</option>
        {categories.data?.results.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </Select>
      <Select value={filters.type} onChange={set("type")} className="w-36">
        <option value="">All Types</option>
        <option value="income">Income</option>
        <option value="expense">Expense</option>
      </Select>
      <Input
        placeholder="Search description…"
        value={filters.description}
        onChange={set("description")}
        className="w-48"
      />
    </div>
  );
}
