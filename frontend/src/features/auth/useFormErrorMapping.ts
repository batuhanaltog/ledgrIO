import { useCallback } from "react";
import type { UseFormSetError, FieldValues, Path } from "react-hook-form";
import { parseApiError } from "@/lib/errors";

export function useApiErrorToForm<T extends FieldValues>(setError: UseFormSetError<T>) {
  return useCallback(
    (err: unknown): { fallback: string | null } => {
      const parsed = parseApiError(err);
      if (parsed.fieldErrors) {
        let mapped = false;
        for (const [field, message] of Object.entries(parsed.fieldErrors)) {
          setError(field as Path<T>, { type: "server", message });
          mapped = true;
        }
        if (mapped) return { fallback: null };
      }
      return { fallback: parsed.message };
    },
    [setError],
  );
}
