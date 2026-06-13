import React, { useState } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { DefectYieldHistoryPayload, DefectYieldWafer, TopWafer, YieldDie } from "../types";

const DEFECT_COLORS: Record<string, string> = {
  PARTICLE: "#f59e0b", SCRATCH: "#ef4444", BRIDGE: "#a855f7",
  PIT: "#3b82f6",      RESIDUE: "#22c55e", CLUSTER: "#ec4899",
};

function binColor(bin: number): string {
  if (bin === 1) return "#15803d";
  if (bin === 2) return "#ef4444";
  if (bin === 3) return "#f97316";
  return "#a855f7";
}

function killColor(rate: number): string {
  return rate >= 40 ? "#f87171" : rate >= 20 ? "#fbbf24" : "#4ade80";
}
function killBg(rate: number): string {
  return rate >= 40 ? "#3f0f0f" : rate >= 20 ? "#3f2a00" : "#0f2a0f";
}
function dotColor(rate: number): string {
  return rate >= 40 ? "#ef4444" : rate >= 20 ? "#f59e0b" : "#22c55e";
}

// ── 미니 Wafer Map (Yield Bin + Defect Overlay) ──────────────────────────────
const CX = 80, CY = 82, R = 72;
const DIE_PX = 7, GRID = 20;
const START = CX - (GRID / 2) * DIE_PX; // = 10

function MiniYieldMap({ wafer, defectType, rank }: { wafer: TopWafer; defectType: string; rank: number }) {
  const typeColor = DEFECT_COLORS[defectType] ?? "#888";
  const clipId = `dyh-clip-${wafer.wafer_no}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg viewBox="0 0 160 182" style={{ width: 148, display: "block", flexShrink: 0 }}>
        <defs>
          <clipPath id={clipId}>
            <circle cx={CX} cy={CY} r={R - 1} />
          </clipPath>
        </defs>

        {/* rank badge */}
        <rect x={2} y={2} width={20} height={14} rx={3} fill={rank <= 3 ? "#7f1d1d" : "#1e293b"} />
        <text x={12} y={13} fill={rank <= 3 ? "#fca5a5" : "#94a3b8"} fontSize={8} textAnchor="middle" fontWeight={700}>
          #{rank}
        </text>

        {/* Wafer base */}
        <circle cx={CX} cy={CY} r={R} fill="#0a0a18" stroke="#334155" strokeWidth={1.5} />

        {/* Die yield bins */}
        <g clipPath={`url(#${clipId})`}>
          {wafer.dies.map((die: YieldDie) => (
            <rect
              key={`${die.row}-${die.col}`}
              x={START + die.col * DIE_PX + 0.5}
              y={START + die.row * DIE_PX + 0.5}
              width={DIE_PX - 1}
              height={DIE_PX - 1}
              fill={binColor(die.bin)}
              opacity={0.82}
            />
          ))}
        </g>

        {/* Defect dots (해당 type만) */}
        {wafer.defects.map((d) => {
          const sx = CX + d.x_norm * R;
          const sy = CY - d.y_norm * R;
          return (
            <circle
              key={d.defect_id}
              cx={sx} cy={sy} r={3}
              fill={typeColor}
              stroke="#000"
              strokeWidth={0.6}
              opacity={0.95}
            >
              <title>{d.defect_type} {d.size_um}μm</title>
            </circle>
          );
        })}

        {/* Wafer outline + notch */}
        <circle cx={CX} cy={CY} r={R} fill="none" stroke="#64748b" strokeWidth={1.2} />
        <path
          d={`M ${CX - 6} ${CY + R + 1} Q ${CX} ${CY + R - 4} ${CX + 6} ${CY + R + 1}`}
          fill="#0a0a18" stroke="#64748b" strokeWidth={0.8}
        />

        {/* Labels */}
        <text x={CX} y={CY + R + 14} fill="#cbd5e1" fontSize={9} textAnchor="middle" fontWeight={600}>
          W{wafer.wafer_no}
        </text>
        <text x={CX} y={CY + R + 25} fill="#22c55e" fontSize={8} textAnchor="middle">
          Yield {wafer.yield_pct}%
        </text>
      </svg>

      {/* 아래 메타 정보 */}
      <div style={{ fontSize: 11, color: typeColor, fontWeight: 700 }}>
        {defectType} {wafer.defect_count}건
      </div>
      <div style={{ fontSize: 10, background: killBg(wafer.kill_rate_pct), color: killColor(wafer.kill_rate_pct), borderRadius: 4, padding: "1px 7px", fontWeight: 600 }}>
        Kill {wafer.kill_rate_pct}%
      </div>
    </div>
  );
}

