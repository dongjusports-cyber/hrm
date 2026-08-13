import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { fetchEmployees } from "../../shared/api";
import { isEmployeeRouteUuid } from "../../shared/employeeRouteId";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";
import { type HrNavState } from "../../shared/hrNavState";
import { EmployeeProfileSheet } from "./EmployeeProfileSheet";

/** Route hồ sơ NV — deep link; UX chính là overlay từ danh sách. */
export function EmployeeDetailPage() {
  const { empId } = useParams();
  const isNew = empId === "new";
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolvingMsnv, setResolvingMsnv] = useState(false);
  const tabParam = searchParams.get("tab");
  const initialExtraTab =
    tabParam === "violations" || tabParam === "documents" || tabParam === "experience"
      ? tabParam
      : null;
  const listBack =
    (location.state as HrNavState | null)?.hrListBack ??
    (isNew ? "/m/hr" : "/m/hr/lists/active");

  useHrSubpageEsc({ backTo: listBack });

  useEffect(() => {
    if (isNew) {
      navigate("/m/hr", { replace: true, state: { openCreate: true } });
    }
  }, [isNew, navigate]);

  useEffect(() => {
    if (!empId || isNew || isEmployeeRouteUuid(empId)) {
      setResolveError(null);
      setResolvingMsnv(false);
      return;
    }

    let cancelled = false;
    setResolvingMsnv(true);
    setResolveError(null);

    void fetchEmployees({ q: empId })
      .then((list) => {
        if (cancelled) return;
        const match = list.find((e) => e.employee_code === empId);
        if (!match) {
          setResolveError(`Không tìm thấy nhân viên MSNV ${empId}.`);
          setResolvingMsnv(false);
          return;
        }
        const qs = searchParams.toString();
        const suffix = qs ? `?${qs}` : "";
        navigate(`/m/hr/employees/${match.id}${suffix}`, {
          replace: true,
          state: location.state,
        });
      })
      .catch((e) => {
        if (!cancelled) {
          setResolveError(String(e));
          setResolvingMsnv(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [empId, isNew, location.state, navigate, searchParams]);

  if (isNew || !empId) {
    return null;
  }

  if (resolveError) {
    return <p className="module-placeholder">{resolveError}</p>;
  }

  if (resolvingMsnv || !isEmployeeRouteUuid(empId)) {
    return <p className="module-placeholder">Đang mở hồ sơ MSNV {empId}…</p>;
  }

  return (
    <EmployeeProfileSheet
      employeeId={empId}
      open
      initialExtraTab={initialExtraTab}
      onClose={() => navigate(listBack)}
    />
  );
}
