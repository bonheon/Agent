import React, { useEffect, useState } from "react";
import { DefectStepOverlayPayload, ProcessStep, StepDefectPoint, CarryoverCluster } from "../types";

const CX = 150, CY = 150, R = 133;

// Step별 색상 (order 1~4)
const STEP_COLORS = ["#60a5fa", "#fbbf24", "#34d399", "#f87171"];
// 현재 step(4번째)은 더 진하게
const STEP_COLORS_BRIGHT = ["#93c5fd", "#fde68a", "#6ee7b7", "#fca5a5"];

function stepColor(order: number, bright = false): string {
  const arr = bright ? STEP_COLORS_BRIGHT : STEP_COLORS;
  return arr[(order - 1) % arr.length];
}

// SVG 마커 — step별 다른 모양 + 색상 적용
function Marker({
  shape, cx, cy, r, fill, stroke, opacity = 0.85,
}: {
  shape: number; cx: number; cy: number; r: number;
  fill: string; stroke: string; opacity?: number;
}) {
  const style = { fill, stroke, strokeWidth: 0.8, opacity };
  if (shape === 1) return <circle cx={cx} cy={cy} r={r} {...style} />;
  if (shape === 2) {
    const pts = `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`;
    return <polygon points={pts} {...style} />;
  }
  if (shape === 3) {
    const h = r * 1.1;
    const pts = `${cx},${cy - h} ${cx + r},${cy + r * 0.6} ${cx - r},${cy + r * 0.6}`;
    return <polygon points={pts} {...style} />;
  }
  // shape 4: current step — circle
  return <circle cx={cx} cy={cy} r={r} {...style} />;
}

// Legend용 작은 마커 (fill 없이 stroke만)
function MarkerPath({ shape, cx, cy, r }: { shape: number; cx: number; cy: number; r: number }) {
  if (shape === 2) {
    const pts = `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`;
    return <polygon points={pts} fill="currentColor" />;
  }
  if (shape === 3) {
    const h = r * 1.1;
    const pts = `${cx},${cy - h} ${cx + r},${cy + r * 0.6} ${cx - r},${cy + r * 0.6}`;
    return <polygon points={pts} fill="currentColor" />;
  }
  return <circle cx={cx} cy={cy} r={r} fill="currentColor" />;
}

interface ClickedState {
  defect: StepDefectPoint;
  step: ProcessStep;
  cluster: CarryoverCluster | null;
}

interface Props {
  data: DefectStepOverlayPayload;
}

