import React, { useState } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { TrendPayload, TrendPoint } from "../types";

interface Props {
  data: TrendPayload;
  lotId: string;
  metric: string;
}

const METRIC_LABEL: Record<string, string> = {
  thickness:      "Thickness (Å)",
  cd:             "CD (nm)",
  particle_count: "Particle Count",
  PARTICLE:  "PARTICLE Defect Count",
  SCRATCH:   "SCRATCH Defect Count",
  BRIDGE:    "BRIDGE Defect Count",
  PIT:       "PIT Defect Count",
  RESIDUE:   "RESIDUE Defect Count",
  CLUSTER:   "CLUSTER Defect Count",
};

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d: TrendPoint = payload[0]?.payload;
  if (!d) return null;
  return (
    <div
      style={{
        background: "#1e293b",
        border: `1px solid ${d.ooc ? "#ef4444" : "#475569"}`,
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 12,
        lineHeight: 1.8,
      }}
    >
      <div style={{ color: "#94a3b8" }}>
        Lot: <strong style={{ color: "#e2e8f0" }}>{d.lot_id}</strong>
      </div>
      <div style={{ color: "#94a3b8" }}>
        Slot: <strong style={{ color: "#e2e8f0" }}>{d.slot}</strong>
      </div>
      <div style={{ color: "#94a3b8" }}>
        Value:{" "}
        <strong style={{ color: d.ooc ? "#ef4444" : "#38bdf8" }}>
          {d.value.toFixed(2)}
        </strong>
      </div>
      {d.ooc && (
        <div style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
          ⚠ OUT OF CONTROL
        </div>
      )}
    </div>
  );
}

function CustomLegend({ oocCount, normalCount }: { oocCount: number; normalCount: number }) {
  return (
    <div style={{ display: "flex", gap: 16, justifyContent: "center", fontSize: 12, color: "#94a3b8", marginBottom: 4 }}>
      <span>
        <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#38bdf8", marginRight: 5 }} />
        Normal ({normalCount})
      </span>
      <span>
        <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#ef4444", marginRight: 5 }} />
        OOC ({oocCount})
      </span>
    </div>
  );
}

