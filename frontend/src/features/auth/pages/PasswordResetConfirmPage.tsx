import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { AuthLayout } from "../components/AuthLayout";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import {
  passwordResetConfirmSchema,
  type PasswordResetConfirmInput,
} from "../schemas";
import { authApi } from "../api";
import { parseApiError } from "@/lib/errors";

export function PasswordResetConfirmPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const tokenFromUrl = params.get("token") ?? "";
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetConfirmInput>({
    resolver: zodResolver(passwordResetConfirmSchema),
    defaultValues: { token: tokenFromUrl, new_password: "", confirm_password: "" },
  });

  const onSubmit = handleSubmit(async ({ token, new_password }) => {
    setError(null);
    try {
      await authApi.passwordResetConfirm(token, new_password);
      setDone(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  });

  return (
    <AuthLayout
      title="Set a new password"
      subtitle="Choose a passphrase you can remember. We can't recover this for you."
      footer={
        <Link to="/login" className="text-brand-cyan hover:underline underline-offset-4">
          Back to sign in
        </Link>
      }
    >
      {done ? (
        <Alert tone="success" title="Password updated">
          Redirecting you to sign in…
        </Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          {!tokenFromUrl ? (
            <Field label="Reset token" htmlFor="token" error={errors.token?.message}>
              <Input id="token" invalid={Boolean(errors.token)} {...register("token")} />
            </Field>
          ) : (
            <input type="hidden" {...register("token")} />
          )}
          <Field
            label="New password"
            htmlFor="new_password"
            error={errors.new_password?.message}
            hint="At least 10 characters."
          >
            <Input
              id="new_password"
              type="password"
              autoComplete="new-password"
              invalid={Boolean(errors.new_password)}
              {...register("new_password")}
            />
          </Field>
          <Field
            label="Confirm password"
            htmlFor="confirm_password"
            error={errors.confirm_password?.message}
          >
            <Input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              invalid={Boolean(errors.confirm_password)}
              {...register("confirm_password")}
            />
          </Field>
          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            Update password
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
