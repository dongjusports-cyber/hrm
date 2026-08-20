import { useMemo } from "react";
import type { KpiMonthTeamsData } from "../../shared/api";
import {
  categoryBars,
  companyDays,
  monthLabel,
  niceMax,
  teamOtBars,
  type ChartCategory,
  type ChartDay,
  type ChartTeamOt,
} from "./kpiChartSeries";

const NAVY = "#1e40af";
const TEAL = "#0f766e";
const SLATE = "#64748b";
const CAT_COLOR: Record<string, string> = {
  direct: "#1e40af",
  prod_indirect: "#0f766e",
  admin_indirect: "#64748b",
};

function fmt(n: number, digits = 0): string {
  return n.toLocaleString("vi-VN", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

function ticks(max: number, count = 4): number[] {
  return Array.from({ length: count + 1 }, (_, i) => (max * i) / count);
}

function ellipsize(s: string, n: number): string {
  const t = s.trim();
  return t.length <= n ? t : `${t.slice(0, n - 1)}…`;
}

/** Bốn biểu đồ KPI tháng — SVG, in A4 được. */
export function KpiCharts({ data }: { data: KpiMonthTeamsData }) {
  const days = useMemo(() => companyDays(data), [data]);
  const teams = useMemo(() => teamOtBars(data), [data]);
  const cats = useMemo(() => categoryBars(data), [data]);
  const periodVi = monthLabel(data.period);

  return (
    <div className="kpi-charts">
      <div className="kpi-print-banner">
        <strong>KPI Dongju Sports VN</strong>
        <span>Tháng {periodVi} · nguồn vân tay · OT sổ + ngoài + CN + lễ</span>
      </div>
      <div className="kpi-chart-grid">
        <article className="kpi-chart-card">
          <h2>Có mặt / HC từng ngày</h2>
          <PresentHcChart days={days} />
        </article>
        <article className="kpi-chart-card">
          <h2>Giờ OT từng ngày</h2>
          <OtDayChart days={days} />
        </article>
        <article className="kpi-chart-card">
          <h2>OT theo tổ</h2>
          {teams.length === 0 ? (
            <p className="kpi-chart-empty">Không có OT tháng này.</p>
          ) : (
            <OtTeamChart rows={teams} />
          )}
        </article>
        <article className="kpi-chart-card">
          <h2>Trực tiếp / gián tiếp</h2>
          <CategoryChart rows={cats} />
        </article>
      </div>
    </div>
  );
}

function PresentHcChart({ days }: { days: ChartDay[] }) {
  const W = 720;
  const H = 228;
  const pad = { l: 40, r: 10, t: 12, b: 28 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const n = Math.max(days.length, 1);
  const yMax = niceMax(Math.max(...days.map((d) => Math.max(d.headcount, d.present)), 1));
  const barW = Math.max(2, (plotW / n) * 0.62);
  const x = (i: number) => pad.l + ((i + 0.5) * plotW) / n;
  const y = (v: number) => pad.t + plotH - (v / yMax) * plotH;
  const line = days.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.headcount).toFixed(1)}`).join(" ");

  return (
    <figure className="kpi-svg-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Có mặt và headcount từng ngày">
        {days.map((d, i) =>
          d.isWorkday ? null : (
            <rect
              key={`off-${d.workDate}`}
              x={pad.l + (i * plotW) / n}
              y={pad.t}
              width={plotW / n}
              height={plotH}
              fill="#f1f5f9"
            />
          ),
        )}
        {ticks(yMax).map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="#e2e8f0" strokeWidth="1" />
            <text x={pad.l - 6} y={y(t) + 3} textAnchor="end" className="kpi-svg-tick">
              {fmt(t)}
            </text>
          </g>
        ))}
        {days.map((d, i) => (
          <rect
            key={d.workDate}
            x={x(i) - barW / 2}
            y={y(d.present)}
            width={barW}
            height={Math.max(0, y(0) - y(d.present))}
            fill={NAVY}
            rx="1"
          />
        ))}
        <path d={line} fill="none" stroke={SLATE} strokeWidth="1.8" strokeDasharray="5 4" />
        {days.map((d, i) =>
          d.dayNum === 1 || d.dayNum % 5 === 0 || i === days.length - 1 ? (
            <text key={`x-${d.workDate}`} x={x(i)} y={H - 8} textAnchor="middle" className="kpi-svg-tick">
              {d.dayNum}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption>
        <span className="kpi-swatch kpi-swatch-navy" /> Có mặt
        <span className="kpi-swatch kpi-swatch-dash" /> HC
        <span className="kpi-swatch kpi-swatch-off" /> CN/lễ
      </figcaption>
    </figure>
  );
}

function OtDayChart({ days }: { days: ChartDay[] }) {
  const W = 720;
  const H = 228;
  const pad = { l: 40, r: 10, t: 12, b: 28 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const n = Math.max(days.length, 1);
  const yMax = niceMax(Math.max(...days.map((d) => d.otHours), 1));
  const barW = Math.max(2, (plotW / n) * 0.62);
  const x = (i: number) => pad.l + ((i + 0.5) * plotW) / n;
  const y = (v: number) => pad.t + plotH - (v / yMax) * plotH;

  return (
    <figure className="kpi-svg-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Giờ OT từng ngày">
        {days.map((d, i) =>
          d.isWorkday ? null : (
            <rect
              key={`off-${d.workDate}`}
              x={pad.l + (i * plotW) / n}
              y={pad.t}
              width={plotW / n}
              height={plotH}
              fill="#f1f5f9"
            />
          ),
        )}
        {ticks(yMax).map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="#e2e8f0" strokeWidth="1" />
            <text x={pad.l - 6} y={y(t) + 3} textAnchor="end" className="kpi-svg-tick">
              {fmt(t, t >= 10 ? 0 : 1)}
            </text>
          </g>
        ))}
        {days.map((d, i) => (
          <rect
            key={d.workDate}
            x={x(i) - barW / 2}
            y={y(d.otHours)}
            width={barW}
            height={Math.max(0, y(0) - y(d.otHours))}
            fill={TEAL}
            rx="1"
          />
        ))}
        {days.map((d, i) =>
          d.dayNum === 1 || d.dayNum % 5 === 0 || i === days.length - 1 ? (
            <text key={`x-${d.workDate}`} x={x(i)} y={H - 8} textAnchor="middle" className="kpi-svg-tick">
              {d.dayNum}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption>Giờ OT (sổ + ngoài + CN + lễ)</figcaption>
    </figure>
  );
}

function OtTeamChart({ rows }: { rows: ChartTeamOt[] }) {
  const W = 720;
  const rowH = 22;
  const pad = { l: 148, r: 52, t: 8, b: 8 };
  const H = pad.t + pad.b + rows.length * rowH;
  const plotW = W - pad.l - pad.r;
  const xMax = niceMax(Math.max(...rows.map((r) => r.hours), 1));
  const x = (v: number) => pad.l + (v / xMax) * plotW;

  return (
    <figure className="kpi-svg-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Giờ OT theo tổ">
        {rows.map((r, i) => {
          const y = pad.t + i * rowH;
          return (
            <g key={r.teamId}>
              <text x={pad.l - 8} y={y + 14} textAnchor="end" className="kpi-svg-label">
                {ellipsize(r.label, 18)}
              </text>
              <rect x={pad.l} y={y + 4} width={plotW} height={14} fill="#f1f5f9" rx="2" />
              <rect x={pad.l} y={y + 4} width={Math.max(2, x(r.hours) - pad.l)} height={14} fill={TEAL} rx="2" />
              <text x={x(r.hours) + 6} y={y + 15} className="kpi-svg-tick">
                {fmt(r.hours, 1)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

function CategoryChart({ rows }: { rows: ChartCategory[] }) {
  const W = 720;
  const H = 228;
  const pad = { l: 40, r: 16, t: 28, b: 36 };
  const mid = W / 2;
  const attMax = niceMax(Math.max(...rows.map((r) => r.attendants), 1));
  const otMax = niceMax(Math.max(...rows.map((r) => r.otHours), 1));

  return (
    <figure className="kpi-svg-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Ngày có mặt và giờ OT theo loại">
        <GroupBars
          title="Ngày có mặt"
          rows={rows}
          value={(r) => r.attendants}
          max={attMax}
          x0={pad.l}
          x1={mid - 12}
          y0={pad.t}
          y1={H - pad.b}
          digits={0}
        />
        <GroupBars
          title="Giờ OT"
          rows={rows}
          value={(r) => r.otHours}
          max={otMax}
          x0={mid + 12}
          x1={W - pad.r}
          y0={pad.t}
          y1={H - pad.b}
          digits={1}
        />
      </svg>
      <figcaption>
        {rows.map((r) => (
          <span key={r.category}>
            <span className="kpi-swatch" style={{ background: CAT_COLOR[r.category] }} /> {r.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

function GroupBars({
  title,
  rows,
  value,
  max,
  x0,
  x1,
  y0,
  y1,
  digits,
}: {
  title: string;
  rows: ChartCategory[];
  value: (r: ChartCategory) => number;
  max: number;
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  digits: number;
}) {
  const plotH = y1 - y0;
  const y = (v: number) => y1 - (v / max) * plotH;
  const gap = 10;
  const barW = Math.max(8, (x1 - x0 - gap * (rows.length - 1)) / rows.length);
  return (
    <g>
      <text x={(x0 + x1) / 2} y={y0 - 8} textAnchor="middle" className="kpi-svg-label">
        {title}
      </text>
      {ticks(max, 3).map((t) => (
        <line key={`${title}-${t}`} x1={x0} x2={x1} y1={y(t)} y2={y(t)} stroke="#e2e8f0" strokeWidth="1" />
      ))}
      {rows.map((r, i) => {
        const x = x0 + i * (barW + gap);
        const v = value(r);
        return (
          <g key={`${title}-${r.category}`}>
            <rect x={x} y={y(v)} width={barW} height={Math.max(0, y1 - y(v))} fill={CAT_COLOR[r.category]} rx="2" />
            <text x={x + barW / 2} y={y1 + 14} textAnchor="middle" className="kpi-svg-tick">
              {fmt(v, digits)}
            </text>
          </g>
        );
      })}
    </g>
  );
}
