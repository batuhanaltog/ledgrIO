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
import { useCreateCategory, useUpdateCategory } from "../hooks";
import type { Category } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  icon: z.string().optional(),
  color: z.string().optional(),
});
type FormInput = z.infer<typeof schema>;

interface CategoryModalProps {
  category: Category | null;
  onClose: () => void;
}

export function CategoryModal({ category, onClose }: CategoryModalProps) {
  const isEdit = category !== null;
  const [topError, setTopError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", icon: "", color: "" },
  });

  useEffect(() => {
    reset(
      isEdit
        ? { name: category.name, icon: category.icon, color: category.color }
        : { name: "", icon: "", color: "" },
    );
  }, [category, isEdit, reset]);

  const apiToForm = useApiErrorToForm(setError);
  const create = useCreateCategory();
  const update = useUpdateCategory();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      if (isEdit) await update.mutateAsync({ id: category.id, data: values });
      else await create.mutateAsync(values);
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
      title={isEdit ? "Edit Category" : "New Category"}
      size="sm"
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" invalid={Boolean(errors.name)} {...register("name")} />
        </Field>
        <Field label="Icon" htmlFor="icon" hint="e.g. leave blank">
          <Input id="icon" {...register("icon")} />
        </Field>
        <Field label="Color" htmlFor="color">
          <Input
            id="color"
            type="color"
            className="h-10 p-1 cursor-pointer"
            {...register("color")}
          />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
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
