import React, { useState } from "react";
import { alpha } from "../lib/color";
import {
  ScatterChart, Scatter, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { DefectYieldHistoryPayload, DefectYieldWafer, TopWafer, YieldDie } from "../types";

const DEFECT_COLORS: Record<string, string> = {
  PARTICLE: "var(--c-amber)", SCRATCH: "var(--c-red)", BRIDGE: "var(--c-purple)",
  PIT: "var(--c-blue)",      RESIDUE: "var(--c-green)", CLUSTER: "#ec4899",
};

function binColor(bin: number): string {
  if (bin === 1) return "#15803d";
  if (bin === 2) return "var(--c-red)";
  if (bin === 3) return "#f97316";
  return "var(--c-purple)";
}

function killColor(rate: number): string {
  return rate >= 40 ? "var(--err)" : rate >= 20 ? "var(--warn)" : "var(--ok)";
}
function killBg(rate: number): string {
  return rate >= 40 ? "var(--err-soft)" : rate >= 20 ? "var(--warn-soft)" : "var(--ok-soft)";
}
function dotColor(rate: number): string {
  return rate >= 40 ? "var(--c-red)" : rate >= 20 ? "var(--c-amber)" : "var(--c-green)";
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
        <rect x={2} y={2} width={20} height={14} rx={3} fill={rank <= 3 ? "var(--err-soft)" : "var(--sand)"} />
        <text x={12} y={13} fill={rank <= 3 ? "var(--err)" : "var(--sub)"} fontSize={8} textAnchor="middle" fontWeight={700}>
          #{rank}
        </text>

        {/* Wafer base */}
        <circle cx={CX} cy={CY} r={R} fill="var(--sunken)" stroke="var(--line-strong)" strokeWidth={1.5} />

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
        <circle cx={CX} cy={CY} r={R} fill="none" stroke="var(--faint)" strokeWidth={1.2} />
        <path
          d={`M ${CX - 6} ${CY + R + 1} Q ${CX} ${CY + R - 4} ${CX + 6} ${CY + R + 1}`}
          fill="var(--sunken)" stroke="var(--faint)" strokeWidth={0.8}
        />

        {/* Labels */}
        <text x={CX} y={CY + R + 14} fill="var(--ink)" fontSize={9} textAnchor="middle" fontWeight={600}>
          W{wafer.wafer_no}
        </text>
        <text x={CX} y={CY + R + 25} fill="var(--c-green)" fontSize={8} textAnchor="middle">
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
    <div style={{ background: "var(--sand)", border: "1px solid var(--faint)", borderRadius: 8, padding: "8px 12px", fontSize: 12, lineHeight: 1.8 }}>
      <div style={{ color: "var(--sub)" }}>Wafer: <strong style={{ color: "var(--ink)" }}>W{d.wafer_no}</strong></div>
      <div style={{ color: "var(--sub)" }}>Defect: <strong style={{ color: "var(--ink)" }}>{d.defect_count}건</strong></div>
      <div style={{ color: "var(--sub)" }}>수율: <strong style={{ color: "var(--c-green)" }}>{d.yield_pct}%</strong></div>
      <div style={{ color: "var(--sub)" }}>Kill Rate: <strong style={{ color: dotColor(d.kill_rate_pct) }}>{d.kill_rate_pct}%</strong></div>
    </div>
  );
}

