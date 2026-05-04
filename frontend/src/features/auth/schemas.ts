import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z.string().min(1, "Password is required."),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z
    .string()
    .min(10, "Password must be at least 10 characters.")
    .max(128, "Password is too long."),
  default_currency_code: z
    .string()
    .length(3, "Currency code must be 3 letters.")
    .regex(/^[A-Z]{3}$/, "Use ISO 4217 (e.g. USD, EUR, TRY)."),
});
export type RegisterInput = z.infer<typeof registerSchema>;

export const passwordResetRequestSchema = z.object({
  email: z.string().email("Enter a valid email."),
});
export type PasswordResetRequestInput = z.infer<typeof passwordResetRequestSchema>;

export const passwordResetConfirmSchema = z
  .object({
    token: z.string().min(1, "Token is required."),
    new_password: z.string().min(10, "Password must be at least 10 characters."),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });
export type PasswordResetConfirmInput = z.infer<typeof passwordResetConfirmSchema>;
