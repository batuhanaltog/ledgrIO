import { useMemo } from "react";
import { Plus, Pencil, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useAccounts } from "@/features/accounts/hooks";
import { useRecurring, useDeleteRecurring, useUpdateRecurring } from "../hooks";
import { RecurringModal } from "../components/RecurringModal";
import type { RecurringTemplate } from "../api";

export function RecurringPage() {
  const { data, isPending, isError } = useRecurring();
  const accounts = useAccounts();
  const accountMap = useMemo(() => {
    const map = new Map<number, string>();
    accounts.data?.results.forEach((a) => map.set(a.id, a.name));
    return map;
  }, [accounts.data]);
  const createModal = useOpenClose();
  const editModal = useEditModal<RecurringTemplate>();
  const deleteConfirm = useDeleteConfirm();
  const deleteRecurring = useDeleteRecurring();
  const updateRecurring = useUpdateRecurring();

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError || !data) return <Alert tone="danger">Could not load recurring templates.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Recurring</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} template{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Template</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No recurring templates yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Description", "Account", "Type", "Amount", "Frequency", "Next Due", "Active", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((t) => (
                <tr key={t.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 font-medium text-ink">{t.description}</td>
                  <td className="px-4 py-3 text-ink-muted">{accountMap.get(t.account) ?? t.account}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${t.type === "income" ? "bg-success/15 text-success" : "bg-danger/15 text-danger"}`}>{t.type}</span>
                  </td>
                  <td className="px-4 py-3 num text-ink">{Number(t.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {t.currency_code}</td>
                  <td className="px-4 py-3 text-ink-muted capitalize">{t.frequency}</td>
                  <td className="px-4 py-3 text-ink-muted">{t.next_due_date ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost" size="icon"
                      disabled={updateRecurring.isPending}
                      onClick={() => updateRecurring.mutate({ id: t.id, data: { is_active: !t.is_active } })}
                      aria-label={t.is_active ? "Deactivate" : "Activate"}
                    >
                      {t.is_active ? <ToggleRight className="h-5 w-5 text-success" /> : <ToggleLeft className="h-5 w-5 text-ink-muted" />}
                    </Button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => editModal.open(t)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(t.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && <RecurringModal template={null} onClose={createModal.close} />}
      {editModal.selected && <RecurringModal template={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId !== null) { await deleteRecurring.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteRecurring.isPending}
      />
    </div>
  );
}
