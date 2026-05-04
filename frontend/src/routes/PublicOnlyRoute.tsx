import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export function PublicOnlyRoute() {
  const access = useAuthStore((s) => s.access);
  if (access) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
