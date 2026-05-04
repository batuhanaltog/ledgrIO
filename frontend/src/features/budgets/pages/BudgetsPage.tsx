import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useBudgets, useDeleteBudget } from "../hooks";
import { BudgetModal } from "../components/BudgetModal";
import { cn } from "@/lib/cn";
import type { Budget } from "../api";

function usageColor(pct: number) {
  if (pct >= 100) return "bg-danger";
  if (pct >= 75) return "bg-warn";
  return "bg-success";
}

export function BudgetsPage() {
  const { data, isPending, isError } = useBudgets();
  const createModal = useOpenClose();
  const editModal = useEditModal<Budget>();
  const deleteConfirm = useDeleteConfirm();
  const deleteBudget = useDeleteBudget();

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError || !data) return <Alert tone="danger">Bütçeler yüklenemedi.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Budgets</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} budget{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Budget</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No budgets yet.</p>
      ) : (
        <div className="space-y-3">
          {data.results.map((b) => {
            const pct = b.usage_pct ? Math.min(Number(b.usage_pct) * 100, 100) : 0;
            return (
              <div key={b.id} className="rounded-lg border border-hairline bg-surface p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-ink">{b.name}</p>
                      <p className="text-xs text-ink-muted">{b.date_from} → {b.date_to}</p>
                    </div>
                    {b.category && <p className="text-xs text-ink-muted mb-2">{b.category.name}</p>}
                    <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden mb-2">
                      <div className={cn("h-full rounded-full transition-all", usageColor(pct))} style={{ width: `${pct}%` }} />
                    </div>
                    <div className="flex justify-between text-xs text-ink-muted">
                      <span>{Number(b.spent).toLocaleString(undefined, { maximumFractionDigits: 2 })} spent</span>
                      <span className={Number(b.remaining) < 0 ? "text-danger" : ""}>
                        {Number(b.remaining).toLocaleString(undefined, { maximumFractionDigits: 2 })} remaining · {pct.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => editModal.open(b)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(b.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {createModal.isOpen && <BudgetModal budget={null} onClose={createModal.close} />}
      {editModal.selected && <BudgetModal budget={editModal.selected} onClose={editModal.close} />}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={deleteConfirm.cancel}
        onConfirm={async () => { if (deleteConfirm.pendingId !== null) { await deleteBudget.mutateAsync(deleteConfirm.pendingId); deleteConfirm.cancel(); } }}
        loading={deleteBudget.isPending}
      />
    </div>
  );
}
