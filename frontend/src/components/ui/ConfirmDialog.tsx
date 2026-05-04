import { Modal } from "./Modal";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Spinner } from "./Spinner";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  message?: string;
  error?: string | null;
}

export function ConfirmDialog({
  open, onClose, onConfirm, loading,
  message = "Bu kaydı silmek istediğine emin misin?",
  error,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} title="Emin misin?" size="sm">
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <p className="text-sm text-ink mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onClose} disabled={loading}>İptal</Button>
        <Button variant="danger" onClick={onConfirm} disabled={loading}>
          {loading && <Spinner />}
          Sil
        </Button>
      </div>
    </Modal>
  );
}
