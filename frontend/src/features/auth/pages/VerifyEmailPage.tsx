import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AuthLayout } from "../components/AuthLayout";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { authApi } from "../api";
import { parseApiError } from "@/lib/errors";

type State =
  | { kind: "loading" }
  | { kind: "success"; email: string }
  | { kind: "error"; message: string }
  | { kind: "missing" };

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState<State>(token ? { kind: "loading" } : { kind: "missing" });

  useEffect(() => {
    if (!token) return;
    authApi
      .verifyEmail(token)
      .then((r) => setState({ kind: "success", email: r.email }))
      .catch((err) =>
        setState({ kind: "error", message: parseApiError(err).message }),
      );
  }, [token]);

  return (
    <AuthLayout
      title="Verify your email"
      footer={
        <Link to="/login" className="text-brand-cyan hover:underline underline-offset-4">
          Back to sign in
        </Link>
      }
    >
      {state.kind === "loading" && (
        <div className="flex items-center gap-3 text-ink-muted">
          <Spinner /> Verifying…
        </div>
      )}
      {state.kind === "success" && (
        <Alert tone="success" title="Email verified">
          {state.email} is confirmed. You can now sign in.
        </Alert>
      )}
      {state.kind === "error" && <Alert tone="danger">{state.message}</Alert>}
      {state.kind === "missing" && (
        <Alert tone="warn">No verification token in the URL.</Alert>
      )}
    </AuthLayout>
  );
}
