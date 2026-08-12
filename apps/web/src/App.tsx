import { Navigate, Route, Routes } from "react-router-dom";
import { ForceChangePasswordPage } from "./portal/ForceChangePasswordPage";
import { LoginPage } from "./portal/LoginPage";
import { PortalHome } from "./portal/PortalHome";
import { ModuleShell } from "./portal/ModuleShell";
import { ConfigHome } from "./modules/config/ConfigHome";
import { ConfigLayout } from "./modules/config/ConfigLayout";
import { ConfigPlaceholder } from "./modules/config/ConfigPlaceholder";
import { CalendarPage } from "./modules/config/CalendarPage";
import { CatalogsPage } from "./modules/config/CatalogsPage";
import { PolicyEditorPage } from "./modules/config/PolicyEditorPage";
import { PolicyPackagePage } from "./modules/config/PolicyPackagePage";
import { UsersPage } from "./modules/config/UsersPage";
import { AiSettingsPage } from "./modules/config/AiSettingsPage";
import { AuditLogPage } from "./modules/config/AuditLogPage";
import { DepartmentsPage } from "./modules/config/DepartmentsPage";
import { KpiConfigPage } from "./modules/config/KpiConfigPage";
import { OrgAdminPage } from "./modules/config/OrgAdminPage";
import { IntegrationAdminPage } from "./modules/config/IntegrationAdminPage";
import { PermissionsAdminPage } from "./modules/config/PermissionsAdminPage";
import { JournalAdminPage } from "./modules/config/JournalAdminPage";
import { PortalTabsPage } from "./modules/config/PortalTabsPage";
import { EmployeeDetailPage } from "./modules/hr/EmployeeDetailPage";
import { EmployeesPage } from "./modules/hr/EmployeesPage";
import { HrHomePage } from "./modules/hr/HrHomePage";
import { HrLayout } from "./modules/hr/HrLayout";
import { LabourContractsPage } from "./modules/hr/LabourContractsPage";
import { ResignationWizardPage } from "./modules/hr/ResignationWizardPage";
import { EmployeeMovementsPage } from "./modules/hr/EmployeeMovementsPage";
import { SalaryRaisePage } from "./modules/hr/SalaryRaisePage";
import { ViolationsBoardPage } from "./modules/hr/ViolationsBoardPage";
import { WorkerQrPage } from "./modules/hr/WorkerQrPage";
import { TimekeepingPage } from "./modules/timekeeping/TimekeepingPage";
import { PayrollPage } from "./modules/payroll/PayrollPage";
import { DisputePage } from "./modules/dispute/DisputePage";
import { OverviewPage } from "./modules/overview/OverviewPage";
import { ReportPage } from "./modules/report/ReportPage";
import { InsurancePage } from "./modules/insurance/InsurancePage";
import { AiFab } from "./shared/AiFab";
import { CommandPalette } from "./shared/CommandPalette";
import { DeniedModal } from "./shared/DeniedModal";
import { FullscreenToggle } from "./shared/FullscreenToggle";
import { GlobalEscBack } from "./shared/GlobalEscBack";
import { KeyboardHintsBar } from "./shared/KeyboardHintsBar";
import { RequireAuth } from "./shared/RequireAuth";
import { useDeniedStore } from "./shared/deniedStore";
import { RequireWorker } from "./worker/RequireWorker";
import { WorkerAccountPage } from "./worker/WorkerAccountPage";
import { WorkerHomePage } from "./worker/WorkerHomePage";
import { WorkerLeavePage } from "./worker/WorkerLeavePage";
import { WorkerLoginPage } from "./worker/WorkerLoginPage";
import { WorkerPayslipPage } from "./worker/WorkerPayslipPage";

