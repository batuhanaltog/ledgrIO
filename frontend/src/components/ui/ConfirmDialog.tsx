import { Modal } from "./Modal";
import { Button } from "./Button";
import { Spinner } from "./Spinner";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  message?: string;
}

export function ConfirmDialog({
  open, onClose, onConfirm, loading,
  message = "Bu kaydı silmek istediğine emin misin?",
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} title="Emin misin?" size="sm">
      <p className="text-sm text-ink mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onClose} disabled={loading}>İptal</Button>
        <Button variant="danger" onClick={onConfirm} disabled={loading}>
          {loading ? <Spinner /> : null} Sil
        </Button>
      </div>
    </Modal>
  );
}
