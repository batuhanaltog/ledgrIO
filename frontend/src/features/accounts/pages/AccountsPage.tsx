import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useAccounts, useDeleteAccount } from "../hooks";
import { AccountModal } from "../components/AccountModal";
import type { Account } from "../api";

function fmt(v: string) {
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function AccountsPage() {
  const { data, isPending, isError } = useAccounts();
  const createModal = useOpenClose();
  const editModal = useEditModal<Account>();
  const deleteConfirm = useDeleteConfirm();
  const deleteAccount = useDeleteAccount();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError) return <Alert tone="danger">Hesaplar yüklenemedi.</Alert>;

  const handleDelete = async () => {
    if (deleteConfirm.pendingId === null) return;
    setDeleteError(null);
    try {
      await deleteAccount.mutateAsync(deleteConfirm.pendingId);
      deleteConfirm.cancel();
    } catch {
      setDeleteError("Hesap silinemedi. İşlem içeren hesaplar silinemez.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Accounts</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} account{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Account</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No accounts yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Name", "Type", "Currency", "Balance", "Transactions", ""].map((h) => (
                  <th key={h} className={`px-4 py-3 text-left font-medium ${h === "Balance" || h === "Transactions" ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((acc) => (
                <tr key={acc.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 font-medium text-ink">{acc.name}</td>
                  <td className="px-4 py-3 text-ink-muted capitalize">{acc.account_type.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-ink-muted">{acc.currency_code}</td>
                  <td className="px-4 py-3 text-right num font-medium text-ink">{fmt(acc.current_balance)}</td>
                  <td className="px-4 py-3 text-right text-ink-muted">{acc.transaction_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => editModal.open(acc)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(acc.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && <AccountModal account={null} onClose={createModal.close} />}
      {editModal.selected && <AccountModal account={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={() => { setDeleteError(null); deleteConfirm.cancel(); }}
        onConfirm={handleDelete}
        loading={deleteAccount.isPending}
        error={deleteError}
      />
    </div>
  );
}
