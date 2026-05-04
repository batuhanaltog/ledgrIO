interface LogoProps {
  variant?: "full" | "mark" | "wordmark";
  className?: string;
  title?: string;
  onDark?: boolean;
}

const Mark = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 64 64"
    className={className}
    role="img"
    aria-hidden="true"
    fill="none"
  >
    <defs>
      <linearGradient id="ledgrio-mark-g" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
        <stop offset="0" stopColor="#0F2547" />
        <stop offset="0.55" stopColor="#1B6E8C" />
        <stop offset="1" stopColor="#2FB0DE" />
      </linearGradient>
    </defs>
    <rect x="2" y="2" width="60" height="60" rx="10" fill="url(#ledgrio-mark-g)" />
    <rect x="14" y="38" width="7" height="14" rx="1.5" fill="#E8F4FB" />
    <rect x="25" y="28" width="7" height="24" rx="1.5" fill="#E8F4FB" />
    <rect x="36" y="20" width="7" height="32" rx="1.5" fill="#E8F4FB" />
    <path
      d="M14 26 L26 18 L36 22 L50 12"
      stroke="#2FB0DE"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M46 12 L50 12 L50 16"
      stroke="#2FB0DE"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const Wordmark = ({ className, onDark }: { className?: string; onDark?: boolean }) => (
  <span className={`font-sans font-bold tracking-tight ${className ?? ""}`}>
    <span className={onDark ? "text-white" : "text-ink"}>Ledgr</span>
    <span className="text-brand-cyan">.io</span>
  </span>
);

export function Logo({ variant = "full", className, title = "Ledgr.io", onDark }: LogoProps) {
  if (variant === "mark") {
    return <Mark className={className ?? "h-8 w-8"} />;
  }
  if (variant === "wordmark") {
    return <Wordmark className={className ?? "text-2xl"} onDark={onDark} />;
  }
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`} aria-label={title}>
      <Mark className="h-8 w-8 shrink-0" />
      <Wordmark className="text-2xl leading-none" onDark={onDark} />
    </span>
  );
}
