import React, { useEffect, useState, useCallback } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { Download, ChevronDown, ChevronUp } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface StatEntry {
  mean: number; std: number; min: number; max: number; count: number;
  q1: number; median: number; q3: number; ucl: number; lcl: number;
}
interface WaferPoint { lot_id: string; wafer_no: number; [key: string]: any; }
interface AnalysisGroup {
  group_value: string; count: number;
  stats: Record<string, StatEntry>;
  wafers: WaferPoint[];
}
interface AnalysisResult {
  group_by: string; lot_ids: string[]; yield_params: string[];
  groups: AnalysisGroup[]; total_wafers: number;
}
// ── Constants ──────────────────────────────────────────────────────────────────

const PASS_PARAMS = new Set(["PT1H", "PT1H_outer", "PT1H_center", "PT1H_inner"]);
const PARAM_LABELS: Record<string, string> = {
  PT1H: "PT1H", PT1H_outer: "PT1H Outer", PT1H_center: "PT1H Center",
  PT1H_inner: "PT1H Inner", bl_lkg: "BL Leakage", ledic: "LEDIC",
};
const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#06b6d4"];

function color(i: number) { return COLORS[i % COLORS.length]; }

function fmtDate(ts: number): string {
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function fmtDateFull(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function statBg(value: number, all: number[], isPass: boolean): string {
  const mn = Math.min(...all), mx = Math.max(...all);
  if (mx === mn) return "transparent";
  const good = isPass ? (value - mn) / (mx - mn) : 1 - (value - mn) / (mx - mn);
  if (good > 0.66) return "rgba(34,197,94,0.18)";
  if (good < 0.33) return "rgba(239,68,68,0.18)";
  return "rgba(245,158,11,0.1)";
}

// ── Scatter tooltip ────────────────────────────────────────────────────────────

function ScatterTip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div style={{
      background: "#1e293b", border: "1px solid #334155",
      borderRadius: 8, padding: "8px 12px", fontSize: 11, lineHeight: 1.7,
    }}>
      <div style={{ color: "#64748b", fontSize: 10 }}>{d.x ? fmtDateFull(d.x) : "—"}</div>
      <div style={{ color: d.groupColor ?? "#94a3b8", fontWeight: 600 }}>{d.group}</div>
      <div style={{ color: "#94a3b8" }}>Lot: {d.lot} / W{d.wafer}</div>
      <div style={{ color: "#60a5fa", fontWeight: 700 }}>{typeof d.y === "number" ? d.y.toFixed(2) : "—"}%</div>
    </div>
  );
}

// ── Box Plot (custom SVG) ──────────────────────────────────────────────────────

interface BoxDatum {
  group: string; color: string;
  mean: number; std: number; median: number;
  q1: number; q3: number; ucl: number; lcl: number; count: number;
}

