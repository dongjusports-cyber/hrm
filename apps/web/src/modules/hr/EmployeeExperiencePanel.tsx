import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  createEmployeeEducation,
  createEmployeeExperience,
  createEmployeeHealthCheck,
  deleteEmployeeEducation,
  deleteEmployeeExperience,
  deleteEmployeeHealthCheck,
  fetchEmployeeEducations,
  fetchEmployeeExperiences,
  fetchEmployeeHealthChecks,
  type EmployeeEducation,
  type EmployeeExperience,
  type EmployeeHealthCheck,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { LookupSelect } from "../../shared/LookupSelect";

type Props = {
  empId: string;
};

/** Tab Kinh nghiệm — 3 bảng con CRUD (5.1). */
export function EmployeeExperiencePanel({ empId }: Props) {
  const [educations, setEducations] = useState<EmployeeEducation[]>([]);
  const [experiences, setExperiences] = useState<EmployeeExperience[]>([]);
  const [healthChecks, setHealthChecks] = useState<EmployeeHealthCheck[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [eduSchool, setEduSchool] = useState("");
  const [eduMajor, setEduMajor] = useState("");
  const [eduDegree, setEduDegree] = useState("");
  const [eduFrom, setEduFrom] = useState("");
  const [eduTo, setEduTo] = useState("");

  const [expCompany, setExpCompany] = useState("");
  const [expTitle, setExpTitle] = useState("");
  const [expFrom, setExpFrom] = useState("");
  const [expTo, setExpTo] = useState("");

  const [hcDate, setHcDate] = useState("");
  const [hcFacility, setHcFacility] = useState("");
  const [hcResult, setHcResult] = useState("");

  const reload = useCallback(async () => {
    const [e, x, h] = await Promise.all([
      fetchEmployeeEducations(empId),
      fetchEmployeeExperiences(empId),
      fetchEmployeeHealthChecks(empId),
    ]);
    setEducations(e);
    setExperiences(x);
    setHealthChecks(h);
  }, [empId]);

  useEffect(() => {
    void reload().catch((err) =>
      setError(err instanceof Error ? err.message : "Không tải được kinh nghiệm."),
    );
  }, [reload]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Thao tác thất bại.");
    } finally {
      setBusy(false);
    }
  }

  async function onAddEducation(e: FormEvent) {
    e.preventDefault();
    if (!eduSchool.trim()) return;
    await run(async () => {
      await createEmployeeEducation(empId, {
        school_name: eduSchool.trim(),
        major: eduMajor.trim() || null,
        degree_code: eduDegree || null,
        from_date: eduFrom || null,
        to_date: eduTo || null,
      });
      setEduSchool("");
      setEduMajor("");
      setEduDegree("");
      setEduFrom("");
      setEduTo("");
    });
  }

  async function onAddExperience(e: FormEvent) {
    e.preventDefault();
    if (!expCompany.trim()) return;
    await run(async () => {
      await createEmployeeExperience(empId, {
        company_name: expCompany.trim(),
        position_title: expTitle.trim() || null,
        from_date: expFrom || null,
        to_date: expTo || null,
      });
      setExpCompany("");
      setExpTitle("");
      setExpFrom("");
      setExpTo("");
    });
  }

  async function onAddHealthCheck(e: FormEvent) {
    e.preventDefault();
    if (!hcDate) return;
    await run(async () => {
      await createEmployeeHealthCheck(empId, {
        check_date: hcDate,
        facility_name: hcFacility.trim() || null,
        result_summary: hcResult.trim() || null,
      });
      setHcDate("");
      setHcFacility("");
      setHcResult("");
    });
  }

  return (
    <div className="emp-exp-panel">
      {error && <p className="banner-warn">{error}</p>}

      <section className="emp-exp-section">
        <h3>Quá trình đào tạo</h3>
        <ul className="dept-list emp-panel-list">
          {educations.length === 0 && <li className="module-placeholder">Chưa có bản ghi.</li>}
          {educations.map((row) => (
            <li key={row.id}>
              <strong>{row.school_name}</strong>
              <span className="field-hint">
                {row.major ? `${row.major} · ` : ""}
                {formatDateDDMMYYYY(row.from_date)} – {formatDateDDMMYYYY(row.to_date) || "nay"}
              </span>
              <button
                type="button"
                className="link-btn danger"
                disabled={busy}
                onClick={() => void run(() => deleteEmployeeEducation(empId, row.id))}
              >
                Xóa
              </button>
            </li>
          ))}
        </ul>
        <form className="emp-fields-grid emp-exp-form" onSubmit={(e) => void onAddEducation(e)}>
          <label className="field emp-field-wide">
            <span>Trường *</span>
            <input value={eduSchool} onChange={(e) => setEduSchool(e.target.value)} required />
          </label>
          <label className="field">
            <span>Chuyên ngành</span>
            <input value={eduMajor} onChange={(e) => setEduMajor(e.target.value)} />
          </label>
          <LookupSelect
            groupCode="education_level"
            label="Bằng cấp"
            value={eduDegree}
            onChange={setEduDegree}
          />
          <label className="field">
            <span>Từ</span>
            <input type="date" value={eduFrom} onChange={(e) => setEduFrom(e.target.value)} />
          </label>
          <label className="field">
            <span>Đến</span>
            <input type="date" value={eduTo} onChange={(e) => setEduTo(e.target.value)} />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Thêm đào tạo
          </button>
        </form>
      </section>

      <section className="emp-exp-section">
        <h3>Kinh nghiệm làm việc</h3>
        <ul className="dept-list emp-panel-list">
          {experiences.length === 0 && <li className="module-placeholder">Chưa có bản ghi.</li>}
          {experiences.map((row) => (
            <li key={row.id}>
              <strong>{row.company_name}</strong>
              <span className="field-hint">
                {row.position_title ? `${row.position_title} · ` : ""}
                {formatDateDDMMYYYY(row.from_date)} – {formatDateDDMMYYYY(row.to_date) || "nay"}
              </span>
              <button
                type="button"
                className="link-btn danger"
                disabled={busy}
                onClick={() => void run(() => deleteEmployeeExperience(empId, row.id))}
              >
                Xóa
              </button>
            </li>
          ))}
        </ul>
        <form className="emp-fields-grid emp-exp-form" onSubmit={(e) => void onAddExperience(e)}>
          <label className="field emp-field-wide">
            <span>Công ty *</span>
            <input value={expCompany} onChange={(e) => setExpCompany(e.target.value)} required />
          </label>
          <label className="field">
            <span>Chức vụ</span>
            <input value={expTitle} onChange={(e) => setExpTitle(e.target.value)} />
          </label>
          <label className="field">
            <span>Từ</span>
            <input type="date" value={expFrom} onChange={(e) => setExpFrom(e.target.value)} />
          </label>
          <label className="field">
            <span>Đến</span>
            <input type="date" value={expTo} onChange={(e) => setExpTo(e.target.value)} />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Thêm kinh nghiệm
          </button>
        </form>
      </section>

      <section className="emp-exp-section">
        <h3>Khám sức khỏe</h3>
        <ul className="dept-list emp-panel-list">
          {healthChecks.length === 0 && <li className="module-placeholder">Chưa có bản ghi.</li>}
          {healthChecks.map((row) => (
            <li key={row.id}>
              <strong>{formatDateDDMMYYYY(row.check_date)}</strong>
              <span className="field-hint">
                {row.facility_name || "—"}
                {row.result_summary ? ` · ${row.result_summary}` : ""}
              </span>
              <button
                type="button"
                className="link-btn danger"
                disabled={busy}
                onClick={() => void run(() => deleteEmployeeHealthCheck(empId, row.id))}
              >
                Xóa
              </button>
            </li>
          ))}
        </ul>
        <form className="emp-fields-grid emp-exp-form" onSubmit={(e) => void onAddHealthCheck(e)}>
          <label className="field">
            <span>Ngày khám *</span>
            <input type="date" value={hcDate} onChange={(e) => setHcDate(e.target.value)} required />
          </label>
          <label className="field">
            <span>Cơ sở</span>
            <input value={hcFacility} onChange={(e) => setHcFacility(e.target.value)} />
          </label>
          <label className="field">
            <span>Kết quả</span>
            <input value={hcResult} onChange={(e) => setHcResult(e.target.value)} />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Thêm khám SK
          </button>
        </form>
      </section>
    </div>
  );
}
