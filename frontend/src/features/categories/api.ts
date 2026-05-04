import { api } from "@/lib/api";

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  is_system: boolean;
  owner_id: number | null;
  parent_id: number | null;
  ordering: number;
  created_at: string;
}

export interface PaginatedCategories {
  results: Category[];
  count: number;
}

export interface CategoryInput {
  name: string;
  category_type: "income" | "expense";
  icon?: string;
  color?: string;
}

export const categoriesApi = {
  list: () => api.get<PaginatedCategories>("/categories/").then((r) => r.data),
  create: (data: CategoryInput) =>
    api.post<Category>("/categories/", data).then((r) => r.data),
  update: (id: number, data: Partial<CategoryInput>) =>
    api.patch<Category>(`/categories/${id}/`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/categories/${id}/`),
};
