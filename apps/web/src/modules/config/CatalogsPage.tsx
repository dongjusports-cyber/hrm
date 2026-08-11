import { FormEvent, useEffect, useState } from "react";
import {
  createCatalogLeaveType,
  createCatalogLookupValue,
  createCatalogPayComponent,
  fetchCatalogLeaveTypes,
  fetchCatalogLookupValues,
  fetchCatalogPayComponents,
  fetchCatalogWorkShifts,
  fetchOrgTeams,
  fetchTeamShiftSchedules,
  patchTeamDefaultShift,
  updateCatalogLeaveType,
  upsertTeamShiftSchedule,
  type CatalogLeaveType,
  type CatalogPayComponent,
  type LookupValueRow,
  type OrgTeam,
  type TeamShiftScheduleRow,
  type WorkShiftRow,
} from "../../shared/api";
import { ConfigTabNav } from "./ConfigTabNav";

type Tab = "leave" | "pay" | "lookup" | "shift";

export function CatalogsPage() {
  const [tab, setTab] = useState<Tab>("leave");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const [leaveRows, setLeaveRows] = useState<CatalogLeaveType[]>([]);
  const [payRows, setPayRows] = useState<CatalogPayComponent[]>([]);
  const [lookupRows, setLookupRows] = useState<LookupValueRow[]>([]);
  const [lookupGroup, setLookupGroup] = useState("ethnicity");

  const [leaveCode, setLeaveCode] = useState("");
  const [leaveName, setLeaveName] = useState("");
  const [payCode, setPayCode] = useState("");
  const [payName, setPayName] = useState("");
  const [lkCode, setLkCode] = useState("");
  const [lkName, setLkName] = useState("");

  const [shiftRows, setShiftRows] = useState<WorkShiftRow[]>([]);
  const [orgTeams, setOrgTeams] = useState<OrgTeam[]>([]);
  const [overrideTeamId, setOverrideTeamId] = useState("");
  const [overrideDate, setOverrideDate] = useState("");
  const [overrideShiftId, setOverrideShiftId] = useState("ADMIN");
  const [overrideNote, setOverrideNote] = useState("");
  const [scheduleRows, setScheduleRows] = useState<TeamShiftScheduleRow[]>([]);

  async function reloadLeave() {
    setLeaveRows(await fetchCatalogLeaveTypes());
  }
  async function reloadPay() {
    setPayRows(await fetchCatalogPayComponents());
  }
  async function reloadLookup() {
    setLookupRows(await fetchCatalogLookupValues(lookupGroup || undefined));
  }
  async function reloadShift() {
    const [shifts, teams] = await Promise.all([fetchCatalogWorkShifts(), fetchOrgTeams()]);
    setShiftRows(shifts);
    setOrgTeams(teams);
    if (!overrideTeamId && teams[0]) setOverrideTeamId(teams[0].id);
  }
  async function reloadSchedules() {
    if (!overrideTeamId) {
      setScheduleRows([]);
      return;
    }
    const from = overrideDate || undefined;
    setScheduleRows(
      await fetchTeamShiftSchedules({
        team_id: overrideTeamId,
        date_from: from,
        date_to: from,
      }),
    );
  }

  useEffect(() => {
    void reloadLeave().catch((e: unknown) =>
      setError(e instanceof Error ? e.message : "Lỗi tải loại nghỉ."),
    );
    void reloadPay().catch(() => undefined);
    void reloadShift().catch(() => undefined);
  }, []);

  useEffect(() => {
    void reloadLookup().catch((e: unknown) =>
      setError(e instanceof Error ? e.message : "Lỗi tải lookup."),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lookupGroup]);

  useEffect(() => {
    if (tab !== "shift") return;
    void reloadSchedules().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, overrideTeamId, overrideDate]);

  async function onTeamDefaultShift(team: OrgTeam, shiftCode: string) {
    setError(null);
    setOk(null);
    try {
      await patchTeamDefaultShift(team.id, shiftCode);
      setOk(`Tổ ${team.code} → ca mặc định ${shiftCode}.`);
      await reloadShift();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được ca mặc định.");
    }
  }

  async function onOverrideShift(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      await upsertTeamShiftSchedule({
        team_id: overrideTeamId,
        work_date: overrideDate,
        work_shift_id: overrideShiftId,
        note: overrideNote,
      });
      setOk("Đã xếp ca override cho ngày đã chọn.");
      setOverrideNote("");
      await reloadSchedules();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được xếp ca.");
    }
  }

  async function onAddLeave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      await createCatalogLeaveType({
        code: leaveCode,
        name: leaveName,
        paid_by_company: true,
        pay_ratio_percent: 100,
      });
      setOk(`Đã thêm loại nghỉ ${leaveCode.toUpperCase()} — hiện ngay ở Chấm công.`);
      setLeaveCode("");
      setLeaveName("");
      await reloadLeave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    }
  }

  async function onAddPay(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      await createCatalogPayComponent({ code: payCode, name: payName });
      setOk(`Đã thêm khoản ${payCode.toUpperCase()}.`);
      setPayCode("");
      setPayName("");
      await reloadPay();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    }
  }

  async function onAddLookup(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      await createCatalogLookupValue({
        group_code: lookupGroup,
        code: lkCode,
        name: lkName,
      });
      setOk("Đã thêm dòng lookup.");
      setLkCode("");
      setLkName("");
      await reloadLookup();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    }
  }

  async function toggleLeaveName(row: CatalogLeaveType) {
    const name = window.prompt("Tên hiển thị mới:", row.name);
    if (!name?.trim()) return;
    await updateCatalogLeaveType(row.code, { name: name.trim() });
    await reloadLeave();
    setOk(`Đã đổi tên ${row.code}.`);
  }

  return (
    <div className="config-section-page">
      <ConfigTabNav />
      <h1>Danh mục</h1>
      <p className="field-hint">
        Loại nghỉ · Khoản lương · Lookup hồ sơ · Ca làm việc — chỉ Admin. Mã nghỉ mới xuất hiện ngay
        trong ô chọn Chấm công.
      </p>

      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <div className="dispute-filters" role="tablist" aria-label="Danh mục">
        {(
          [
            ["leave", "Loại nghỉ"],
            ["pay", "Khoản lương"],
            ["lookup", "Lookup hồ sơ"],
            ["shift", "Ca làm việc"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? "filter-chip is-active" : "filter-chip"}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "leave" && (
        <div className="hr-split">
          <form className="users-form-card" onSubmit={onAddLeave}>
            <h2>Thêm loại nghỉ</h2>
            <label className="field">
              Mã
              <input value={leaveCode} onChange={(e) => setLeaveCode(e.target.value)} required />
            </label>
            <label className="field">
              Tên
              <input value={leaveName} onChange={(e) => setLeaveName(e.target.value)} required />
            </label>
            <button type="submit" className="btn-primary">
              Thêm
            </button>
          </form>
          <div>
            <h2>Đang có ({leaveRows.length})</h2>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Mã</th>
                  <th>Tên</th>
                  <th>% lương</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {leaveRows.map((r) => (
                  <tr key={r.code}>
                    <td>
                      <strong>{r.code}</strong>
                    </td>
                    <td>{r.name}</td>
                    <td>{r.pay_ratio_percent ?? "—"}</td>
                    <td>
                      <button type="button" className="btn-link" onClick={() => void toggleLeaveName(r)}>
                        Sửa tên
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "pay" && (
        <div className="hr-split">
          <form className="users-form-card" onSubmit={onAddPay}>
            <h2>Thêm khoản lương</h2>
            <label className="field">
              Mã
              <input value={payCode} onChange={(e) => setPayCode(e.target.value)} required />
            </label>
            <label className="field">
              Tên
              <input value={payName} onChange={(e) => setPayName(e.target.value)} required />
            </label>
            <button type="submit" className="btn-primary">
              Thêm
            </button>
          </form>
          <div>
            <h2>Catalog ({payRows.length})</h2>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Mã</th>
                  <th>Tên</th>
                  <th>Mặc định</th>
                </tr>
              </thead>
              <tbody>
                {payRows.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.code}</strong>
                    </td>
                    <td>{r.name}</td>
                    <td>{r.default_amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "lookup" && (
        <div className="hr-split">
          <form className="users-form-card" onSubmit={onAddLookup}>
            <h2>Thêm lookup</h2>
            <label className="field">
              Nhóm (group_code)
              <input value={lookupGroup} onChange={(e) => setLookupGroup(e.target.value)} required />
            </label>
            <label className="field">
              Mã
              <input value={lkCode} onChange={(e) => setLkCode(e.target.value)} required />
            </label>
            <label className="field">
              Tên
              <input value={lkName} onChange={(e) => setLkName(e.target.value)} required />
            </label>
            <button type="submit" className="btn-primary">
              Thêm
            </button>
          </form>
          <div>
            <h2>
              Nhóm <code>{lookupGroup}</code> ({lookupRows.length})
            </h2>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Mã</th>
                  <th>Tên</th>
                </tr>
              </thead>
              <tbody>
                {lookupRows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.code}</td>
                    <td>{r.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "shift" && (
        <div className="hr-split">
          <div>
            <h2>Ca làm việc ({shiftRows.length})</h2>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Mã</th>
                  <th>Tên</th>
                  <th>Giờ</th>
                  <th>Công chuẩn</th>
                </tr>
              </thead>
              <tbody>
                {shiftRows.map((r) => (
                  <tr key={r.code}>
                    <td>
                      <strong>{r.code}</strong>
                    </td>
                    <td>{r.name}</td>
                    <td>
                      {r.start_time?.slice(0, 5)} – {r.end_time?.slice(0, 5)}
                    </td>
                    <td>{r.standard_hours}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h2 style={{ marginTop: "1.5rem" }}>Ca mặc định theo tổ</h2>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Tổ</th>
                  <th>Bộ phận</th>
                  <th>Ca mặc định</th>
                </tr>
              </thead>
              <tbody>
                {orgTeams.slice(0, 40).map((t) => (
                  <tr key={t.id}>
                    <td>{t.code}</td>
                    <td>{t.department_code}</td>
                    <td>
                      <select
                        value={t.default_shift_id ?? ""}
                        onChange={(e) => void onTeamDefaultShift(t, e.target.value)}
                      >
                        <option value="">—</option>
                        {shiftRows.map((s) => (
                          <option key={s.code} value={s.code}>
                            {s.code}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {orgTeams.length > 40 && (
              <p className="field-hint">Hiển thị 40 tổ đầu — dùng API nếu cần xem hết.</p>
            )}
          </div>

          <form className="users-form-card" onSubmit={onOverrideShift}>
            <h2>Xếp ca một ngày</h2>
            <p className="field-hint">Override ca mặc định cho một tổ tại một ngày cụ thể.</p>
            <label className="field">
              Tổ
              <select
                value={overrideTeamId}
                onChange={(e) => setOverrideTeamId(e.target.value)}
                required
              >
                {orgTeams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.code} ({t.department_code})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Ngày
              <input
                type="date"
                value={overrideDate}
                onChange={(e) => setOverrideDate(e.target.value)}
                required
              />
            </label>
            <label className="field">
              Ca
              <select
                value={overrideShiftId}
                onChange={(e) => setOverrideShiftId(e.target.value)}
                required
              >
                {shiftRows.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.code} — {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Ghi chú
              <input value={overrideNote} onChange={(e) => setOverrideNote(e.target.value)} />
            </label>
            <button type="submit" className="btn-primary">
              Lưu xếp ca
            </button>
            {scheduleRows.length > 0 && (
              <p className="field-hint">
                Override ngày đã chọn: {scheduleRows[0].work_shift_id}
                {scheduleRows[0].note ? ` — ${scheduleRows[0].note}` : ""}
              </p>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