export default function App() {
  const { open, message, close } = useDeniedStore();

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/change-password" element={<ForceChangePasswordPage />} />
        <Route path="/worker/login" element={<WorkerLoginPage />} />
        <Route
          path="/worker"
          element={
            <RequireWorker>
              <WorkerHomePage />
            </RequireWorker>
          }
        />
        <Route
          path="/worker/payslips/:payslipId"
          element={
            <RequireWorker>
              <WorkerPayslipPage />
            </RequireWorker>
          }
        />
        <Route
          path="/worker/leave"
          element={
            <RequireWorker>
              <WorkerLeavePage />
            </RequireWorker>
          }
        />
        <Route
          path="/worker/account"
          element={
            <RequireWorker>
              <WorkerAccountPage />
            </RequireWorker>
          }
        />
        <Route
          path="/"
          element={
            <RequireAuth>
              <PortalHome />
            </RequireAuth>
          }
        />
        <Route
          path="/m/config"
          element={
            <RequireAuth>
              <ConfigLayout />
            </RequireAuth>
          }
        >
          <Route index element={<ConfigHome />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="policy-package" element={<PolicyPackagePage />} />
          <Route path="catalogs" element={<CatalogsPage />} />
          <Route path="payroll-policy" element={<PolicyEditorPage />} />
          <Route
            path="insurance-policy"
            element={<Navigate to="/m/config/policy-package" replace />}
          />
          <Route
            path="attendance-policy"
            element={<Navigate to="/m/config/policy-package" replace />}
          />
          <Route path="portal-tabs" element={<PortalTabsPage />} />
          <Route path="departments" element={<DepartmentsPage />} />
          <Route path="organization" element={<OrgAdminPage />} />
          <Route path="integration" element={<IntegrationAdminPage />} />
          <Route path="permissions" element={<PermissionsAdminPage />} />
          <Route path="journal" element={<JournalAdminPage />} />
          <Route path="kpi" element={<KpiConfigPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="ai" element={<AiSettingsPage />} />
          <Route path="audit-log" element={<AuditLogPage />} />
          <Route path="agent" element={<Navigate to="/m/timekeeping" replace />} />
          <Route path=":sectionKey" element={<ConfigPlaceholder />} />
        </Route>
        <Route
          path="/m/hr"
          element={
            <RequireAuth>
              <HrLayout />
            </RequireAuth>
          }
        >
          <Route index element={<HrHomePage />} />
          <Route path="lists/:filterKey" element={<EmployeesPage />} />
          <Route path="salary-raise" element={<SalaryRaisePage />} />
          <Route path="contracts" element={<LabourContractsPage />} />
          <Route path="family" element={<Navigate to="/m/insurance?tab=tax" replace />} />
          <Route path="movements" element={<EmployeeMovementsPage />} />
          <Route path="resignation" element={<ResignationWizardPage />} />
          <Route path="violations" element={<ViolationsBoardPage />} />
          <Route path="qr-code" element={<WorkerQrPage />} />
          <Route path="employees/new" element={<EmployeeDetailPage />} />
          <Route path="employees/:empId" element={<EmployeeDetailPage />} />
        </Route>
        <Route
          path="/admin/qr-code"
          element={
            <RequireAuth>
              <WorkerQrPage />
            </RequireAuth>
          }
        />
        <Route
          path="/hr/employees"
          element={
            <RequireAuth>
              <EmployeesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/timekeeping"
          element={
            <RequireAuth>
              <TimekeepingPage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/payroll"
          element={
            <RequireAuth>
              <PayrollPage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/dispute"
          element={
            <RequireAuth>
              <DisputePage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/overview"
          element={
            <RequireAuth>
              <OverviewPage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/report"
          element={
            <RequireAuth>
              <ReportPage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/insurance"
          element={
            <RequireAuth>
              <InsurancePage />
            </RequireAuth>
          }
        />
        <Route
          path="/m/:moduleKey/*"
          element={
            <RequireAuth>
              <ModuleShell />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <GlobalEscBack />
      <CommandPalette />
      <KeyboardHintsBar />
      <FullscreenToggle />
      <DeniedModal open={open} message={message} onClose={close} />
      <AiFab />
    </>
  );
}