// ── Scatter Tooltip ───────────────────────────────────────────────────────────
function ScatterTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d: DefectYieldWafer = payload[0]?.payload;
  return (
    <div style={{ background: "#1e293b", border: "1px solid #475569", borderRadius: 8, padding: "8px 12px", fontSize: 12, lineHeight: 1.8 }}>
      <div style={{ color: "#94a3b8" }}>Wafer: <strong style={{ color: "#e2e8f0" }}>W{d.wafer_no}</strong></div>
      <div style={{ color: "#94a3b8" }}>Defect: <strong style={{ color: "#e2e8f0" }}>{d.defect_count}건</strong></div>
      <div style={{ color: "#94a3b8" }}>수율: <strong style={{ color: "#22c55e" }}>{d.yield_pct}%</strong></div>
      <div style={{ color: "#94a3b8" }}>Kill Rate: <strong style={{ color: dotColor(d.kill_rate_pct) }}>{d.kill_rate_pct}%</strong></div>
    </div>
  );
}

// ── 범례 칩 ──────────────────────────────────────────────────────────────────
function LegendRow() {
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", fontSize: 10, color: "#94a3b8", marginBottom: 4 }}>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "#15803d", display: "inline-block", borderRadius: 2 }} /> Pass
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "#ef4444", display: "inline-block", borderRadius: 2 }} /> Fail B2
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "#f97316", display: "inline-block", borderRadius: 2 }} /> Fail B3
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "#a855f7", display: "inline-block", borderRadius: 2 }} /> Fail B4+
      </span>
      <span style={{ color: "#64748b" }}>● Defect 위치</span>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
interface Props {
  data: DefectYieldHistoryPayload;
}