// ── 범례 칩 ──────────────────────────────────────────────────────────────────
function LegendRow() {
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", fontSize: 10, color: "var(--sub)", marginBottom: 4 }}>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "#15803d", display: "inline-block", borderRadius: 2 }} /> Pass
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "var(--c-red)", display: "inline-block", borderRadius: 2 }} /> Fail B2
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "#f97316", display: "inline-block", borderRadius: 2 }} /> Fail B3
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
        <span style={{ width: 10, height: 10, background: "var(--c-purple)", display: "inline-block", borderRadius: 2 }} /> Fail B4+
      </span>
      <span style={{ color: "var(--faint)" }}>● Defect 위치</span>
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
    data.correlation < -0.5 ? "var(--c-red)" :
    data.correlation < -0.3 ? "var(--c-amber)" : "var(--c-green)";

  const avgYield = data.avg_yield_pct;

  return (
    <div className="trend-chart-container">
      {/* 헤더 */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0, fontSize: 14, color: "var(--sub)" }}>
          Defect–수율 이력 분석 — Lot: <strong style={{ color: "var(--ink)" }}>{data.lot_id}</strong>
          {"  "}|{"  "}<strong style={{ color: typeColor }}>{data.defect_type}</strong>
        </h3>
        <span style={{ fontSize: 11, color: "var(--faint)", marginLeft: "auto" }}>25 wafers</span>
      </div>

      {/* 통계 칩 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        {[
          { label: "상관계수 r", val: String(data.correlation), color: corrColor },
          { label: "판정",       val: corrLabel,                 color: corrColor },
          { label: "평균 수율",  val: `${data.avg_yield_pct}%`,  color: "var(--c-green)" },
          { label: "평균 Kill",  val: `${data.avg_kill_rate_pct}%`, color: data.avg_kill_rate_pct > 30 ? "var(--c-red)" : "var(--c-amber)" },
          { label: "고위험 슬롯", val: `${data.high_risk_wafers}개`, color: "var(--c-red)" },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ fontSize: 11, background: "var(--sunken)", border: `1px solid ${alpha(color, "44")}`, borderRadius: 6, padding: "2px 10px", color }}>
            {label}: <strong>{val}</strong>
          </div>
        ))}
      </div>

      {/* ── Section 1: Scatter (defect count vs yield) ── */}
      <div style={{ fontSize: 12, color: "var(--sub)", fontWeight: 600, marginBottom: 6 }}>
        Defect 건수 vs 수율 (전체 25 Wafer)
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 6, fontSize: 11, color: "var(--sub)" }}>
        {[["Kill ≥40%", "var(--c-red)"], ["Kill 20~40%", "var(--c-amber)"], ["Kill <20%", "var(--c-green)"]].map(([l, c]) => (
          <span key={l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: c as string, display: "inline-block" }} />{l}
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart margin={{ top: 4, right: 8, left: -10, bottom: 18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--sand)" />
          <XAxis
            type="number" dataKey="defect_count" name="Defect 수"
            tick={{ fontSize: 9, fill: "var(--faint)" }} tickLine={false}
            label={{ value: `${data.defect_type} 건수`, fill: "var(--faint)", fontSize: 10, position: "insideBottom", offset: -12 }}
          />
          <YAxis
            type="number" dataKey="yield_pct" name="수율 (%)"
            tick={{ fontSize: 9, fill: "var(--faint)" }} tickLine={false}
            domain={[Math.max(0, avgYield - 15), Math.min(100, avgYield + 10)]}
          />
          <Tooltip content={<ScatterTooltip />} cursor={{ stroke: "var(--line-strong)", strokeWidth: 1 }} />
          <ReferenceLine y={avgYield} stroke="var(--faint)" strokeDasharray="4 2" strokeWidth={1}
            label={{ value: `AVG ${avgYield}%`, fill: "var(--faint)", fontSize: 9, position: "insideTopRight" }} />
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
        <div style={{ fontSize: 12, color: "var(--sub)", fontWeight: 600, marginBottom: 8 }}>
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
        style={{ background: "none", border: `1px solid ${alpha(typeColor, "88")}`, color: typeColor, borderRadius: 6, padding: "3px 12px", fontSize: 11, cursor: "pointer", marginTop: 14, display: "flex", alignItems: "center", gap: 6 }}
      >
        <span>{showTable ? "▲" : "▼"}</span>
        전체 25 Wafer 상세 이력
      </button>

      {showTable && (
        <div style={{ maxHeight: 260, overflowY: "auto", borderRadius: 8, border: "1px solid var(--sand)", marginTop: 8 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0, background: "var(--sunken)", zIndex: 1 }}>
              <tr>
                {["Wafer", "Defect 수", "수율 %", "영향 Die", "Kill Die", "Kill Rate"].map((h) => (
                  <th key={h} style={{ padding: "6px 10px", color: "var(--faint)", textAlign: "left", fontWeight: 600, fontSize: 11, borderBottom: "1px solid var(--sand)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.wafers.map((w, i) => (
                <tr key={w.wafer_no} style={{ borderBottom: "1px solid var(--sunken)", background: i % 2 === 0 ? "transparent" : "var(--sunken)" }}>
                  <td style={{ padding: "5px 10px", color: "var(--sub)" }}>W{w.wafer_no}</td>
                  <td style={{ padding: "5px 10px", color: w.defect_count > 0 ? typeColor : "var(--faint)", fontWeight: w.defect_count > 0 ? 700 : 400 }}>{w.defect_count}</td>
                  <td style={{ padding: "5px 10px", color: "var(--c-green)" }}>{w.yield_pct}%</td>
                  <td style={{ padding: "5px 10px", color: "var(--sub)" }}>{w.dies_affected}</td>
                  <td style={{ padding: "5px 10px", color: "var(--c-red)" }}>{w.killed_dies}</td>
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
