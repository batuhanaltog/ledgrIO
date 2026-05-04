import { useState } from "react";
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
import { useAddPayment } from "../hooks";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  account_id: z.string().min(1, "Account is required."),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  paid_at: z.string().min(1, "Date is required."),
  description: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface PaymentModalProps { debtId: number; debtName: string; onClose: () => void; }

export function PaymentModal({ debtId, debtName, onClose }: PaymentModalProps) {
  const [topError, setTopError] = useState<string | null>(null);
  const accounts = useAccounts();

  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { account_id: "", amount: "", paid_at: today(), description: "" },
    });

  const apiToForm = useApiErrorToForm(setError);
  const addPayment = useAddPayment();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      await addPayment.mutateAsync({
        debtId,
        data: { account_id: Number(values.account_id), amount: values.amount, paid_at: values.paid_at, description: values.description ?? "" },
      });
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={`Add Payment — ${debtName}`} size="sm">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Account" htmlFor="account_id" error={errors.account_id?.message}>
          <Select id="account_id" invalid={Boolean(errors.account_id)} {...register("account_id")}>
            <option value="">Select account…</option>
            {accounts.data?.results.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </Select>
        </Field>
        <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
          <Input id="amount" inputMode="decimal" invalid={Boolean(errors.amount)} {...register("amount")} />
        </Field>
        <Field label="Date" htmlFor="paid_at" error={errors.paid_at?.message}>
          <Input id="paid_at" type="date" invalid={Boolean(errors.paid_at)} {...register("paid_at")} />
        </Field>
        <Field label="Description" htmlFor="description">
          <Input id="description" {...register("description")} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Spinner />}
            Add Payment
          </Button>
        </div>
      </form>
    </Modal>
  );
}
