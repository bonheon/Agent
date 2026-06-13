import React, { useState } from "react";
import { DefectMapPayload, DefectPoint } from "../types";

const CX = 150, CY = 150, R = 133;

const DEFECT_COLORS: Record<string, string> = {
  PARTICLE: "#f59e0b",
  SCRATCH:  "#ef4444",
  BRIDGE:   "#a855f7",
  PIT:      "#3b82f6",
  RESIDUE:  "#22c55e",
  CLUSTER:  "#ec4899",
};

interface ReviewState {
  defect: DefectPoint;
  image: string | null;
  loading: boolean;
  x_mm: number;
  y_mm: number;
}

interface Props {
  data: DefectMapPayload;
}

export default function DefectMap({ data }: Props) {
  const [activeTypes, setActiveTypes] = useState<Set<string>>(
    new Set(Object.keys(data.type_counts))
  );
  const [review, setReview] = useState<ReviewState | null>(null);

  const toggleType = (type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      next.has(type) ? next.delete(type) : next.add(type);
      return next;
    });
  };

  const handleClick = async (defect: DefectPoint) => {
    setReview({ defect, image: null, loading: true, x_mm: 0, y_mm: 0 });
    try {
      const res = await fetch(
        `/api/chart/defect-review?lot_id=${data.lot_id}&wafer_no=${data.wafer_no}&defect_id=${defect.defect_id}`
      );
      const d = await res.json();
      setReview({ defect, image: d.review_image, loading: false, x_mm: d.x_mm, y_mm: d.y_mm });
    } catch {
      setReview({ defect, image: null, loading: false, x_mm: 0, y_mm: 0 });
    }
  };

  const visible = data.defects.filter((d) => activeTypes.has(d.defect_type));

  return (
    <div className="wafer-map-container">
      <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#94a3b8" }}>
        Defect Map — Lot: <strong style={{ color: "#e2e8f0" }}>{data.lot_id}</strong>
        {"  "}| Wafer <strong style={{ color: "#e2e8f0" }}>{data.wafer_no}</strong>
        {"  "}
        <span style={{ color: "#ef4444" }}>Total: {data.defects.length}</span>
      </h3>

      {/* Filter chips */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {Object.entries(data.type_counts)
          .sort((a, b) => b[1] - a[1])
          .map(([type, count]) => {
            const color = DEFECT_COLORS[type] ?? "#888";
            const active = activeTypes.has(type);
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                style={{
                  padding: "3px 11px",
                  borderRadius: 12,
                  border: `1px solid ${color}`,
                  background: active ? color + "28" : "transparent",
                  color: active ? color : "#64748b",
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: active ? 600 : 400,
                  transition: "all 0.15s",
                }}
              >
                ● {type} ({count})
              </button>
            );
          })}
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* SVG Wafer */}
        <svg
          viewBox="0 0 300 310"
          style={{ width: "100%", maxWidth: 300, flexShrink: 0, cursor: "crosshair" }}
        >
          <defs>
            <radialGradient id="dm-bg" cx="38%" cy="32%">
              <stop offset="0%" stopColor="#252545" />
              <stop offset="100%" stopColor="#0c0c1e" />
            </radialGradient>
            <clipPath id="dm-clip">
              <circle cx={CX} cy={CY} r={R - 1} />
            </clipPath>
          </defs>

          {/* Wafer base */}
          <circle cx={CX} cy={CY} r={R} fill="url(#dm-bg)" stroke="#475569" strokeWidth={2} />

          {/* Die grid (faint) */}
          <g clipPath="url(#dm-clip)" opacity={0.15}>
            {Array.from({ length: 20 }, (_, i) => (
              <React.Fragment key={i}>
                <line x1={20 + i * 13} y1={20} x2={20 + i * 13} y2={280} stroke="#fff" strokeWidth={0.3} />
                <line x1={20} y1={20 + i * 13} x2={280} y2={20 + i * 13} stroke="#fff" strokeWidth={0.3} />
              </React.Fragment>
            ))}
          </g>

          {/* Defect dots */}
          {visible.map((d) => {
            const svgX = CX + d.x_norm * R;
            const svgY = CY - d.y_norm * R;
            const isSelected = review?.defect.defect_id === d.defect_id;
            const color = DEFECT_COLORS[d.defect_type] ?? "#888";
            const dotR = Math.max(3, Math.min(d.size_um * 1.8, 9));
            return (
              <g key={d.defect_id} onClick={() => handleClick(d)} style={{ cursor: "pointer" }}>
                {isSelected && (
                  <circle cx={svgX} cy={svgY} r={dotR + 5} fill="none" stroke="#fff" strokeWidth={1.5} opacity={0.7} />
                )}
                <circle
                  cx={svgX} cy={svgY} r={dotR}
                  fill={color}
                  opacity={isSelected ? 1 : 0.75}
                  stroke={isSelected ? "#fff" : color}
                  strokeWidth={isSelected ? 1 : 0.5}
                >
                  <title>{d.defect_type} | {d.size_um}μm | Die R{d.die_row} C{d.die_col}</title>
                </circle>
              </g>
            );
          })}

          {/* Wafer outline + notch */}
          <circle cx={CX} cy={CY} r={R} fill="none" stroke="#94a3b8" strokeWidth={1.5} />
          <path d={`M ${CX-8} ${CY+R+1} Q ${CX} ${CY+R-5} ${CX+8} ${CY+R+1}`} fill="#0a0a18" stroke="#94a3b8" strokeWidth={1} />
        </svg>

        {/* Review panel */}
        {review && (
          <div
            style={{
              flex: 1,
              minWidth: 180,
              maxWidth: 240,
              background: "#0f172a",
              borderRadius: 10,
              border: `1px solid ${DEFECT_COLORS[review.defect.defect_type] ?? "#334155"}44`,
              padding: 14,
            }}
          >
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>
              Review Image
              <span
                onClick={() => setReview(null)}
                style={{ float: "right", cursor: "pointer", color: "#475569" }}
              >
                ✕
              </span>
            </div>

            {review.loading ? (
              <div style={{ color: "#64748b", fontSize: 12 }}>Loading...</div>
            ) : review.image ? (
              <img
                src={review.image}
                alt="review"
                style={{ width: "100%", borderRadius: 8, marginBottom: 10, display: "block" }}
              />
            ) : null}

            {/* Defect info */}
            <div style={{ fontSize: 12, lineHeight: 2 }}>
              {[
                ["ID",    review.defect.defect_id],
                ["Type",  review.defect.defect_type],
                ["Size",  `${review.defect.size_um} μm`],
                ["Die",   `R${review.defect.die_row} C${review.defect.die_col}`],
                ["Pos",   `(${review.x_mm}, ${review.y_mm}) mm`],
              ].map(([label, val]) => (
                <div key={label}>
                  <span style={{ color: "#64748b", display: "inline-block", width: 36 }}>{label}</span>
                  <span
                    style={{
                      color: label === "Type"
                        ? (DEFECT_COLORS[val] ?? "#e2e8f0")
                        : "#e2e8f0",
                      fontWeight: label === "Type" ? 700 : 400,
                    }}
                  >
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {!review && (
        <div style={{ marginTop: 8, fontSize: 11, color: "#475569" }}>
          ↑ 점을 클릭하면 Review Image를 볼 수 있습니다
        </div>
      )}
    </div>
  );
}
