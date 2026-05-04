import { useState } from "react";

export function useOpenClose() {
  const [isOpen, setIsOpen] = useState(false);
  return { isOpen, open: () => setIsOpen(true), close: () => setIsOpen(false) };
}

export function useEditModal<T>() {
  const [selected, setSelected] = useState<T | null>(null);
  return { selected, open: (item: T) => setSelected(item), close: () => setSelected(null) };
}

export function useDeleteConfirm() {
  const [pendingId, setPendingId] = useState<number | null>(null);
  return { pendingId, confirm: (id: number) => setPendingId(id), cancel: () => setPendingId(null) };
}
