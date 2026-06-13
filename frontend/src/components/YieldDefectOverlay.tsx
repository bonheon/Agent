import React from "react";
import { YieldDefectPayload } from "../types";

const CX = 150, CY = 155, R = 133;
const GRID = 20, DIE_PX = 13, START = CX - (GRID / 2) * DIE_PX;

const DEFECT_COLORS: Record<string, string> = {
  PARTICLE: "#f59e0b", SCRATCH: "#ef4444", BRIDGE: "#a855f7",
  PIT: "#3b82f6",      RESIDUE: "#22c55e", CLUSTER: "#ec4899",
};

function binColor(bin: number): string {
  if (bin === 1) return "#15803d";   // pass — green
  if (bin === 2) return "#ef4444";   // fail bin 2 — red
  if (bin === 3) return "#f97316";   // fail bin 3 — orange
  return "#a855f7";                  // fail bin 4+ — purple
}

interface Props {
  data: YieldDefectPayload;
}

export default function YieldDefectOverlay({ data }: Props) {
  return (
    <div className="wafer-map-container">
      <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#94a3b8" }}>
        Yield + Defect — Lot: <strong style={{ color: "#e2e8f0" }}>{data.lot_id}</strong>
        {"  "}| Wafer <strong style={{ color: "#e2e8f0" }}>{data.wafer_no}</strong>
        {"  "}
        <strong style={{ color: "#22c55e" }}>Yield: {data.wafer_yield_pct}%</strong>
      </h3>

      {/* 범례 */}
      <div style={{ display: "flex", gap: 12, marginBottom: 10, flexWrap: "wrap", fontSize: 11 }}>
        {[["Pass", "#15803d"], ["Fail B2", "#ef4444"], ["Fail B3", "#f97316"], ["Fail B4+", "#a855f7"]].map(
          ([label, color]) => (
            <span key={label} style={{ display: "flex", alignItems: "center", gap: 4, color: "#94a3b8" }}>
              <span style={{ width: 10, height: 10, background: color, display: "inline-block", borderRadius: 2 }} />
              {label}
            </span>
          )
        )}
        <span style={{ color: "#64748b" }}>● Defect (클릭 불가, 위치 참고용)</span>
      </div>

      <svg viewBox="0 0 370 330" style={{ width: "100%", maxWidth: 420, display: "block" }}>
        <defs>
          <clipPath id="yd-clip"><circle cx={CX} cy={CY} r={R - 1} /></clipPath>
        </defs>

        {/* Wafer base */}
        <circle cx={CX} cy={CY} r={R} fill="#0a0a18" stroke="#475569" strokeWidth={2} />

        {/* Die bins */}
        <g clipPath="url(#yd-clip)">
          {data.dies.map((die) => (
            <rect
              key={`${die.row}-${die.col}`}
              x={START + die.col * DIE_PX + 0.5}
              y={START + die.row * DIE_PX + 0.5}
              width={DIE_PX - 1}
              height={DIE_PX - 1}
              fill={binColor(die.bin)}
              opacity={0.85}
            >
              <title>{die.pass ? "PASS" : `FAIL Bin${die.bin}`}{die.defect_count > 0 ? ` | ${die.defect_types.join(",")}` : ""}</title>
            </rect>
          ))}
        </g>

        {/* Defect overlay dots */}
        {data.defects.map((d) => {
          const svgX = CX + d.x_norm * R;
          const svgY = CY - d.y_norm * R;
          return (
            <circle
              key={d.defect_id}
              cx={svgX} cy={svgY}
              r={3}
              fill={DEFECT_COLORS[d.defect_type] ?? "#fff"}
              stroke="#000"
              strokeWidth={0.5}
              opacity={0.9}
            >
              <title>{d.defect_type} | {d.size_um}μm</title>
            </circle>
          );
        })}

        {/* Wafer outline + notch */}
        <circle cx={CX} cy={CY} r={R} fill="none" stroke="#94a3b8" strokeWidth={1.5} />
        <path d={`M ${CX-8} ${CY+R+1} Q ${CX} ${CY+R-5} ${CX+8} ${CY+R+1}`} fill="#0a0a18" stroke="#94a3b8" strokeWidth={1} />

        {/* Yield text */}
        <text x={305} y={30} fill="#e2e8f0" fontSize={11} textAnchor="start" fontWeight={600}>{data.wafer_yield_pct}%</text>
        <text x={305} y={44} fill="#64748b" fontSize={9} textAnchor="start">Yield</text>
        <text x={305} y={62} fill="#e2e8f0" fontSize={11} textAnchor="start">{data.defects.length}</text>
        <text x={305} y={76} fill="#64748b" fontSize={9} textAnchor="start">Defects</text>
      </svg>

      {/* Chip Kill 분석 테이블 */}
      {data.kill_analysis.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600, marginBottom: 8 }}>
            Chip Kill 분석
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #334155" }}>
                  {["Defect 유형", "영향 Die", "Kill Die", "Kill Rate"].map((h) => (
                    <th key={h} style={{ padding: "5px 10px", color: "#64748b", textAlign: "left", fontSize: 11 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.kill_analysis
                  .sort((a, b) => b.kill_rate_pct - a.kill_rate_pct)
                  .map((row, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                      <td style={{ padding: "5px 10px" }}>
                        <span style={{ color: DEFECT_COLORS[row.defect_type] ?? "#e2e8f0", fontWeight: 600 }}>
                          {row.defect_type}
                        </span>
                      </td>
                      <td style={{ padding: "5px 10px", color: "#94a3b8" }}>{row.dies_affected}</td>
                      <td style={{ padding: "5px 10px", color: "#ef4444" }}>{row.killed_dies}</td>
                      <td style={{ padding: "5px 10px" }}>
                        <span
                          style={{
                            background: row.kill_rate_pct > 40 ? "#3f0f0f" : row.kill_rate_pct > 20 ? "#3f2a00" : "#0f2a0f",
                            color:      row.kill_rate_pct > 40 ? "#f87171" : row.kill_rate_pct > 20 ? "#fbbf24" : "#4ade80",
                            borderRadius: 4, padding: "1px 7px", fontWeight: 600,
                          }}
                        >
                          {row.kill_rate_pct}%
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
