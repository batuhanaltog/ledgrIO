import { useState } from "react";
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
import { useCategories, useDeleteCategory } from "../hooks";
import { CategoryModal } from "../components/CategoryModal";
import type { Category } from "../api";

export function CategoriesPage() {
  const { data, isPending, isError } = useCategories();
  const createModal = useOpenClose();
  const editModal = useEditModal<Category>();
  const deleteConfirm = useDeleteConfirm();
  const deleteCategory = useDeleteCategory();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (isPending)
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  if (isError || !data)
    return <Alert tone="danger">Kategoriler yüklenemedi.</Alert>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Categories</h1>
          <p className="text-sm text-ink-muted mt-1">{data.count} categories</p>
        </div>
        <Button onClick={createModal.open}>
          <Plus className="h-4 w-4" /> Add Category
        </Button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-ink-muted">No categories yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-ink-muted">
              <tr>
                {["Icon", "Name", "Color", "Type", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {data.results.map((cat) => (
                <tr key={cat.id} className="hover:bg-surface-2/50">
                  <td className="px-4 py-3 text-xl">{cat.icon || "—"}</td>
                  <td className="px-4 py-3 font-medium text-ink">{cat.name}</td>
                  <td className="px-4 py-3">
                    {cat.color ? (
                      <span className="inline-flex items-center gap-2">
                        <span
                          className="w-4 h-4 rounded-full border border-hairline"
                          style={{ background: cat.color }}
                        />
                        <span className="text-ink-muted text-xs">
                          {cat.color}
                        </span>
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-muted capitalize">{cat.category_type ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => editModal.open(cat)}
                        aria-label="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteConfirm.confirm(cat.id)}
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
        <CategoryModal category={null} onClose={createModal.close} />
      )}
      {editModal.selected && (
        <CategoryModal
          category={editModal.selected}
          onClose={editModal.close}
        />
      )}
      <ConfirmDialog
        open={deleteConfirm.pendingId !== null}
        onClose={() => { setDeleteError(null); deleteConfirm.cancel(); }}
        onConfirm={async () => {
          if (deleteConfirm.pendingId !== null) {
            try {
              await deleteCategory.mutateAsync(deleteConfirm.pendingId);
              deleteConfirm.cancel();
            } catch {
              setDeleteError("Could not delete category. Please try again.");
            }
          }
        }}
        loading={deleteCategory.isPending}
        error={deleteError}
      />
    </div>
  );
}