export default function DefectYieldHistory({ data }: Props) {
  const [showTable, setShowTable] = useState(false);
  const typeColor = DEFECT_COLORS[data.defect_type] ?? "#888";

  const corrLabel =
    data.correlation < -0.5 ? "강한 음의 상관 (수율 영향 큼)" :
    data.correlation < -0.3 ? "중간 음의 상관" :
    data.correlation < 0.3  ? "상관 약함" : "양의 상관 (예외적)";
  const corrColor =
    data.correlation < -0.5 ? "#ef4444" :
    data.correlation < -0.3 ? "#f59e0b" : "#22c55e";

  const avgYield = data.avg_yield_pct;

  return (
    <div className="trend-chart-container">
      {/* 헤더 */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0, fontSize: 14, color: "#94a3b8" }}>
          Defect–수율 이력 분석 — Lot: <strong style={{ color: "#e2e8f0" }}>{data.lot_id}</strong>
          {"  "}|{"  "}<strong style={{ color: typeColor }}>{data.defect_type}</strong>
        </h3>
        <span style={{ fontSize: 11, color: "#64748b", marginLeft: "auto" }}>25 wafers</span>
      </div>

      {/* 통계 칩 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        {[
          { label: "상관계수 r", val: String(data.correlation), color: corrColor },
          { label: "판정",       val: corrLabel,                 color: corrColor },
          { label: "평균 수율",  val: `${data.avg_yield_pct}%`,  color: "#22c55e" },
          { label: "평균 Kill",  val: `${data.avg_kill_rate_pct}%`, color: data.avg_kill_rate_pct > 30 ? "#ef4444" : "#f59e0b" },
          { label: "고위험 슬롯", val: `${data.high_risk_wafers}개`, color: "#ef4444" },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ fontSize: 11, background: "#0f172a", border: `1px solid ${color}44`, borderRadius: 6, padding: "2px 10px", color }}>
            {label}: <strong>{val}</strong>
          </div>
        ))}
      </div>

      {/* ── Section 1: Scatter (defect count vs yield) ── */}
      <div style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600, marginBottom: 6 }}>
        Defect 건수 vs 수율 (전체 25 Wafer)
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 6, fontSize: 11, color: "#94a3b8" }}>
        {[["Kill ≥40%", "#ef4444"], ["Kill 20~40%", "#f59e0b"], ["Kill <20%", "#22c55e"]].map(([l, c]) => (
          <span key={l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: c as string, display: "inline-block" }} />{l}
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart margin={{ top: 4, right: 8, left: -10, bottom: 18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            type="number" dataKey="defect_count" name="Defect 수"
            tick={{ fontSize: 9, fill: "#64748b" }} tickLine={false}
            label={{ value: `${data.defect_type} 건수`, fill: "#475569", fontSize: 10, position: "insideBottom", offset: -12 }}
          />
          <YAxis
            type="number" dataKey="yield_pct" name="수율 (%)"
            tick={{ fontSize: 9, fill: "#64748b" }} tickLine={false}
            domain={[Math.max(0, avgYield - 15), Math.min(100, avgYield + 10)]}
          />
          <Tooltip content={<ScatterTooltip />} cursor={{ stroke: "#334155", strokeWidth: 1 }} />
          <ReferenceLine y={avgYield} stroke="#475569" strokeDasharray="4 2" strokeWidth={1}
            label={{ value: `AVG ${avgYield}%`, fill: "#64748b", fontSize: 9, position: "insideTopRight" }} />
          <Scatter
            data={data.wafers}
            isAnimationActive={false}
            shape={(props: any) => {
              const d: DefectYieldWafer = props.payload;
              return <circle cx={props.cx} cy={props.cy} r={d.defect_count > 0 ? 5 : 3} fill={dotColor(d.kill_rate_pct)} stroke="#000" strokeWidth={0.4} opacity={0.85} />;
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>

      {/* ── Section 2: Top 10 Mini Wafer Maps ── */}
      <div style={{ marginTop: 18 }}>
        <div style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600, marginBottom: 8 }}>
          Defect 집중 상위 {data.top_wafers.length}개 Wafer — Yield Bin + {data.defect_type} Defect 위치
        </div>
        <LegendRow />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 6 }}>
          {data.top_wafers.map((w, i) => (
            <MiniYieldMap key={w.wafer_no} wafer={w} defectType={data.defect_type} rank={i + 1} />
          ))}
        </div>
      </div>

      {/* ── Section 3: 전체 테이블 (접기) ── */}
      <button
        onClick={() => setShowTable((s) => !s)}
        style={{ background: "none", border: `1px solid ${typeColor}88`, color: typeColor, borderRadius: 6, padding: "3px 12px", fontSize: 11, cursor: "pointer", marginTop: 14, display: "flex", alignItems: "center", gap: 6 }}
      >
        <span>{showTable ? "▲" : "▼"}</span>
        전체 25 Wafer 상세 이력
      </button>

      {showTable && (
        <div style={{ maxHeight: 260, overflowY: "auto", borderRadius: 8, border: "1px solid #1e293b", marginTop: 8 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0, background: "#0f172a", zIndex: 1 }}>
              <tr>
                {["Wafer", "Defect 수", "수율 %", "영향 Die", "Kill Die", "Kill Rate"].map((h) => (
                  <th key={h} style={{ padding: "6px 10px", color: "#64748b", textAlign: "left", fontWeight: 600, fontSize: 11, borderBottom: "1px solid #1e293b" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.wafers.map((w, i) => (
                <tr key={w.wafer_no} style={{ borderBottom: "1px solid #1e2940", background: i % 2 === 0 ? "transparent" : "#0d1525" }}>
                  <td style={{ padding: "5px 10px", color: "#94a3b8" }}>W{w.wafer_no}</td>
                  <td style={{ padding: "5px 10px", color: w.defect_count > 0 ? typeColor : "#475569", fontWeight: w.defect_count > 0 ? 700 : 400 }}>{w.defect_count}</td>
                  <td style={{ padding: "5px 10px", color: "#22c55e" }}>{w.yield_pct}%</td>
                  <td style={{ padding: "5px 10px", color: "#94a3b8" }}>{w.dies_affected}</td>
                  <td style={{ padding: "5px 10px", color: "#ef4444" }}>{w.killed_dies}</td>
                  <td style={{ padding: "5px 10px" }}>
                    <span style={{ background: killBg(w.kill_rate_pct), color: killColor(w.kill_rate_pct), borderRadius: 4, padding: "1px 7px", fontWeight: 600, fontSize: 11 }}>
                      {w.kill_rate_pct}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
