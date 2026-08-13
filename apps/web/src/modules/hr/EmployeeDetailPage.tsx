import { useEffect } from "react";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
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

  if (isNew || !empId) {
    return null;
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
