import React, { useState, useMemo } from "react";
import { WaferMapPayload } from "../types";

// SVG layout constants
const CX = 150;        // wafer center X
const CY = 155;        // wafer center Y
const WAFER_R = 138;   // wafer radius in px
const GRID = 20;       // 20×20 die grid
const DIE_PX = 13;     // px per die
// Grid starts so that center of grid aligns with (CX, CY)
const START = CX - (GRID / 2) * DIE_PX; // = 150 - 130 = 20

/** Map thickness value to HSL color: red=thick, green=nominal, blue=thin */
function toColor(v: number, min: number, max: number): string {
  const t = max > min ? (v - min) / (max - min) : 0.5;
  const hue = Math.round(240 - t * 240); // 240(blue) → 0(red)
  return `hsl(${hue},88%,52%)`;
}

interface Props {
  data: WaferMapPayload;
}

export default function WaferMap({ data }: Props) {
  const [sel, setSel] = useState(0);
  const wafer = data.wafers[sel];

  const { tMin, tMax } = useMemo(() => {
    const vals = wafer.dies.map((d) => d.thickness);
    return { tMin: Math.min(...vals), tMax: Math.max(...vals) };
  }, [wafer]);

  const tMid = ((tMin + tMax) / 2).toFixed(0);
  const gradId = `grad-${data.lot_id}`;
  const clipId = `clip-${data.lot_id}`;
  const bgId   = `bg-${data.lot_id}`;

  return (
    <div className="wafer-map-container">
      <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#94a3b8" }}>
        Wafer Map — Lot:{" "}
        <strong style={{ color: "#e2e8f0" }}>{data.lot_id}</strong>
        {"  "}|{"  "}Avg Thickness:{" "}
        <strong style={{ color: "#38bdf8" }}>{wafer.avg_thickness} Å</strong>
      </h3>

      {/* Wafer selector tabs */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 10 }}>
        {data.wafers.map((w, i) => (
          <button
            key={w.wafer_no}
            onClick={() => setSel(i)}
            style={{
              padding: "2px 8px",
              fontSize: 11,
              borderRadius: 4,
              border: "1px solid",
              cursor: "pointer",
              background: sel === i ? "#3b82f6" : "transparent",
              borderColor: sel === i ? "#3b82f6" : "#475569",
              color: sel === i ? "#fff" : "#94a3b8",
            }}
          >
            W{w.wafer_no}
          </button>
        ))}
      </div>

      {/* SVG wafer with thickness heatmap */}
      <svg
        viewBox="0 0 370 320"
        style={{ width: "100%", maxWidth: 420, display: "block" }}
      >
        <defs>
          {/* Clip to wafer circle */}
          <clipPath id={clipId}>
            <circle cx={CX} cy={CY} r={WAFER_R - 1} />
          </clipPath>

          {/* Subtle radial background for silicon look */}
          <radialGradient id={bgId} cx="38%" cy="32%">
            <stop offset="0%" stopColor="#252545" />
            <stop offset="100%" stopColor="#0c0c1e" />
          </radialGradient>

          {/* Color scale gradient: top=red(thick), bottom=blue(thin) */}
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="hsl(0,88%,52%)"   />
            <stop offset="50%"  stopColor="hsl(120,70%,42%)" />
            <stop offset="100%" stopColor="hsl(240,88%,58%)" />
          </linearGradient>
        </defs>

        {/* Wafer base circle */}
        <circle
          cx={CX} cy={CY} r={WAFER_R}
          fill={`url(#${bgId})`}
          stroke="#475569"
          strokeWidth={2}
        />

        {/* Die heatmap — clipped to circle */}
        <g clipPath={`url(#${clipId})`}>
          {wafer.dies.map((die) => (
            <rect
              key={`${die.row}-${die.col}`}
              x={START + die.col * DIE_PX + 0.5}
              y={START + die.row * DIE_PX + 0.5}
              width={DIE_PX - 1}
              height={DIE_PX - 1}
              fill={toColor(die.thickness, tMin, tMax)}
              opacity={0.9}
            >
              <title>{`R${die.row} C${die.col}: ${die.thickness} Å`}</title>
            </rect>
          ))}
        </g>

        {/* Wafer outline */}
        <circle
          cx={CX} cy={CY} r={WAFER_R}
          fill="none"
          stroke="#94a3b8"
          strokeWidth={1.5}
        />

        {/* Notch at 6 o'clock */}
        <path
          d={`M ${CX - 9} ${CY + WAFER_R + 1}
              Q ${CX} ${CY + WAFER_R - 6}
              ${CX + 9} ${CY + WAFER_R + 1}`}
          fill="#0a0a18"
          stroke="#94a3b8"
          strokeWidth={1}
        />

        {/* ── Color scale bar ── */}
        {/* Bar */}
        <rect x={305} y={25} width={20} height={250} fill={`url(#${gradId})`} rx={3} />
        {/* Tick lines */}
        <line x1={305} y1={25}  x2={301} y2={25}  stroke="#64748b" strokeWidth={1} />
        <line x1={305} y1={150} x2={301} y2={150} stroke="#64748b" strokeWidth={1} />
        <line x1={305} y1={275} x2={301} y2={275} stroke="#64748b" strokeWidth={1} />
        {/* Labels */}
        <text x={298} y={25}  textAnchor="end" dominantBaseline="middle" fill="#e2e8f0" fontSize={10}>
          {tMax.toFixed(0)}
        </text>
        <text x={298} y={150} textAnchor="end" dominantBaseline="middle" fill="#e2e8f0" fontSize={10}>
          {tMid}
        </text>
        <text x={298} y={275} textAnchor="end" dominantBaseline="middle" fill="#e2e8f0" fontSize={10}>
          {tMin.toFixed(0)}
        </text>
        {/* Unit label */}
        <text x={315} y={285} textAnchor="middle" fill="#64748b" fontSize={9}>Å</text>
        {/* Thick / Thin */}
        <text x={315} y={14}  textAnchor="middle" fill="#94a3b8" fontSize={9}>Thick</text>
        <text x={315} y={295} textAnchor="middle" fill="#94a3b8" fontSize={9}>Thin</text>
      </svg>
    </div>
  );
}
