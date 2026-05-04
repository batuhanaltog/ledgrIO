import { useCallback, useMemo, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  useOpenClose,
  useEditModal,
  useDeleteConfirm,
} from "@/hooks/useModalState";
import { useAccounts } from "@/features/accounts/hooks";
import { useTransactions, useDeleteTransaction } from "../hooks";
import { todayMonthRange } from "../utils";
import {
  TransactionFilters,
  type FilterValues,
} from "../components/TransactionFilters";
import { TransactionModal } from "../components/TransactionModal";
import type { Transaction } from "../api";

export function TransactionsPage() {
  const { date_from, date_to } = todayMonthRange();
  const [params, setParams] = useState<Record<string, string>>({
    date_from,
    date_to,
  });
  const { data, isPending, isError } = useTransactions(params);
  const accounts = useAccounts();
  const accountMap = useMemo(() => {
    const map = new Map<number, string>();
    accounts.data?.results.forEach((a) => map.set(a.id, a.name));
    return map;
  }, [accounts.data]);
  const createModal = useOpenClose();
  const editModal = useEditModal<Transaction>();
  const deleteConfirm = useDeleteConfirm();
  const deleteTransaction = useDeleteTransaction();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleFilterChange = useCallback((f: FilterValues) => {
    const p: Record<string, string> = {};
    if (f.date_from) p.date_from = f.date_from;
    if (f.date_to) p.date_to = f.date_to;
    if (f.account_id) p.account_id = f.account_id;
    if (f.category_id) p.category_id = f.category_id;
    if (f.type) p.type = f.type;
    if (f.description) p.description = f.description;
    setParams(p);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Transactions</h1>
          {data && (
            <p className="text-sm text-ink-muted mt-1">
              {data.count} transaction{data.count !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <Button onClick={createModal.open}>
          <Plus className="h-4 w-4" /> Add Transaction
        </Button>
      </div>

      <TransactionFilters onChange={handleFilterChange} />

      {isPending ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : isError ? (
        <Alert tone="danger">İşlemler yüklenemedi.</Alert>
      ) : data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No transactions found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {[
                  "Date",
                  "Description",
                  "Category",
                  "Account",
                  "Type",
                  "Amount",
                  "",
                ].map((h) => (
                  <th
                    key={h}
                    className={`px-4 py-3 text-left font-medium ${h === "Amount" ? "text-right" : ""}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((tx) => (
                <tr key={tx.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 text-ink-muted whitespace-nowrap">
                    {tx.date}
                  </td>
                  <td className="px-4 py-3 text-ink">
                    {tx.description || "—"}
                  </td>
                  <td className="px-4 py-3 text-ink-muted">
                    {tx.category?.name ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{accountMap.get(tx.account_id) ?? tx.account_id}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-semibold uppercase ${tx.type === "income" ? "text-success" : "text-danger"}`}
                    >
                      {tx.type}
                    </span>
                  </td>
                  <td
                    className={`px-4 py-3 text-right num font-medium ${tx.type === "income" ? "text-success" : "text-danger"}`}
                  >
                    {tx.type === "expense" ? "−" : "+"}
                    {Number(tx.amount).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{" "}
                    {tx.currency_code}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => editModal.open(tx)}
                        aria-label="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteConfirm.confirm(tx.id)}
                        aria-label="Delete"
                      >
                        <Trash2 className="h-4 w-4 text-danger" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal.isOpen && (
        <TransactionModal transaction={null} onClose={createModal.close} />
      )}
      {editModal.selected && (
        <TransactionModal
          transaction={editModal.selected}
          onClose={editModal.close}
        />
      )}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={() => { setDeleteError(null); deleteConfirm.cancel(); }}
        onConfirm={async () => {
          if (deleteConfirm.pendingId !== null) {
            try {
              await deleteTransaction.mutateAsync(deleteConfirm.pendingId);
              deleteConfirm.cancel();
            } catch {
              setDeleteError("Could not delete transaction. Please try again.");
            }
          }
        }}
        loading={deleteTransaction.isPending}
        error={deleteError}
      />
    </div>
  );
}
