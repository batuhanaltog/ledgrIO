import { useState } from "react";

export function useOpenClose() {
  const [isOpen, setIsOpen] = useState(false);
  return { isOpen, open: () => setIsOpen(true), close: () => setIsOpen(false) };
}

export function useEditModal<T>() {
  const [selected, setSelected] = useState<T | null>(null);
  return { selected, open: (item: T) => setSelected(item), close: () => setSelected(null) };
}

export function useDeleteConfirm<T = number>() {
  const [pendingId, setPendingId] = useState<T | null>(null);
  return { pendingId, confirm: (id: T) => setPendingId(id), cancel: () => setPendingId(null) };
}
