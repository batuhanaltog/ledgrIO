import { useEffect } from "react";
import { useAuthStore } from "@/store/auth.store";

export default function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {isAuthenticated ? (
        <div className="flex items-center justify-center h-screen">
          <p className="text-muted-foreground">Dashboard — coming in Phase 3</p>
        </div>
      ) : (
        <div className="flex items-center justify-center h-screen">
          <p className="text-muted-foreground">Auth pages — coming in Phase 3</p>
        </div>
      )}
    </div>
  );
}
