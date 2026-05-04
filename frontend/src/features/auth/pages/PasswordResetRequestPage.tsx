import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { AuthLayout } from "../components/AuthLayout";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import {
  passwordResetRequestSchema,
  type PasswordResetRequestInput,
} from "../schemas";
import { authApi } from "../api";
import { parseApiError } from "@/lib/errors";

export function PasswordResetRequestPage() {
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetRequestInput>({
    resolver: zodResolver(passwordResetRequestSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = handleSubmit(async ({ email }) => {
    setError(null);
    try {
      await authApi.passwordResetRequest(email);
      setSubmitted(true);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  });

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter the email associated with your account. We'll send a reset link if it exists."
      footer={
        <Link to="/login" className="text-brand-cyan hover:underline underline-offset-4">
          Back to sign in
        </Link>
      }
    >
      {submitted ? (
        <Alert tone="info" title="Request received">
          If that email is registered, a reset link has been sent. The link expires in
          a short window — check your inbox.
        </Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Field label="Email" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              invalid={Boolean(errors.email)}
              {...register("email")}
            />
          </Field>
          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
