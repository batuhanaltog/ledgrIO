import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { AuthLayout } from "../components/AuthLayout";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { registerSchema, type RegisterInput } from "../schemas";
import { useRegister } from "../hooks";
import { useApiErrorToForm } from "../useFormErrorMapping";

export function RegisterPage() {
  const [topError, setTopError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const {
    register: rhf,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "", default_currency_code: "USD" },
  });

  const apiToForm = useApiErrorToForm(setError);
  const reg = useRegister();

  const onSubmit = handleSubmit(async (values) => {
    setTopError(null);
    try {
      const user = await reg.mutateAsync(values);
      setDone(user.email);
    } catch (err) {
      const { fallback } = apiToForm(err);
      if (fallback) setTopError(fallback);
    }
  });

  if (done) {
    return (
      <AuthLayout
        title="Check your email"
        subtitle="We've sent a verification link to confirm your address."
        footer={
          <p>
            Already verified?{" "}
            <Link to="/login" className="text-brand-cyan hover:underline underline-offset-4">
              Sign in
            </Link>
          </p>
        }
      >
        <Alert tone="success" title="Account created">
          A verification link was sent to <span className="font-medium">{done}</span>.
          In development the link is printed to the backend console.
        </Alert>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create your Ledgr.io account"
      subtitle="One household, one ledger. Free, self-hosted, yours."
      footer={
        <p>
          Already have an account?{" "}
          <Link to="/login" className="text-brand-cyan hover:underline underline-offset-4">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {topError ? <Alert tone="danger">{topError}</Alert> : null}

        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            invalid={Boolean(errors.email)}
            {...rhf("email")}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password?.message}
          hint="At least 10 characters. Use a passphrase you can remember."
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            invalid={Boolean(errors.password)}
            {...rhf("password")}
          />
        </Field>

        <Field
          label="Base currency"
          htmlFor="default_currency_code"
          error={errors.default_currency_code?.message}
          hint="All transactions are converted to this for budgets."
        >
          <Select
            id="default_currency_code"
            invalid={Boolean(errors.default_currency_code)}
            {...rhf("default_currency_code")}
          >
            <option value="EUR">EUR — Euro</option>
            <option value="TRY">TRY — Turkish Lira</option>
            <option value="USD">USD — US Dollar</option>
          </Select>
        </Field>

        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? <Spinner /> : null}
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