function BoxPlotSVG({ data, yMin, yMax }: { data: BoxDatum[]; yMin: number; yMax: number }) {
  const n = data.length;
  const COL = 72, PAD_L = 38, PAD_R = 8, PAD_T = 12, PAD_B = 34;
  const H = 230;
  const W = n * COL + PAD_L + PAD_R;
  const chartH = H - PAD_T - PAD_B;
  const sy = (v: number) => PAD_T + chartH * (1 - (Math.min(Math.max(v, yMin), yMax) - yMin) / (yMax - yMin));

  // Y axis ticks
  const ticks: number[] = [];
  const steps = 5;
  for (let i = 0; i <= steps; i++) ticks.push(yMin + (yMax - yMin) * i / steps);

  return (
    <svg width={W} height={H} style={{ display: "block", overflow: "visible" }}>
      {/* Grid + Y ticks */}
      {ticks.map((v, ti) => {
        const y = sy(v);
        return (
          <g key={ti}>
            <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y} stroke="#1e293b" strokeWidth={0.5} strokeDasharray="3 2" />
            <text x={PAD_L - 5} y={y} textAnchor="end" dominantBaseline="central" fill="#475569" fontSize={8.5}>
              {v.toFixed(1)}
            </text>
          </g>
        );
      })}
      <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={H - PAD_B} stroke="#334155" strokeWidth={1} />

      {/* Box plots */}
      {data.map((d, i) => {
        const cx  = PAD_L + i * COL + COL / 2;
        const BW  = 28; // box width
        const CW  = 10; // whisker cap width
        const yQ1 = sy(d.q1),  yQ3 = sy(d.q3);
        const yMed= sy(d.median), yMn = sy(d.mean);
        const yU  = sy(d.ucl),  yL  = sy(d.lcl);
        const boxH = Math.abs(yQ1 - yQ3);

        return (
          <g key={d.group}>
            {/* Upper whisker: Q3 → UCL */}
            <line x1={cx} y1={yQ3} x2={cx} y2={yU} stroke={d.color} strokeWidth={1.5} strokeOpacity={0.6} strokeDasharray="3 2" />
            <line x1={cx - CW/2} y1={yU} x2={cx + CW/2} y2={yU} stroke={d.color} strokeWidth={2} />

            {/* Box: Q1–Q3 */}
            <rect x={cx - BW/2} y={yQ3} width={BW} height={Math.max(boxH, 2)}
              fill={d.color} fillOpacity={0.15} stroke={d.color} strokeWidth={1.8} rx={2} />

            {/* Median */}
            <line x1={cx - BW/2} y1={yMed} x2={cx + BW/2} y2={yMed}
              stroke={d.color} strokeWidth={2.5} />

            {/* Mean ✕ */}
            <text x={cx} y={yMn} textAnchor="middle" dominantBaseline="central"
              fill="#f8fafc" fontSize={12} fontWeight="800">✕</text>

            {/* Lower whisker: Q1 → LCL */}
            <line x1={cx} y1={yQ1} x2={cx} y2={yL} stroke={d.color} strokeWidth={1.5} strokeOpacity={0.6} strokeDasharray="3 2" />
            <line x1={cx - CW/2} y1={yL} x2={cx + CW/2} y2={yL} stroke={d.color} strokeWidth={2} />

            {/* Value labels on right side of box */}
            <text x={cx + BW/2 + 4} y={yU}   dominantBaseline="central" fill="#64748b" fontSize={8}>{d.ucl.toFixed(1)}</text>
            <text x={cx + BW/2 + 4} y={yQ3}  dominantBaseline="central" fill="#94a3b8" fontSize={8}>{d.q3.toFixed(1)}</text>
            <text x={cx + BW/2 + 4} y={yMed} dominantBaseline="central" fill={d.color}  fontSize={8} fontWeight="700">{d.median.toFixed(1)}</text>
            <text x={cx + BW/2 + 4} y={yQ1}  dominantBaseline="central" fill="#94a3b8" fontSize={8}>{d.q1.toFixed(1)}</text>
            <text x={cx + BW/2 + 4} y={yL}   dominantBaseline="central" fill="#64748b" fontSize={8}>{d.lcl.toFixed(1)}</text>

            {/* Group name */}
            <text x={cx} y={H - PAD_B + 14} textAnchor="middle" fill={d.color} fontSize={9} fontWeight="600">
              {d.group.length > 10 ? d.group.slice(0, 9) + "…" : d.group}
            </text>
            {/* Count */}
            <text x={cx} y={H - PAD_B + 24} textAnchor="middle" fill="#475569" fontSize={8}>
              n={d.count}
            </text>
          </g>
        );
      })}

      {/* Legend (top-right corner) */}
      {[
        { sym: "─",  label: "Median",    clr: "#94a3b8" },
        { sym: "✕",  label: "Mean",      clr: "#f8fafc"  },
        { sym: "┬┴", label: "3σ UCL/LCL",clr: "#64748b" },
      ].map(({ sym, label, clr }, li) => (
        <g key={li} transform={`translate(${W - PAD_R}, ${PAD_T + li * 13})`}>
          <text x={0} y={0} textAnchor="end" dominantBaseline="central" fill={clr} fontSize={8.5}>
            {sym} {label}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ── Per-parameter card: scatter (left) + box plot (right) ─────────────────────

function ParamCard({ param, groups }: { param: string; groups: AnalysisGroup[] }) {
  const isPass = PASS_PARAMS.has(param);

  // Shared Y domain across scatter + box plot
  const allUCL = groups.map(g => g.stats[param]?.ucl ?? 100);
  const allLCL = groups.map(g => g.stats[param]?.lcl ?? 0);
  const rMax = Math.max(...allUCL);
  const rMin = Math.min(...allLCL, 0);
  const margin = Math.max((rMax - rMin) * 0.06, 1);
  const yMax = Math.ceil(rMax + margin);
  const yMin = Math.max(0, Math.floor(rMin - margin));

  // Scatter data: X = process_ts (ms), color by group
  const scatterSeries = groups.map((g, gi) => ({
    key:       g.group_value,
    color:     color(gi),
    points:    g.wafers.map(w => ({
      x:          (w as any).process_ts ?? 0,
      y:          (w as any)[param] ?? 0,
      group:      g.group_value,
      groupColor: color(gi),
      lot:        w.lot_id,
      wafer:      w.wafer_no,
    })),
  }));

  // X domain (global across all groups)
  const allTs = scatterSeries.flatMap(s => s.points.map(p => p.x)).filter(Boolean);
  const xMin = allTs.length ? Math.min(...allTs) : 0;
  const xMax = allTs.length ? Math.max(...allTs) : 1;
  const xPad = (xMax - xMin) * 0.03;

  // Box plot data
  const boxData: BoxDatum[] = groups.map((g, gi) => ({
    group:  g.group_value,
    color:  color(gi),
    mean:   g.stats[param]?.mean   ?? 0,
    std:    g.stats[param]?.std    ?? 0,
    median: g.stats[param]?.median ?? 0,
    q1:     g.stats[param]?.q1     ?? 0,
    q3:     g.stats[param]?.q3     ?? 0,
    ucl:    g.stats[param]?.ucl    ?? 0,
    lcl:    g.stats[param]?.lcl    ?? 0,
    count:  g.stats[param]?.count  ?? 0,
  }));

  return (
    <div style={{
      background: "#0d1b2e", border: "1px solid #1e3a5f",
      borderRadius: 10, padding: "12px 12px 10px", marginBottom: 10,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10, fontSize: 12, fontWeight: 700, color: "#cbd5e1" }}>
        <span style={{
          padding: "1px 7px", borderRadius: 4, fontSize: 9, fontWeight: 700, letterSpacing: "0.05em",
          background: isPass ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
          color: isPass ? "#86efac" : "#fca5a5",
        }}>
          {isPass ? "PASS" : "FAIL"}
        </span>
        {PARAM_LABELS[param] ?? param}
        <span style={{ color: "#334155", fontWeight: 400, fontSize: 11 }}>(%)</span>
      </div>

      {/* Charts row */}
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        {/* ── Scatter plot ── */}
        <div style={{ flex: "1 1 0", minWidth: 0 }}>
          <div style={{ fontSize: 9, color: "#334155", textAlign: "center", marginBottom: 2, letterSpacing: "0.06em", textTransform: "uppercase" }}>
            Scatter · date trend
          </div>
          <ResponsiveContainer width="100%" height={230}>
            <ScatterChart margin={{ top: 6, right: 10, left: 0, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                type="number"
                dataKey="x"
                domain={[xMin - xPad, xMax + xPad]}
                tickCount={6}
                tickFormatter={(ts) => fmtDate(ts)}
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[yMin, yMax]}
                tick={{ fill: "#475569", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                width={34}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip content={<ScatterTip />} />

              {/* Mean dashed reference lines */}
              {groups.map((g, gi) => (
                <ReferenceLine
                  key={g.group_value}
                  y={g.stats[param]?.mean ?? 0}
                  stroke={color(gi)}
                  strokeDasharray="6 3"
                  strokeOpacity={0.55}
                  strokeWidth={1.5}
                />
              ))}

              {/* Scatter points */}
              {scatterSeries.map(({ key, color: c, points }) => (
                <Scatter key={key} data={points} fill={c} fillOpacity={0.7} r={3} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>

          {/* Group legend */}
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap", marginTop: 2 }}>
            {groups.map((g, gi) => (
              <div key={g.group_value} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "#64748b" }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: color(gi) }} />
                {g.group_value}
              </div>
            ))}
          </div>
        </div>

        {/* ── Box plot ── */}
        <div style={{ flex: "0 0 auto" }}>
          <div style={{ fontSize: 9, color: "#334155", textAlign: "center", marginBottom: 2, letterSpacing: "0.06em", textTransform: "uppercase" }}>
            Box Plot · 3σ
          </div>
          <div style={{ overflowX: "auto" }}>
            <BoxPlotSVG data={boxData} yMin={yMin} yMax={yMax} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Summary stats table ────────────────────────────────────────────────────────

function StatsTable({ result }: { result: AnalysisResult }) {
  const [open, setOpen] = useState(true);
  const params = result.yield_params;
  const meansByParam: Record<string, number[]> = {};
  params.forEach(p => { meansByParam[p] = result.groups.map(g => g.stats[p]?.mean ?? 0); });

  const thBase: React.CSSProperties = {
    background: "#0a1628", color: "#64748b", fontWeight: 600,
    padding: "5px 7px", textAlign: "center", whiteSpace: "nowrap",
    borderBottom: "1px solid #1e293b", fontSize: 10,
  };
  const subTh: React.CSSProperties = { ...thBase, background: "#060e1a", color: "#334155", fontSize: 9 };
  const td: React.CSSProperties = {
    padding: "5px 7px", textAlign: "center", whiteSpace: "nowrap", color: "#e2e8f0", fontSize: 10,
  };

  return (
    <div style={{ background: "#0a1628", border: "1px solid #1e3a5f", borderRadius: 10, overflow: "hidden", marginBottom: 12 }}>
      <div
        onClick={() => setOpen(v => !v)}
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "9px 14px", cursor: "pointer",
          borderBottom: open ? "1px solid #1e293b" : "none",
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8" }}>
          Summary Statistics
          <span style={{ color: "#334155", fontWeight: 400, marginLeft: 10, fontSize: 11 }}>
            {result.total_wafers} wafers · {result.groups.length} groups
          </span>
        </span>
        {open ? <ChevronUp size={13} color="#334155" /> : <ChevronDown size={13} color="#334155" />}
      </div>

      {open && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", fontSize: 10 }}>
            <thead>
              <tr>
                <th style={thBase}>Group</th>
                <th style={thBase}>N</th>
                {params.map(p => {
                  const isPass = PASS_PARAMS.has(p);
                  return (
                    <th key={p} colSpan={7} style={{
                      ...thBase,
                      color: isPass ? "#86efac" : "#fca5a5",
                      borderLeft: "1px solid #1e293b",
                    }}>
                      {PARAM_LABELS[p] ?? p}
                    </th>
                  );
                })}
              </tr>
              <tr>
                <th style={subTh}></th><th style={subTh}></th>
                {params.map(p => (
                  <React.Fragment key={p}>
                    {["Mean", "Std", "UCL+3σ", "LCL-3σ", "Median", "Q1", "Q3"].map(h => (
                      <th key={h} style={{ ...subTh, borderLeft: h === "Mean" ? "1px solid #1e293b" : undefined }}>
                        {h}
                      </th>
                    ))}
                  </React.Fragment>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.groups.map((g, gi) => (
                <tr key={g.group_value} style={{ borderBottom: "1px solid #0a1222" }}>
                  <td style={{ ...td, fontWeight: 700, color: color(gi) }}>{g.group_value}</td>
                  <td style={{ ...td, color: "#475569" }}>{g.count}</td>
                  {params.map(p => {
                    const s = g.stats[p];
                    const isPass = PASS_PARAMS.has(p);
                    const bg = s ? statBg(s.mean, meansByParam[p], isPass) : "transparent";
                    return (
                      <React.Fragment key={p}>
                        <td style={{ ...td, background: bg, fontWeight: 700, borderLeft: "1px solid #1e293b" }}>
                          {s?.mean.toFixed(2) ?? "—"}
                        </td>
                        <td style={{ ...td, color: "#64748b" }}>{s?.std.toFixed(2) ?? "—"}</td>
                        <td style={{ ...td, color: "#94a3b8" }}>{s?.ucl.toFixed(2) ?? "—"}</td>
                        <td style={{ ...td, color: "#94a3b8" }}>{s?.lcl.toFixed(2) ?? "—"}</td>
                        <td style={{ ...td }}>{s?.median.toFixed(2) ?? "—"}</td>
                        <td style={{ ...td, color: "#475569" }}>{s?.q1.toFixed(2) ?? "—"}</td>
                        <td style={{ ...td, color: "#475569" }}>{s?.q3.toFixed(2) ?? "—"}</td>
                      </React.Fragment>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main exported component ────────────────────────────────────────────────────

interface Props { value: string; }

export default function YieldAnalysisCard({ value }: Props) {
  const [result, setResult]   = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const parts = value.split(":");
  const lotIds      = parts[0]?.split(",").filter(Boolean) ?? [];
  const groupBy     = parts[1] ?? "recipe";
  const yieldParams = parts[2]?.split(",").filter(Boolean)
    ?? ["PT1H", "PT1H_outer", "PT1H_center", "PT1H_inner", "bl_lkg", "ledic"];

  useEffect(() => {
    fetch("/api/yield/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lot_ids: lotIds, group_by: groupBy, yield_params: yieldParams }),
    })
      .then(r => r.json())
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const exportExcel = useCallback(async () => {
    setExporting(true);
    try {
      const res = await fetch("/api/yield/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lot_ids: lotIds, group_by: groupBy, yield_params: yieldParams }),
      });
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url; a.download = `yield_analysis_${groupBy}.xlsx`; a.click();
      URL.revokeObjectURL(url);
    } finally { setExporting(false); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const shell: React.CSSProperties = {
    marginTop: 12,
    background: "#080f1e",
    border: "1px solid #1e3a5f",
    borderRadius: 12,
    overflow: "hidden",
  };

  if (loading) return (
    <div style={shell}>
      <div style={{ padding: "14px 16px", color: "#334155", fontSize: 13 }}>수율 분석 로딩 중...</div>
    </div>
  );
  if (!result) return (
    <div style={shell}>
      <div style={{ padding: "14px 16px", color: "#ef4444", fontSize: 13 }}>데이터를 불러올 수 없습니다.</div>
    </div>
  );

  const groupByLabel: Record<string, string> = {
    recipe: "Recipe", equipment: "Equipment", process_id: "Process ID", custom_group: "Custom Group",
  };

  const passParams = yieldParams.filter(p => PASS_PARAMS.has(p));
  const failParams = yieldParams.filter(p => !PASS_PARAMS.has(p));

  return (
    <div style={shell}>
      {/* ── Header ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "11px 14px", borderBottom: "1px solid #1e293b", flexWrap: "wrap", gap: 8,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#e2e8f0" }}>수율 Grouping 분석</span>
          <span style={{
            fontSize: 11, background: "#1e293b", border: "1px solid #334155",
            color: "#94a3b8", padding: "2px 9px", borderRadius: 12,
          }}>
            {groupByLabel[groupBy] ?? groupBy}
          </span>
          <span style={{ fontSize: 11, color: "#334155" }}>
            {lotIds.length} lots · {result.total_wafers} wafers · {result.groups.length} groups
          </span>
        </div>
        <button
          onClick={exportExcel} disabled={exporting}
          style={{
            display: "flex", alignItems: "center", gap: 5,
            padding: "5px 12px", background: "#065f46", border: "1px solid #047857",
            borderRadius: 7, color: "#6ee7b7", fontSize: 12, fontWeight: 600,
            cursor: exporting ? "not-allowed" : "pointer",
            opacity: exporting ? 0.6 : 1, fontFamily: "inherit",
          }}
        >
          <Download size={12} />
          {exporting ? "…" : "Excel"}
        </button>
      </div>

      {/* ── Body ── */}
      <div style={{ padding: "12px 14px" }}>
        {/* Stats table */}
        <StatsTable result={result} />

        {/* Pass rate charts */}
        {passParams.length > 0 && (
          <>
            <div style={{
              fontSize: 10, fontWeight: 700, color: "#22c55e",
              letterSpacing: "0.08em", textTransform: "uppercase",
              marginBottom: 8,
            }}>
              Pass Rate
            </div>
            {passParams.map(p => (
              <ParamCard key={p} param={p} groups={result.groups} />
            ))}
          </>
        )}

        {/* Fail rate charts */}
        {failParams.length > 0 && (
          <>
            <div style={{
              fontSize: 10, fontWeight: 700, color: "#ef4444",
              letterSpacing: "0.08em", textTransform: "uppercase",
              marginTop: 10, marginBottom: 8,
            }}>
              Fail Rate
            </div>
            {failParams.map(p => (
              <ParamCard key={p} param={p} groups={result.groups} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
