import { useState } from "react";
import { Plus, Pencil, Trash2, ChevronDown, ChevronRight, CreditCard } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useOpenClose, useEditModal, useDeleteConfirm } from "@/hooks/useModalState";
import { useDebts, useDeleteDebt } from "../hooks";
import { DebtModal } from "../components/DebtModal";
import { PaymentModal } from "../components/PaymentModal";
import type { Debt } from "../api";

interface PaymentTarget { debtId: number; debtName: string; }

export function DebtsPage() {
  const { data, isPending, isError } = useDebts();
  const createModal = useOpenClose();
  const editModal = useEditModal<Debt>();
  const deleteConfirm = useDeleteConfirm();
  const deleteDebt = useDeleteDebt();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [paymentTarget, setPaymentTarget] = useState<PaymentTarget | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (isPending) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (isError || !data) return <Alert tone="danger">Could not load debts.</Alert>;

  const toggle = (id: number) => setExpandedId((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Debts</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} debt{data.count !== 1 ? "s" : ""}</p>
        </div>
        <Button onClick={createModal.open}><Plus className="h-4 w-4" /> Add Debt</Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No debts recorded.</p>
      ) : (
        <div className="space-y-2">
          {data.results.map((debt) => {
            const paidPct = Number(debt.original_amount) > 0
              ? Math.min(100, (1 - Number(debt.current_balance) / Number(debt.original_amount)) * 100)
              : 100;
            const isExpanded = expandedId === debt.id;

            return (
              <div key={debt.id} className="rounded-lg border border-hairline bg-surface overflow-hidden">
                <div
                  className="flex items-center gap-3 px-5 py-4 cursor-pointer hover:bg-surface-2/50"
                  onClick={() => toggle(debt.id)}
                >
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-ink-muted shrink-0" /> : <ChevronRight className="h-4 w-4 text-ink-muted shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-medium text-ink">{debt.name}</p>
                      <div className="flex items-center gap-4 text-sm shrink-0">
                        <span className="text-ink-muted num">
                          {Number(debt.current_balance).toLocaleString(undefined, { maximumFractionDigits: 2 })} / {Number(debt.original_amount).toLocaleString(undefined, { maximumFractionDigits: 2 })} {debt.currency_code}
                        </span>
                        {debt.is_settled && <span className="text-xs px-2 py-0.5 rounded-full bg-success/15 text-success font-medium">Settled</span>}
                      </div>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-surface-2 overflow-hidden">
                      <div className="h-full rounded-full bg-brand-cyan transition-all" style={{ width: `${paidPct}%` }} />
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="icon" onClick={() => editModal.open(debt)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => deleteConfirm.confirm(debt.id)} aria-label="Delete"><Trash2 className="h-4 w-4 text-danger" /></Button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-hairline px-5 py-4 space-y-3 bg-surface-2/30">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                      <div><p className="text-xs text-ink-muted mb-0.5">Monthly Payment</p><p className="font-medium num text-ink">{Number(debt.expected_monthly_payment).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p></div>
                      {debt.interest_rate_pct && <div><p className="text-xs text-ink-muted mb-0.5">Interest</p><p className="font-medium num text-ink">{debt.interest_rate_pct}%</p></div>}
                      {debt.due_day && <div><p className="text-xs text-ink-muted mb-0.5">Due Day</p><p className="font-medium text-ink">Day {debt.due_day}</p></div>}
                      {debt.notes && <div className="col-span-2"><p className="text-xs text-ink-muted mb-0.5">Notes</p><p className="text-ink">{debt.notes}</p></div>}
                    </div>
                    <Button
                      variant="outline" size="sm"
                      onClick={() => setPaymentTarget({ debtId: debt.id, debtName: debt.name })}
                    >
                      <CreditCard className="h-4 w-4" /> Add Payment
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {createModal.isOpen && <DebtModal debt={null} onClose={createModal.close} />}
      {editModal.selected && <DebtModal debt={editModal.selected} onClose={editModal.close} />}
      {paymentTarget && (
        <PaymentModal
          debtId={paymentTarget.debtId}
          debtName={paymentTarget.debtName}
          onClose={() => setPaymentTarget(null)}
        />
      )}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={() => { setDeleteError(null); deleteConfirm.cancel(); }}
        onConfirm={async () => {
          if (deleteConfirm.pendingId !== null) {
            try {
              await deleteDebt.mutateAsync(deleteConfirm.pendingId);
              deleteConfirm.cancel();
            } catch {
              setDeleteError("Could not delete debt. Please try again.");
            }
          }
        }}
        loading={deleteDebt.isPending}
        error={deleteError}
      />
    </div>
  );
}
