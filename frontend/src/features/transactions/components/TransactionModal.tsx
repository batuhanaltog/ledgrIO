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
import { useCreateTransaction, useUpdateTransaction } from "../hooks";
import type { Transaction } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

const schema = z.object({
  account_id: z.string().min(1, "Account is required."),
  type: z.enum(["income", "expense"]),
  amount: z.string().regex(/^\d+(\.\d+)?$/, "Enter a valid amount."),
  currency_code: z
    .string()
    .length(3)
    .regex(/^[A-Z]{3}$/),
  category_id: z.string().optional(),
  date: z.string().min(1, "Date is required."),
  description: z.string().optional(),
  reference: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface TransactionModalProps {
  transaction: Transaction | null;
  onClose: () => void;
}

export function TransactionModal({ transaction, onClose }: TransactionModalProps) {
  const isEdit = transaction !== null;
  const [topError, setTopError] = useState<string | null>(null);
  const accounts = useAccounts();
  const categories = useCategories();

  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput>({
    resolver: zodResolver(schema),
    defaultValues: {
      account_id: "",
      type: "expense",
      amount: "",
      currency_code: "USD",
      category_id: "",
      date: today(),
      description: "",
      reference: "",
    },
  });

  useEffect(() => {
    reset(
      isEdit
        ? {
            account_id: String(transaction.account_id),
            type: transaction.type,
            amount: transaction.amount.replace(/\.?0+$/, ""),
            currency_code: transaction.currency_code,
            category_id: transaction.category
              ? String(transaction.category.id)
              : "",
            date: transaction.date,
            description: transaction.description,
            reference: transaction.reference,
          }
        : {
            account_id: "",
            type: "expense",
            amount: "",
            currency_code: "USD",
            category_id: "",
            date: today(),
            description: "",
            reference: "",
          },
    );
  }, [transaction, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateTransaction();
  const update = useUpdateTransaction();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    const payload = {
      account_id: Number(values.account_id),
      type: values.type,
      amount: values.amount,
      currency_code: values.currency_code,
      category_id: values.category_id ? Number(values.category_id) : null,
      date: values.date,
      description: values.description ?? "",
      reference: values.reference ?? "",
    };
    try {
      if (isEdit) await update.mutateAsync({ id: transaction.id, data: payload });
      else await create.mutateAsync(payload);
      onClose();
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? "Edit Transaction" : "New Transaction"}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <div className="grid grid-cols-2 gap-4">
          <Field
            label="Account"
            htmlFor="account_id"
            error={errors.account_id?.message}
            className="col-span-2"
          >
            <Select
              id="account_id"
              invalid={Boolean(errors.account_id)}
              {...register("account_id")}
            >
              <option value="">Select account…</option>
              {accounts.data?.results.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Type" htmlFor="type">
            <Select id="type" {...register("type")}>
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </Select>
          </Field>
          <Field label="Amount" htmlFor="amount" error={errors.amount?.message}>
            <Input
              id="amount"
              inputMode="decimal"
              invalid={Boolean(errors.amount)}
              {...register("amount")}
            />
          </Field>
          <Field
            label="Currency"
            htmlFor="currency_code"
            error={errors.currency_code?.message}
          >
            <Input
              id="currency_code"
              placeholder="USD"
              invalid={Boolean(errors.currency_code)}
              {...register("currency_code")}
            />
          </Field>
          <Field label="Date" htmlFor="date" error={errors.date?.message}>
            <Input
              id="date"
              type="date"
              invalid={Boolean(errors.date)}
              {...register("date")}
            />
          </Field>
          <Field label="Category" htmlFor="category_id" className="col-span-2">
            <Select id="category_id" {...register("category_id")}>
              <option value="">No category</option>
              {categories.data?.results.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Description"
            htmlFor="description"
            className="col-span-2"
          >
            <Input id="description" {...register("description")} />
          </Field>
          <Field label="Reference" htmlFor="reference" className="col-span-2">
            <Input id="reference" {...register("reference")} />
          </Field>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Spinner />}
            {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