export default function DefectStepOverlay({ data }: Props) {
  const [activeSteps, setActiveSteps] = useState<Set<string>>(
    new Set(data.steps.map((s) => s.step_name))
  );
  const [carryoverOnly, setCarryoverOnly] = useState(false);
  const [showLines, setShowLines]         = useState(true);
  const [clicked, setClicked]             = useState<ClickedState | null>(null);

  // cluster lookup map: cluster_id → CarryoverCluster
  const clusterById = React.useMemo(() => {
    const m: Record<string, CarryoverCluster> = {};
    for (const c of data.carryover_clusters) m[c.cluster_id] = c;
    return m;
  }, [data.carryover_clusters]);

  // defect lookup map: (step_name, defect_id) → defect
  const defectByStepId = React.useMemo(() => {
    const m: Record<string, StepDefectPoint> = {};
    for (const step of data.steps) {
      for (const d of step.defects) {
        m[`${step.step_name}|${d.defect_id}`] = d;
      }
    }
    return m;
  }, [data.steps]);

  const toggleStep = (name: string) => {
    setActiveSteps((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  // 현재 클릭된 cluster의 defect 위치들 (연결선 그리기용)
  const clusterPositions: Array<{ x: number; y: number; stepOrder: number }> = React.useMemo(() => {
    if (!clicked?.cluster || !showLines) return [];
    const cl = clicked.cluster;
    const positions: Array<{ x: number; y: number; stepOrder: number }> = [];
    for (const step of data.steps) {
      const app = cl.appearances[step.step_name];
      if (!app) continue;
      const d = defectByStepId[`${step.step_name}|${app.defect_id}`];
      if (!d) continue;
      positions.push({
        x: CX + d.x_norm * R,
        y: CY - d.y_norm * R,
        stepOrder: step.step_order,
      });
    }
    return positions;
  }, [clicked, showLines, data.steps, defectByStepId]);

  // 하이라이트할 defect_id set
  const highlightedIds = React.useMemo(() => {
    if (!clicked?.cluster) return new Set<string>();
    const ids = new Set<string>();
    for (const app of Object.values(clicked.cluster.appearances)) {
      ids.add(app.defect_id);
    }
    return ids;
  }, [clicked]);

  return (
    <div
      style={{
        background: "#0f172a",
        border: "1px solid #334155",
        borderRadius: 12,
        padding: 16,
        marginTop: 12,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9" }}>
            Step 간 Defect Overlay
          </span>
          <span style={{ fontSize: 11, color: "#64748b", marginLeft: 10 }}>
            Lot: <strong style={{ color: "#e2e8f0" }}>{data.lot_id}</strong>
            {"  "}Wafer <strong style={{ color: "#e2e8f0" }}>{data.wafer_no}</strong>
          </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, color: "#94a3b8" }}>
            Carryover: <strong style={{ color: "#f59e0b" }}>{data.carryover_clusters.length}건</strong>
          </span>
        </div>
      </div>

      {/* Step toggle buttons */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        {data.steps.map((step) => {
          const col   = stepColor(step.step_order);
          const active = activeSteps.has(step.step_name);
          return (
            <button
              key={step.step_name}
              onClick={() => toggleStep(step.step_name)}
              style={{
                padding: "3px 11px",
                borderRadius: 12,
                border: `1px solid ${col}`,
                background: active ? col + "22" : "transparent",
                color: active ? col : "#475569",
                cursor: "pointer",
                fontSize: 11,
                fontWeight: active ? 700 : 400,
                transition: "all 0.15s",
              }}
            >
              {step.is_current ? "● " : "◆ "}{step.step_name} ({step.defect_count})
              {step.is_current && (
                <span style={{ fontSize: 9, marginLeft: 4, opacity: 0.8 }}>현재</span>
              )}
            </button>
          );
        })}

        {/* Carryover Only 토글 */}
        <button
          onClick={() => setCarryoverOnly((p) => !p)}
          style={{
            padding: "3px 11px",
            borderRadius: 12,
            border: `1px solid ${carryoverOnly ? "#f59e0b" : "#334155"}`,
            background: carryoverOnly ? "#f59e0b22" : "transparent",
            color: carryoverOnly ? "#f59e0b" : "#64748b",
            cursor: "pointer",
            fontSize: 11,
            fontWeight: carryoverOnly ? 700 : 400,
            transition: "all 0.15s",
          }}
        >
          Carryover만
        </button>

        {/* 연결선 토글 */}
        <button
          onClick={() => setShowLines((p) => !p)}
          style={{
            padding: "3px 11px",
            borderRadius: 12,
            border: `1px solid ${showLines ? "#a78bfa" : "#334155"}`,
            background: showLines ? "#a78bfa22" : "transparent",
            color: showLines ? "#a78bfa" : "#64748b",
            cursor: "pointer",
            fontSize: 11,
            transition: "all 0.15s",
          }}
        >
          연결선
        </button>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* SVG Wafer */}
        <svg
          viewBox="0 0 300 310"
          style={{ width: "100%", maxWidth: 300, flexShrink: 0, cursor: "crosshair" }}
        >
          <defs>
            <radialGradient id="so-bg" cx="38%" cy="32%">
              <stop offset="0%" stopColor="#1a1a35" />
              <stop offset="100%" stopColor="#080814" />
            </radialGradient>
            <clipPath id="so-clip">
              <circle cx={CX} cy={CY} r={R - 1} />
            </clipPath>
          </defs>

          {/* Wafer base */}
          <circle cx={CX} cy={CY} r={R} fill="url(#so-bg)" stroke="#475569" strokeWidth={2} />

          {/* Die grid */}
          <g clipPath="url(#so-clip)" opacity={0.10}>
            {Array.from({ length: 20 }, (_, i) => (
              <React.Fragment key={i}>
                <line x1={20 + i * 13} y1={20} x2={20 + i * 13} y2={280} stroke="#fff" strokeWidth={0.3} />
                <line x1={20} y1={20 + i * 13} x2={280} y2={20 + i * 13} stroke="#fff" strokeWidth={0.3} />
              </React.Fragment>
            ))}
          </g>

          {/* Carryover 연결선 (클릭한 cluster의 step 간 경로) */}
          {clusterPositions.length >= 2 && clusterPositions.map((pos, i) => {
            if (i === 0) return null;
            const prev = clusterPositions[i - 1];
            return (
              <line
                key={i}
                x1={prev.x} y1={prev.y}
                x2={pos.x}  y2={pos.y}
                stroke="#a78bfa"
                strokeWidth={1.2}
                strokeDasharray="4 3"
                opacity={0.7}
              />
            );
          })}

          {/* Defect markers — step order 순 (현재 step이 맨 위에 그려짐) */}
          {data.steps
            .slice()
            .sort((a, b) => a.step_order - b.step_order)
            .map((step) => {
              if (!activeSteps.has(step.step_name)) return null;
              const col = stepColor(step.step_order);
              const isCurrent = step.is_current;

              return step.defects
                .filter((d) => !carryoverOnly || d.carryover_id !== null)
                .map((d) => {
                  const svgX = CX + d.x_norm * R;
                  const svgY = CY - d.y_norm * R;
                  const isHighlighted = highlightedIds.has(d.defect_id);
                  const isClicked =
                    clicked?.defect.defect_id === d.defect_id &&
                    clicked?.step.step_name === step.step_name;
                  const dotR = isCurrent
                    ? Math.max(4, Math.min(d.size_um * 1.8, 9))
                    : Math.max(3, Math.min(d.size_um * 1.4, 7));
                  const hasCarryover = d.carryover_id !== null;

                  return (
                    <g
                      key={`${step.step_name}-${d.defect_id}`}
                      onClick={() => {
                        const cluster = d.carryover_id ? (clusterById[d.carryover_id] ?? null) : null;
                        setClicked(isClicked ? null : { defect: d, step, cluster });
                      }}
                      style={{ cursor: "pointer" }}
                    >
                      {/* 클릭/하이라이트 링 */}
                      {(isClicked || isHighlighted) && (
                        <circle
                          cx={svgX} cy={svgY}
                          r={dotR + 5}
                          fill="none"
                          stroke={isClicked ? "#fff" : "#a78bfa"}
                          strokeWidth={1.5}
                          opacity={0.8}
                        />
                      )}
                      {/* Carryover 점선 링 */}
                      {hasCarryover && !isClicked && !isHighlighted && (
                        <circle
                          cx={svgX} cy={svgY}
                          r={dotR + 3}
                          fill="none"
                          stroke={col}
                          strokeWidth={0.8}
                          strokeDasharray="2 2"
                          opacity={0.5}
                        />
                      )}
                      <Marker
                        shape={step.step_order}
                        cx={svgX} cy={svgY} r={dotR}
                        fill={col}
                        stroke={col}
                        opacity={isClicked || isHighlighted ? 1 : isCurrent ? 0.88 : 0.65}
                      />
                    </g>
                  );
                });
            })}

          {/* Wafer outline + notch */}
          <circle cx={CX} cy={CY} r={R} fill="none" stroke="#94a3b8" strokeWidth={1.5} />
          <path d={`M ${CX - 8} ${CY + R + 1} Q ${CX} ${CY + R - 5} ${CX + 8} ${CY + R + 1}`}
            fill="#050510" stroke="#94a3b8" strokeWidth={1} />
        </svg>

        {/* Right panel: clicked defect info OR step summary */}
        <div style={{ flex: 1, minWidth: 190 }}>
          {clicked ? (
            <ClickedPanel
              clicked={clicked}
              data={data}
              defectByStepId={defectByStepId}
              stepColors={data.steps.reduce((m, s) => ({ ...m, [s.step_name]: stepColor(s.step_order) }), {} as Record<string, string>)}
              onClose={() => setClicked(null)}
            />
          ) : (
            <StepSummaryPanel data={data} stepColors={data.steps.reduce((m, s) => ({ ...m, [s.step_name]: stepColor(s.step_order) }), {} as Record<string, string>)} />
          )}
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: 14, marginTop: 10, flexWrap: "wrap" }}>
        {data.steps.map((step) => (
          <div key={step.step_name} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <svg width={14} height={14}>
              <MarkerPath shape={step.step_order} cx={7} cy={7} r={5} />
            </svg>
            <span style={{ fontSize: 11, color: stepColor(step.step_order) }}>
              {step.step_name}
            </span>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <svg width={14} height={14}>
            <circle cx={7} cy={7} r={5} fill="none" stroke="#94a3b8" strokeWidth={0.8} strokeDasharray="2 2" />
            <circle cx={7} cy={7} r={2} fill="#94a3b8" />
          </svg>
          <span style={{ fontSize: 11, color: "#94a3b8" }}>Carryover</span>
        </div>
      </div>

      {!clicked && (
        <div style={{ marginTop: 8, fontSize: 11, color: "#475569" }}>
          ↑ defect 점 클릭 시 step별 이력 추적 · carryover 연결선이 표시됩니다
        </div>
      )}
    </div>
  );
}


function ClickedPanel({
  clicked, data, defectByStepId, stepColors, onClose,
}: {
  clicked: ClickedState;
  data: DefectStepOverlayPayload;
  defectByStepId: Record<string, StepDefectPoint>;
  stepColors: Record<string, string>;
  onClose: () => void;
}) {
  const { defect, step, cluster } = clicked;
  const col = stepColors[step.step_name] ?? "#94a3b8";

  return (
    <div
      style={{
        background: "#0c1220",
        border: `1px solid ${col}44`,
        borderRadius: 10,
        padding: 14,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: col }}>
          {step.step_name} {step.is_current && "(현재)"}
        </span>
        <span
          onClick={onClose}
          style={{ cursor: "pointer", color: "#475569", fontSize: 13 }}
        >
          ✕
        </span>
      </div>

      {/* 클릭된 defect 기본 정보 */}
      <div style={{ fontSize: 12, lineHeight: 2, marginBottom: 10 }}>
        {[
          ["ID",   defect.defect_id],
          ["Type", defect.defect_type],
          ["Size", `${defect.size_um} μm`],
          ["Die",  `R${defect.die_row} C${defect.die_col}`],
        ].map(([label, val]) => (
          <div key={label}>
            <span style={{ color: "#64748b", display: "inline-block", width: 38 }}>{label}</span>
            <span style={{ color: "#e2e8f0" }}>{val}</span>
          </div>
        ))}
      </div>

      {/* Carryover 추적 */}
      {cluster ? (
        <>
          <div style={{ fontSize: 11, color: "#f59e0b", fontWeight: 700, marginBottom: 6 }}>
            Carryover 추적 ({Object.keys(cluster.appearances).length}개 step)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {data.steps.map((s) => {
              const app = cluster.appearances[s.step_name];
              if (!app) return null;
              const c = stepColors[s.step_name] ?? "#94a3b8";
              const isCurrent = s.is_current;
              return (
                <div
                  key={s.step_name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "4px 8px",
                    borderRadius: 6,
                    background: s.step_name === step.step_name ? c + "22" : "#1e293b",
                    border: `1px solid ${s.step_name === step.step_name ? c + "66" : "#1e293b"}`,
                  }}
                >
                  <svg width={10} height={10} style={{ flexShrink: 0 }}>
                    <MarkerPath shape={s.step_order} cx={5} cy={5} r={4} />
                  </svg>
                  <span style={{ fontSize: 11, color: c, fontWeight: isCurrent ? 700 : 400, flex: 1 }}>
                    {s.step_name}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      background: c + "33",
                      color: c,
                      borderRadius: 4,
                      padding: "1px 6px",
                    }}
                  >
                    {app.defect_type}
                  </span>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: 10, color: "#475569", marginTop: 8 }}>
            ↑ 동일 위치 근방에서 발생한 연속 carryover defect
          </div>
        </>
      ) : (
        <div style={{ fontSize: 11, color: "#475569" }}>
          이 step에서 새로 발생한 defect (carryover 없음)
        </div>
      )}
    </div>
  );
}


function StepSummaryPanel({
  data, stepColors,
}: {
  data: DefectStepOverlayPayload;
  stepColors: Record<string, string>;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {data.steps.map((step) => {
        const col = stepColors[step.step_name] ?? "#94a3b8";
        const carryoverCount = step.defects.filter((d) => d.carryover_id !== null).length;
        return (
          <div
            key={step.step_name}
            style={{
              background: "#1e293b",
              border: `1px solid ${col}33`,
              borderLeft: `3px solid ${col}`,
              borderRadius: 8,
              padding: "8px 12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: col }}>
                {step.step_name}
                {step.is_current && (
                  <span
                    style={{
                      fontSize: 9,
                      background: col + "33",
                      color: col,
                      borderRadius: 4,
                      padding: "1px 5px",
                      marginLeft: 6,
                    }}
                  >
                    현재
                  </span>
                )}
              </span>
              <span style={{ fontSize: 11, color: "#e2e8f0" }}>
                {step.defect_count}건
              </span>
            </div>
            <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>{step.step_desc}</div>
            {carryoverCount > 0 && (
              <div style={{ fontSize: 10, color: "#f59e0b", marginTop: 3 }}>
                carryover {carryoverCount}건 포함
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