export default function TrendChart({ data, lotId, metric }: Props) {
  const [showTable, setShowTable] = useState(true);

  const normalPoints = data.points.filter((p) => !p.ooc);
  const oocPoints    = data.points.filter((p) =>  p.ooc);
  const oocRate      = ((oocPoints.length / data.points.length) * 100).toFixed(1);

  return (
    <div className="trend-chart-container">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0, fontSize: 14, color: "#94a3b8" }}>
          Trend — Lot:{" "}
          <strong style={{ color: "#e2e8f0" }}>{lotId}</strong>
          {"  "}|{"  "}
          <strong style={{ color: "#e2e8f0" }}>{METRIC_LABEL[metric] ?? metric}</strong>
        </h3>
        <span style={{ fontSize: 12, color: "#ef4444", background: "#3f1010", borderRadius: 4, padding: "1px 8px" }}>
          OOC {oocPoints.length}건 ({oocRate}%)
        </span>
        <span style={{ fontSize: 11, color: "#64748b", marginLeft: "auto" }}>
          n = {data.points.length}
        </span>
      </div>

      {/* SPC 통계 칩 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        {[
          { label: "AVG", val: data.avg.toFixed(2), color: "#64748b" },
          { label: "UCL", val: data.ucl.toFixed(2), color: "#f59e0b" },
          { label: "LCL", val: data.lcl.toFixed(2), color: "#f59e0b" },
          { label: "3σ",  val: ((data.ucl - data.avg) / 3).toFixed(2), color: "#8b5cf6" },
        ].map(({ label, val, color }) => (
          <div
            key={label}
            style={{
              fontSize: 11,
              background: "#0f172a",
              border: `1px solid ${color}44`,
              borderRadius: 6,
              padding: "2px 10px",
              color,
            }}
          >
            {label}: <strong>{val}</strong>
          </div>
        ))}
      </div>

      <CustomLegend oocCount={oocPoints.length} normalCount={normalPoints.length} />

      {/* Scatter Plot */}
      <ResponsiveContainer width="100%" height={230}>
        <ScatterChart margin={{ top: 4, right: 8, left: -10, bottom: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            type="number"
            dataKey="index"
            name="Measurement"
            tick={{ fontSize: 9, fill: "#64748b" }}
            tickLine={false}
            label={{ value: "Measurement #", fill: "#475569", fontSize: 10, position: "insideBottom", offset: -10 }}
          />
          <YAxis
            type="number"
            dataKey="value"
            name="Value"
            tick={{ fontSize: 9, fill: "#64748b" }}
            tickLine={false}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#334155", strokeWidth: 1 }} />

          {/* Control limit lines */}
          <ReferenceLine
            y={data.ucl}
            stroke="#f59e0b"
            strokeDasharray="6 3"
            strokeWidth={1.5}
            label={{ value: `UCL ${data.ucl.toFixed(1)}`, fill: "#f59e0b", fontSize: 9, position: "insideTopRight" }}
          />
          <ReferenceLine
            y={data.avg}
            stroke="#475569"
            strokeDasharray="4 2"
            strokeWidth={1}
            label={{ value: `AVG`, fill: "#64748b", fontSize: 9, position: "insideTopRight" }}
          />
          <ReferenceLine
            y={data.lcl}
            stroke="#f59e0b"
            strokeDasharray="6 3"
            strokeWidth={1.5}
            label={{ value: `LCL ${data.lcl.toFixed(1)}`, fill: "#f59e0b", fontSize: 9, position: "insideBottomRight" }}
          />

          {/* Normal points — small, semi-transparent */}
          <Scatter
            name="Normal"
            data={normalPoints}
            fill="#38bdf8"
            opacity={0.45}
            isAnimationActive={false}
            shape={(props: any) => (
              <circle cx={props.cx} cy={props.cy} r={2} fill="#38bdf8" opacity={0.45} />
            )}
          />

          {/* OOC points — larger, solid red */}
          <Scatter
            name="OOC"
            data={oocPoints}
            fill="#ef4444"
            opacity={1}
            isAnimationActive={false}
            shape={(props: any) => (
              <circle cx={props.cx} cy={props.cy} r={4} fill="#ef4444" stroke="#fca5a5" strokeWidth={1} />
            )}
          />
        </ScatterChart>
      </ResponsiveContainer>

      {/* OOC Slot 상세 테이블 */}
      {oocPoints.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <button
            onClick={() => setShowTable((s) => !s)}
            style={{
              background: "none",
              border: "1px solid #ef444488",
              color: "#ef4444",
              borderRadius: 6,
              padding: "3px 12px",
              fontSize: 11,
              cursor: "pointer",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span>{showTable ? "▲" : "▼"}</span>
            OOC Slot 상세 목록 ({oocPoints.length}건)
          </button>

          {showTable && (
            <div style={{ maxHeight: 240, overflowY: "auto", borderRadius: 8, border: "1px solid #1e293b" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead style={{ position: "sticky", top: 0, background: "#0f172a", zIndex: 1 }}>
                  <tr>
                    {["#", "Lot ID", "Slot", "Value", "편차", "판정"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          color: "#64748b",
                          textAlign: "left",
                          fontWeight: 600,
                          fontSize: 11,
                          borderBottom: "1px solid #1e293b",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {oocPoints.map((p, i) => {
                    const dev = p.value - data.avg;
                    const isHigh = p.value > data.ucl;
                    return (
                      <tr
                        key={i}
                        style={{
                          borderBottom: "1px solid #1e2940",
                          background: i % 2 === 0 ? "transparent" : "#0d1525",
                        }}
                      >
                        <td style={{ padding: "5px 10px", color: "#475569", fontSize: 10 }}>{i + 1}</td>
                        <td style={{ padding: "5px 10px", color: "#e2e8f0", fontFamily: "monospace" }}>{p.lot_id}</td>
                        <td style={{ padding: "5px 10px", color: "#94a3b8" }}>W{p.slot}</td>
                        <td style={{ padding: "5px 10px", color: "#ef4444", fontWeight: 700 }}>
                          {p.value.toFixed(2)}
                        </td>
                        <td
                          style={{
                            padding: "5px 10px",
                            color: isHigh ? "#f87171" : "#60a5fa",
                            fontWeight: 600,
                          }}
                        >
                          {dev > 0 ? "+" : ""}{dev.toFixed(2)}
                        </td>
                        <td style={{ padding: "5px 10px" }}>
                          <span
                            style={{
                              background: isHigh ? "#3f0f0f" : "#0f1f3f",
                              color: isHigh ? "#f87171" : "#60a5fa",
                              fontSize: 10,
                              borderRadius: 4,
                              padding: "1px 6px",
                            }}
                          >
                            {isHigh ? "HIGH" : "LOW"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
