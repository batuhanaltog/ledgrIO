import { type HTMLAttributes } from "react";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/cn";

type Tone = "info" | "success" | "warn" | "danger";

const tones: Record<
  Tone,
  { wrap: string; icon: typeof Info }
> = {
  info: { wrap: "bg-brand-cyan/10 text-brand-navy border-brand-cyan/30", icon: Info },
  success: { wrap: "bg-success/10 text-success border-success/30", icon: CheckCircle2 },
  warn: { wrap: "bg-warn/10 text-warn border-warn/30", icon: TriangleAlert },
  danger: { wrap: "bg-danger/10 text-danger border-danger/30", icon: AlertCircle },
};

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  tone?: Tone;
  title?: string;
}

export function Alert({ tone = "info", title, className, children, ...props }: AlertProps) {
  const { wrap, icon: Icon } = tones[tone];
  return (
    <div
      role="alert"
      className={cn(
        "flex gap-3 rounded-md border px-4 py-3 text-sm",
        wrap,
        className,
      )}
      {...props}
    >
      <Icon className="h-4 w-4 mt-0.5 shrink-0" />
      <div className="flex-1 leading-snug">
        {title ? <p className="font-medium">{title}</p> : null}
        {children ? <div className={title ? "mt-0.5 opacity-90" : ""}>{children}</div> : null}
      </div>
    </div>
  );
}
