// frontend/src/components/ui/Modal.tsx
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

const SIZES = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" } as const;

const FOCUSABLE = [
  "a[href]", "button:not([disabled])", "input:not([disabled])",
  "select:not([disabled])", "textarea:not([disabled])", "[tabindex]:not([tabindex='-1'])",
].join(", ");

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  size?: keyof typeof SIZES;
}

export function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // ESC key to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Focus trap + scroll lock
  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    const first = containerRef.current?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal aria-labelledby="modal-title">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        ref={containerRef}
        className={cn("relative w-full bg-surface rounded-xl shadow-xl border border-hairline", SIZES[size])}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-hairline">
          <h2 id="modal-title" className="text-base font-semibold text-ink">{title}</h2>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="px-6 py-5 overflow-y-auto max-h-[calc(100vh-10rem)]">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
