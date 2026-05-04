import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useCategories } from "@/features/categories/hooks";
import { useCreateBudget, useUpdateBudget } from "../hooks";
import type { Budget } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  category_id: z.string().optional(),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  date_from: z.string().min(1, "Date from is required."),
  date_to: z.string().min(1, "Date to is required."),
  alert_threshold: z.string().optional(),
}).refine((d) => !d.date_to || !d.date_from || d.date_to >= d.date_from, {
  message: "Date to must be on or after date from.", path: ["date_to"],
});
type FormInput = z.infer<typeof schema>;

function thisMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const last = new Date(y, now.getMonth() + 1, 0).getDate();
  return { date_from: `${y}-${m}-01`, date_to: `${y}-${m}-${last}` };
}

interface BudgetModalProps { budget: Budget | null; onClose: () => void; }

export function BudgetModal({ budget, onClose }: BudgetModalProps) {
  const isEdit = budget !== null;
  const [topError, setTopError] = useState<string | null>(null);
  const categories = useCategories();
  const { date_from, date_to } = thisMonthRange();

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", category_id: "", amount: "", date_from, date_to, alert_threshold: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      name: budget.name,
      category_id: budget.category ? String(budget.category.id) : "",
      amount: budget.amount.replace(/\.?0+$/, ""),
      date_from: budget.date_from, date_to: budget.date_to,
      alert_threshold: budget.alert_threshold
        ? (parseFloat(budget.alert_threshold) * 100).toString().replace(/\.?0+$/, "")
        : "",
    } : { name: "", category_id: "", amount: "", date_from, date_to, alert_threshold: "" });
  }, [budget, isEdit, reset, date_from, date_to]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateBudget();
  const update = useUpdateBudget();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    const payload = {
      name: values.name,
      category_id: values.category_id ? Number(values.category_id) : null,
      amount: values.amount,
      date_from: values.date_from,
      date_to: values.date_to,
      alert_threshold: values.alert_threshold
        ? (parseFloat(values.alert_threshold) / 100).toString()
        : null,
    };
    try {
      if (isEdit) await update.mutateAsync({ id: budget.id, data: payload });
      else await create.mutateAsync(payload);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Budget" : "New Budget"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <Field label="Category" htmlFor="category_id" hint="Leave empty to track all categories.">
          <Select id="category_id" {...register("category_id")}>
            <option value="">All categories</option>
            {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Field>
        <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
          <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Date From" htmlFor="date_from" error={errors.date_from?.message}>
            <Input id="date_from" type="date" invalid={Boolean(errors.date_from)} {...register("date_from")} />
          </Field>
          <Field label="Date To" htmlFor="date_to" error={errors.date_to?.message}>
            <Input id="date_to" type="date" invalid={Boolean(errors.date_to)} {...register("date_to")} />
          </Field>
        </div>
        <Field label="Alert Threshold (%)" htmlFor="alert_threshold" hint="e.g. 80 to alert at 80% spent. Leave empty to disable.">
          <Input id="alert_threshold" inputMode="decimal" placeholder="80" {...register("alert_threshold")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Spinner />}
            {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
