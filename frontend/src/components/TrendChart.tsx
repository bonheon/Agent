import React, { useState } from "react";
import { alpha } from "../lib/color";
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
        background: "var(--sand)",
        border: `1px solid ${d.ooc ? "var(--c-red)" : "var(--faint)"}`,
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 12,
        lineHeight: 1.8,
      }}
    >
      <div style={{ color: "var(--sub)" }}>
        Lot: <strong style={{ color: "var(--ink)" }}>{d.lot_id}</strong>
      </div>
      <div style={{ color: "var(--sub)" }}>
        Slot: <strong style={{ color: "var(--ink)" }}>{d.slot}</strong>
      </div>
      <div style={{ color: "var(--sub)" }}>
        Value:{" "}
        <strong style={{ color: d.ooc ? "var(--c-red)" : "var(--c-sky)" }}>
          {d.value.toFixed(2)}
        </strong>
      </div>
      {d.ooc && (
        <div style={{ color: "var(--c-red)", fontSize: 11, marginTop: 2 }}>
          ⚠ OUT OF CONTROL
        </div>
      )}
    </div>
  );
}

function CustomLegend({ oocCount, normalCount }: { oocCount: number; normalCount: number }) {
  return (
    <div style={{ display: "flex", gap: 16, justifyContent: "center", fontSize: 12, color: "var(--sub)", marginBottom: 4 }}>
      <span>
        <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "var(--c-sky)", marginRight: 5 }} />
        Normal ({normalCount})
      </span>
      <span>
        <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "var(--c-red)", marginRight: 5 }} />
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
        <h3 style={{ margin: 0, fontSize: 14, color: "var(--sub)" }}>
          Trend — Lot:{" "}
          <strong style={{ color: "var(--ink)" }}>{lotId}</strong>
          {"  "}|{"  "}
          <strong style={{ color: "var(--ink)" }}>{METRIC_LABEL[metric] ?? metric}</strong>
        </h3>
        <span style={{ fontSize: 12, color: "var(--c-red)", background: "var(--err-soft)", borderRadius: 4, padding: "1px 8px" }}>
          OOC {oocPoints.length}건 ({oocRate}%)
        </span>
        <span style={{ fontSize: 11, color: "var(--faint)", marginLeft: "auto" }}>
          n = {data.points.length}
        </span>
      </div>

      {/* SPC 통계 칩 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        {[
          { label: "AVG", val: data.avg.toFixed(2), color: "var(--faint)" },
          { label: "UCL", val: data.ucl.toFixed(2), color: "var(--c-amber)" },
          { label: "LCL", val: data.lcl.toFixed(2), color: "var(--c-amber)" },
          { label: "3σ",  val: ((data.ucl - data.avg) / 3).toFixed(2), color: "var(--c-purple)" },
        ].map(({ label, val, color }) => (
          <div
            key={label}
            style={{
              fontSize: 11,
              background: "var(--sunken)",
              border: `1px solid ${alpha(color, "44")}`,
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
          <CartesianGrid strokeDasharray="3 3" stroke="var(--sand)" />
          <XAxis
            type="number"
            dataKey="index"
            name="Measurement"
            tick={{ fontSize: 9, fill: "var(--faint)" }}
            tickLine={false}
            label={{ value: "Measurement #", fill: "var(--faint)", fontSize: 10, position: "insideBottom", offset: -10 }}
          />
          <YAxis
            type="number"
            dataKey="value"
            name="Value"
            tick={{ fontSize: 9, fill: "var(--faint)" }}
            tickLine={false}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "var(--line-strong)", strokeWidth: 1 }} />

          {/* Control limit lines */}
          <ReferenceLine
            y={data.ucl}
            stroke="var(--c-amber)"
            strokeDasharray="6 3"
            strokeWidth={1.5}
            label={{ value: `UCL ${data.ucl.toFixed(1)}`, fill: "var(--c-amber)", fontSize: 9, position: "insideTopRight" }}
          />
          <ReferenceLine
            y={data.avg}
            stroke="var(--faint)"
            strokeDasharray="4 2"
            strokeWidth={1}
            label={{ value: `AVG`, fill: "var(--faint)", fontSize: 9, position: "insideTopRight" }}
          />
          <ReferenceLine
            y={data.lcl}
            stroke="var(--c-amber)"
            strokeDasharray="6 3"
            strokeWidth={1.5}
            label={{ value: `LCL ${data.lcl.toFixed(1)}`, fill: "var(--c-amber)", fontSize: 9, position: "insideBottomRight" }}
          />

          {/* Normal points — small, semi-transparent */}
          <Scatter
            name="Normal"
            data={normalPoints}
            fill="var(--c-sky)"
            opacity={0.45}
            isAnimationActive={false}
            shape={(props: any) => (
              <circle cx={props.cx} cy={props.cy} r={2} fill="var(--c-sky)" opacity={0.45} />
            )}
          />

          {/* OOC points — larger, solid red */}
          <Scatter
            name="OOC"
            data={oocPoints}
            fill="var(--c-red)"
            opacity={1}
            isAnimationActive={false}
            shape={(props: any) => (
              <circle cx={props.cx} cy={props.cy} r={4} fill="var(--c-red)" stroke="var(--err)" strokeWidth={1} />
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
              border: "1px solid color-mix(in srgb, var(--c-red) 53%, transparent)",
              color: "var(--c-red)",
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
            <div style={{ maxHeight: 240, overflowY: "auto", borderRadius: 8, border: "1px solid var(--sand)" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead style={{ position: "sticky", top: 0, background: "var(--sunken)", zIndex: 1 }}>
                  <tr>
                    {["#", "Lot ID", "Slot", "Value", "편차", "판정"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          color: "var(--faint)",
                          textAlign: "left",
                          fontWeight: 600,
                          fontSize: 11,
                          borderBottom: "1px solid var(--sand)",
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
                          borderBottom: "1px solid var(--sunken)",
                          background: i % 2 === 0 ? "transparent" : "var(--sunken)",
                        }}
                      >
                        <td style={{ padding: "5px 10px", color: "var(--faint)", fontSize: 10 }}>{i + 1}</td>
                        <td style={{ padding: "5px 10px", color: "var(--ink)", fontFamily: "monospace" }}>{p.lot_id}</td>
                        <td style={{ padding: "5px 10px", color: "var(--sub)" }}>W{p.slot}</td>
                        <td style={{ padding: "5px 10px", color: "var(--c-red)", fontWeight: 700 }}>
                          {p.value.toFixed(2)}
                        </td>
                        <td
                          style={{
                            padding: "5px 10px",
                            color: isHigh ? "var(--err)" : "var(--c-sky)",
                            fontWeight: 600,
                          }}
                        >
                          {dev > 0 ? "+" : ""}{dev.toFixed(2)}
                        </td>
                        <td style={{ padding: "5px 10px" }}>
                          <span
                            style={{
                              background: isHigh ? "var(--err-soft)" : "var(--c-blue-soft)",
                              color: isHigh ? "var(--err)" : "var(--c-sky)",
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
