import { useCallback, useEffect, useState } from "react";
import {
  createEmployeeWtRegime,
  endEmployeeWtRegime,
  fetchEmployeeWtRegimes,
  type EmployeeWtRegime,
  type WtRegimeType,
} from "../../shared/api";

const TYPE_LABEL: Record<WtRegimeType, string> = {
  PREGNANT: "Thai sản",
  CHILD: "Nuôi con",
};

// Mặc định gợi ý: Thai sản → 1h, Nuôi con → 2h (HR sửa được).
const DEFAULT_HOURS: Record<WtRegimeType, number> = { PREGNANT: 1, CHILD: 2 };

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

function isActive(r: EmployeeWtRegime): boolean {
  const today = todayIso();
  return r.date_from <= today && today <= r.date_to;
}

type Props = { employeeId: string; embedded?: boolean };

export function WtRegimePanel({ employeeId, embedded = false }: Props) {
  const [rows, setRows] = useState<EmployeeWtRegime[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [regimeType, setRegimeType] = useState<WtRegimeType>("PREGNANT");
  const [hoursEarly, setHoursEarly] = useState(1);
  const [dateFrom, setDateFrom] = useState(todayIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchEmployeeWtRegimes(employeeId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải chế độ về sớm.");
    } finally {
      setLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    void load();
  }, [load]);

  function onChangeType(next: WtRegimeType) {
    setRegimeType(next);
    setHoursEarly(DEFAULT_HOURS[next]);
  }

  async function onAdd() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      await createEmployeeWtRegime(employeeId, {
        regime_type: regimeType,
        hours_early: hoursEarly,
        date_from: dateFrom,
        date_to: dateTo,
        note: note.trim(),
      });
      setNote("");
      setOk("Đã lưu chế độ về sớm. Công đã được tính lại.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không lưu được chế độ về sớm.");
    } finally {
      setBusy(false);
    }
  }

  async function onEnd(id: string) {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      await endEmployeeWtRegime(employeeId, id);
      setOk("Đã chấm dứt chế độ.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không chấm dứt được chế độ.");
    } finally {
      setBusy(false);
    }
  }

  const title = embedded ? (
    <h4 className="emp-allow-block-title">Chế độ về sớm</h4>
  ) : (
    <h3 className="emp-form-section-title">Chế độ về sớm</h3>
  );

  const body = (
    <>
      {error && <p className="form-error">{error}</p>}
      {ok && <p className="form-ok">{ok}</p>}

      <div className="wt-regime-form">
        <label className="field">
          <span>Loại</span>
          <select
            value={regimeType}
            onChange={(e) => onChangeType(e.target.value as WtRegimeType)}
          >
            <option value="PREGNANT">Thai sản</option>
            <option value="CHILD">Nuôi con</option>
          </select>
        </label>
        <label className="field">
          <span>Giờ về sớm</span>
          <select value={hoursEarly} onChange={(e) => setHoursEarly(Number(e.target.value))}>
            <option value={1}>1 giờ</option>
            <option value={2}>2 giờ</option>
            <option value={3}>3 giờ</option>
          </select>
        </label>
        <label className="field">
          <span>Từ ngày</span>
          <input type="date" value={dateFrom} min={todayIso()} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label className="field">
          <span>Đến ngày</span>
          <input type="date" value={dateTo} min={dateFrom} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <label className="field wt-regime-note">
          <span>Ghi chú</span>
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <button type="button" className="btn-primary btn-sm" disabled={busy} onClick={() => void onAdd()}>
          Thêm chế độ
        </button>
      </div>

      {loading ? (
        <p className="field-hint">Đang tải…</p>
      ) : rows.length === 0 ? (
        <p className="field-hint">Chưa có chế độ về sớm.</p>
      ) : (
        <ul className="wt-regime-list">
          {rows.map((r) => (
            <li key={r.id} className={isActive(r) && !r.ended_at ? "wt-regime-active" : "wt-regime-done"}>
              <span className="wt-regime-info">
                {TYPE_LABEL[r.regime_type]} · {r.hours_early}h · {fmtDate(r.date_from)}–{fmtDate(r.date_to)}
                {r.ended_at ? " · đã chấm dứt" : ""}
                {r.note ? ` · ${r.note}` : ""}
              </span>
              {isActive(r) && !r.ended_at && (
                <button
                  type="button"
                  className="btn-ghost-dark btn-sm"
                  disabled={busy}
                  onClick={() => void onEnd(r.id)}
                >
                  Chấm dứt
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );

  if (embedded) {
    return (
      <div className="emp-wt-regime-block" aria-label="Chế độ về sớm">
        {title}
        {body}
      </div>
    );
  }

  return (
    <section className="emp-form-section emp-form-section-col wt-regime-panel">
      {title}
      {body}
    </section>
  );
}
