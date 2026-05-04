import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useApiErrorToForm } from "@/features/auth/useFormErrorMapping";
import { useCreateDebt, useUpdateDebt } from "../hooks";
import type { Debt } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  original_amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  expected_monthly_payment: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  currency_code: z.string().length(3).regex(/^[A-Z]{3}$/),
  interest_rate_pct: z.string().optional().refine(
    (v) => !v || /^\d+(\.\d+)?$/.test(v),
    { message: "Enter a valid rate." }
  ),
  due_day: z.string().optional().refine(
    (v) => !v || (/^\d+$/.test(v) && Number(v) >= 1 && Number(v) <= 31),
    { message: "Enter a day between 1 and 31." }
  ),
  notes: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface DebtModalProps { debt: Debt | null; onClose: () => void; }

export function DebtModal({ debt, onClose }: DebtModalProps) {
  const isEdit = debt !== null;
  const [topError, setTopError] = useState<string | null>(null);

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", original_amount: "", expected_monthly_payment: "", currency_code: "USD", interest_rate_pct: "", due_day: "", notes: "" },
    });

  useEffect(() => {
    reset(isEdit ? {
      name: debt.name,
      original_amount: debt.original_amount.replace(/\.?0+$/, ""),
      expected_monthly_payment: debt.expected_monthly_payment.replace(/\.?0+$/, ""),
      currency_code: debt.currency_code,
      interest_rate_pct: debt.interest_rate_pct ? debt.interest_rate_pct.replace(/\.?0+$/, "") : "",
      due_day: debt.due_day ? String(debt.due_day) : "",
      notes: debt.notes ?? "",
    } : { name: "", original_amount: "", expected_monthly_payment: "", currency_code: "USD", interest_rate_pct: "", due_day: "", notes: "" });
  }, [debt, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateDebt();
  const update = useUpdateDebt();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      if (isEdit) {
        await update.mutateAsync({ id: debt.id, data: {
          name: values.name,
          expected_monthly_payment: values.expected_monthly_payment,
          interest_rate_pct: values.interest_rate_pct || null,
          due_day: values.due_day ? Number(values.due_day) : null,
          notes: values.notes,
        }});
      } else {
        await create.mutateAsync({
          name: values.name, original_amount: values.original_amount,
          expected_monthly_payment: values.expected_monthly_payment,
          currency_code: values.currency_code,
          interest_rate_pct: values.interest_rate_pct || null,
          due_day: values.due_day ? Number(values.due_day) : null,
          notes: values.notes,
        });
      }
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Debt" : "New Debt"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          {!isEdit && (
            <Field label="Original Amount" htmlFor="original_amount" error={errors.original_amount?.message} className="col-span-2">
              <Input id="original_amount" inputMode="decimal" invalid={Boolean(errors.original_amount)} {...register("original_amount")} />
            </Field>
          )}
          <Field label="Monthly Payment" htmlFor="expected_monthly_payment" error={errors.expected_monthly_payment?.message}>
            <Input id="expected_monthly_payment" inputMode="decimal" invalid={Boolean(errors.expected_monthly_payment)} {...register("expected_monthly_payment")} />
          </Field>
          {!isEdit && (
            <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
              <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
            </Field>
          )}
          <Field label="Interest Rate (%)" htmlFor="interest_rate_pct" hint="Optional">
            <Input id="interest_rate_pct" inputMode="decimal" {...register("interest_rate_pct")} />
          </Field>
          <Field label="Due Day" htmlFor="due_day" hint="Day of month (1–31), optional">
            <Input id="due_day" inputMode="numeric" {...register("due_day")} />
          </Field>
        </div>
        <Field label="Notes" htmlFor="notes">
          <textarea
            id="notes"
            rows={3}
            className="w-full rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand resize-none"
            {...register("notes")}
          />
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
