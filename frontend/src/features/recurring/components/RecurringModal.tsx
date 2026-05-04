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
import { useAccounts } from "@/features/accounts/hooks";
import { useCategories } from "@/features/categories/hooks";
import { useCreateRecurring, useUpdateRecurring } from "../hooks";
import type { RecurringTemplate } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  type: z.enum(["income", "expense"]),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  currency_code: z.string().length(3).regex(/^[A-Z]{3}$/),
  account_id: z.string().min(1, "Account is required."),
  category_id: z.string().optional(),
  description: z.string().min(1, "Description is required."),
  frequency: z.enum(["weekly", "monthly", "yearly"]),
  day_of_period: z.string().regex(/^\d+$/, "Enter a number."),
  start_date: z.string().min(1, "Start date is required."),
  end_date: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface RecurringModalProps { template: RecurringTemplate | null; onClose: () => void; }

export function RecurringModal({ template, onClose }: RecurringModalProps) {
  const isEdit = template !== null;
  const [topError, setTopError] = useState<string | null>(null);
  const accounts = useAccounts();
  const categories = useCategories();

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { type: "expense", amount: "", currency_code: "USD", account_id: "", category_id: "", description: "", frequency: "monthly", day_of_period: "1", start_date: today(), end_date: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      type: template.type,
      amount: template.amount.replace(/\.?0+$/, ""),
      currency_code: template.currency_code,
      account_id: String(template.account),
      category_id: template.category ? String(template.category) : "",
      description: template.description, frequency: template.frequency,
      day_of_period: String(template.day_of_period), start_date: template.start_date,
      end_date: template.end_date ?? "",
    } : { type: "expense", amount: "", currency_code: "USD", account_id: "", category_id: "", description: "", frequency: "monthly", day_of_period: "1", start_date: today(), end_date: "" });
  }, [template, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateRecurring();
  const update = useUpdateRecurring();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    const payload = {
      type: values.type, amount: values.amount, currency_code: values.currency_code,
      account_id: Number(values.account_id),
      category_id: values.category_id ? Number(values.category_id) : null,
      description: values.description, frequency: values.frequency,
      day_of_period: Number(values.day_of_period), start_date: values.start_date,
      end_date: values.end_date || null,
    };
    try {
      if (isEdit) await update.mutateAsync({ id: template.id, data: payload });
      else await create.mutateAsync(payload);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Recurring" : "New Recurring Template"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Description" htmlFor="description" error={errors.description?.message}>
          <Input id="description" invalid={Boolean(errors.description)} {...register("description")} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Type" htmlFor="type">
            <Select id="type" {...register("type")}>
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </Select>
          </Field>
          <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
            <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
          </Field>
          <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
            <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
          </Field>
          <Field label="Account" htmlFor="account_id" error={errors.account_id?.message}>
            <Select id="account_id" invalid={Boolean(errors.account_id)} {...register("account_id")}>
              <option value="">Select…</option>
              {accounts.data?.results.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </Select>
          </Field>
          <Field label="Category" htmlFor="category_id">
            <Select id="category_id" {...register("category_id")}>
              <option value="">No category</option>
              {categories.data?.results.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
          <Field label="Frequency" htmlFor="frequency">
            <Select id="frequency" {...register("frequency")}>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </Select>
          </Field>
          <Field label="Day of Period" htmlFor="day_of_period" error={errors.day_of_period?.message} hint="1–31 for monthly, 1–7 for weekly">
            <Input id="day_of_period" inputMode="numeric" invalid={Boolean(errors.day_of_period)} {...register("day_of_period")} />
          </Field>
          <Field label="Start Date" htmlFor="start_date" error={errors.start_date?.message}>
            <Input id="start_date" type="date" invalid={Boolean(errors.start_date)} {...register("start_date")} />
          </Field>
          <Field label="End Date" htmlFor="end_date" hint="Optional">
            <Input id="end_date" type="date" {...register("end_date")} />
          </Field>
        </div>
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
