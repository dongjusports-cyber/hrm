import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../shared/authStore";
import { ModuleLayerHeader } from "../../shared/ModuleLayerHeader";
import { showDenied } from "../../shared/deniedStore";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";

/** Lv2 Cấu Hình — chỉ Admin (file 02). */
export function ConfigLayout() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed = user?.role === "admin";

  useHrSubpageEsc({ backTo: "/m/config" });

  useEffect(() => {
    if (user && !allowed) {
      showDenied(user.full_name);
      navigate("/", { replace: true });
    }
  }, [user, allowed, navigate]);

  if (!allowed) return null;

  return (
    <div className="module-page">
      <ModuleLayerHeader
        layers={[
          { label: "← Portal", to: "/" },
          { label: "Cấu Hình", to: "/m/config" },
        ]}
      />
      <main className="module-body">
        <Outlet />
      </main>
    </div>
  );
}
