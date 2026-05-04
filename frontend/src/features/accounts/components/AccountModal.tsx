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
import { useCreateAccount, useUpdateAccount } from "../hooks";
import type { Account } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  account_type: z.enum(["cash", "bank", "credit_card", "savings"]),
  currency_code: z.string().length(3, "3-letter ISO code required.").regex(/^[A-Z]{3}$/, "Use uppercase (e.g. USD)."),
  opening_balance: z.string().regex(/^-?\d+(\.\d+)?$/, "Enter a valid number."),
  notes: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface AccountModalProps {
  account: Account | null;
  onClose: () => void;
}

export function AccountModal({ account, onClose }: AccountModalProps) {
  const isEdit = account !== null;
  const [topError, setTopError] = useState<string | null>(null);

  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } =
    useForm<FormInput>({
      resolver: zodResolver(schema),
      defaultValues: { name: "", account_type: "bank", currency_code: "USD", opening_balance: "0", notes: "" },
    });

  useEffect(() => {
    reset(isEdit
      ? { name: account.name, account_type: account.account_type as FormInput["account_type"], currency_code: account.currency_code, opening_balance: account.opening_balance, notes: account.notes }
      : { name: "", account_type: "bank", currency_code: "USD", opening_balance: "0", notes: "" }
    );
  }, [account, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateAccount();
  const update = useUpdateAccount();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      if (isEdit) await update.mutateAsync({ id: account.id, data: values });
      else await create.mutateAsync(values);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Account" : "New Account"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <Field label="Type" htmlFor="account_type" error={errors.account_type?.message}>
          <Select id="account_type" {...register("account_type")}>
            <option value="bank">Bank</option>
            <option value="cash">Cash</option>
            <option value="credit_card">Credit Card</option>
            <option value="savings">Savings</option>
          </Select>
        </Field>
        <Field label="Currency" htmlFor="currency_code" error={errors.currency_code?.message}>
          <Input id="currency_code" placeholder="USD" invalid={Boolean(errors.currency_code)} {...register("currency_code")} />
        </Field>
        <Field label="Opening Balance" htmlFor="opening_balance" error={errors.opening_balance?.message}>
          <Input id="opening_balance" inputMode="decimal" invalid={Boolean(errors.opening_balance)} {...register("opening_balance")} />
        </Field>
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
