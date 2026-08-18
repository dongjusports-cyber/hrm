import { useCallback, useEffect, useState } from "react";
import {
  createEmployeeWtRegime,
  endEmployeeWtRegime,
  fetchEmployeeWtRegimes,
  type EmployeeWtRegime,
  type WtRegimeType,
} from "../../shared/api";

const TYPE_LABEL: Record<WtRegimeType, string> = {
  PREGNANT: "Đang mang thai",
  MATERNITY: "Nghỉ thai sản",
  CHILD: "Nuôi con nhỏ",
};

const DEFAULT_HOURS: Record<WtRegimeType, number> = {
  PREGNANT: 1,
  MATERNITY: 0,
  CHILD: 2,
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addMonths(iso: string, months: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1 + months, d);
  const yy = dt.getFullYear();
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  const dd = String(dt.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

function isActive(r: EmployeeWtRegime): boolean {
  const today = todayIso();
  return r.date_from <= today && today <= r.date_to;
}

function regimeSummary(r: EmployeeWtRegime): string {
  const label = TYPE_LABEL[r.regime_type] || r.regime_type;
  const hours =
    r.regime_type === "MATERNITY" || r.hours_early <= 0 ? "" : ` · ${r.hours_early}h`;
  return `${label}${hours} · ${fmtDate(r.date_from)}–${fmtDate(r.date_to)}`;
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
      setError(e instanceof Error ? e.message : "Không tải chế độ đặc biệt.");
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
    if (next === "MATERNITY") {
      setDateTo(addMonths(dateFrom, 6));
    }
  }

  function onChangeFrom(next: string) {
    setDateFrom(next);
    if (regimeType === "MATERNITY") {
      setDateTo(addMonths(next, 6));
    } else if (dateTo < next) {
      setDateTo(next);
    }
  }

  async function onAdd() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      await createEmployeeWtRegime(employeeId, {
        regime_type: regimeType,
        hours_early: regimeType === "MATERNITY" ? 0 : hoursEarly,
        date_from: dateFrom,
        date_to: dateTo,
        note: note.trim(),
      });
      setNote("");
      setOk(
        regimeType === "MATERNITY"
          ? "Đã lưu nghỉ thai sản. Bảng công đã gắn MLE; BH và công đoàn tạm dừng."
          : "Đã lưu chế độ. Công đã được tính lại. Giai đoạn cũ (nếu còn mở) đã tự cắt.",
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không lưu được chế độ đặc biệt.");
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
    <h4 className="emp-allow-block-title">Chế độ đặc biệt</h4>
  ) : (
    <h3 className="emp-form-section-title">Chế độ đặc biệt</h3>
  );

  const body = (
    <>
      {error && <p className="form-error">{error}</p>}
      {ok && <p className="form-ok">{ok}</p>}

      <p className="field-hint">
        Chỉ chọn từ–đến. Giai đoạn đang mở tự cắt ngày kết thúc = ngày trước ngày bắt đầu mới.
        {regimeType === "MATERNITY"
          ? " Nghỉ thai sản: hệ thống tự đánh MLE trên bảng công, tạm dừng BHXH/BHYT/BHTN và công đoàn."
          : " Mang thai / nuôi con: chọn 1–2–3 giờ về sớm."}
      </p>

      <div className="wt-regime-form">
        <label className="field">
          <span>Loại</span>
          <select
            value={regimeType}
            onChange={(e) => onChangeType(e.target.value as WtRegimeType)}
          >
            <option value="PREGNANT">Đang mang thai</option>
            <option value="MATERNITY">Nghỉ thai sản</option>
            <option value="CHILD">Nuôi con nhỏ</option>
          </select>
        </label>
        {regimeType !== "MATERNITY" && (
          <label className="field">
            <span>Giờ về sớm</span>
            <select value={hoursEarly} onChange={(e) => setHoursEarly(Number(e.target.value))}>
              <option value={1}>1 giờ</option>
              <option value={2}>2 giờ</option>
              <option value={3}>3 giờ</option>
            </select>
          </label>
        )}
        <label className="field">
          <span>Từ ngày</span>
          <input
            type="date"
            value={dateFrom}
            min={regimeType === "MATERNITY" ? undefined : todayIso()}
            onChange={(e) => onChangeFrom(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Đến ngày</span>
          <input type="date" value={dateTo} min={dateFrom} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <label className="field wt-regime-note">
          <span>Ghi chú</span>
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <button type="button" className="btn-primary btn-sm wt-regime-add-btn" disabled={busy} onClick={() => void onAdd()}>
          Thêm chế độ
        </button>
      </div>

      {loading ? (
        <p className="field-hint">Đang tải…</p>
      ) : rows.length === 0 ? (
        <p className="field-hint">Chưa có chế độ đặc biệt.</p>
      ) : (
        <ul className="wt-regime-list">
          {rows.map((r) => (
            <li key={r.id} className={isActive(r) && !r.ended_at ? "wt-regime-active" : "wt-regime-done"}>
              <span className="wt-regime-info">
                {regimeSummary(r)}
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
      <div className="emp-wt-regime-block emp-profile-bottom-panel" aria-label="Chế độ đặc biệt">
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
