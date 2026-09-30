import React, { useState } from "react";
import { alpha } from "../lib/color";
import { WipStatusPayload, WipProcessGroup, EquipmentStatus, EqStatus } from "../types";

// ── 장비 Status 색상/레이블 ──────────────────────────────────────
const EQ_STATUS_META: Record<EqStatus, { color: string; bg: string; label: string }> = {
  RUNNING: { color: "var(--c-green)", bg: "color-mix(in srgb, var(--ok-soft) 20%, transparent)", label: "RUN" },
  IDLE:    { color: "var(--sub)", bg: "var(--sand)",   label: "IDLE" },
  DOWN:    { color: "var(--c-red)", bg: "color-mix(in srgb, var(--err-soft) 20%, transparent)", label: "DOWN" },
  PM:      { color: "var(--c-purple)", bg: "color-mix(in srgb, var(--c-purple-soft) 67%, transparent)", label: "PM" },
  SETUP:   { color: "var(--c-blue)", bg: "color-mix(in srgb, var(--c-blue-soft) 20%, transparent)", label: "SETUP" },
};

// ── 달성률 기반 색상 ─────────────────────────────────────────────
function achieveColor(pct: number): string {
  if (pct >= 95)  return "var(--c-green)";
  if (pct >= 80)  return "var(--c-amber)";
  return "var(--c-red)";
}

// ── 숫자 포맷 ────────────────────────────────────────────────────
function fmt1(n: number) { return n.toFixed(1); }

// ── Move Progress Bar (actual + projected gap vs target) ────────
function MoveBar({
  actual, projected, target, height = 10,
}: {
  actual: number; projected: number; target: number; height?: number;
}) {
  const safeTarget = target || 1;
  const pctActual    = Math.min(100, (actual    / safeTarget) * 100);
  const pctProjected = Math.min(100, (projected / safeTarget) * 100) - pctActual;
  const targetX      = Math.min(100, 100); // target line at 100%

  return (
    <div style={{ position: "relative", width: "100%", height, marginTop: 4 }}>
      {/* Background */}
      <div style={{ position: "absolute", inset: 0, background: "var(--sand)", borderRadius: height / 2 }} />
      {/* Actual (solid green) */}
      <div style={{
        position: "absolute", top: 0, left: 0, bottom: 0,
        width: `${pctActual}%`,
        background: "var(--c-green)",
        borderRadius: height / 2,
        transition: "width 0.4s",
      }} />
      {/* Projected gap (striped lighter) */}
      {pctProjected > 0 && (
        <div style={{
          position: "absolute", top: 0, bottom: 0,
          left: `${pctActual}%`,
          width: `${pctProjected}%`,
          background: "repeating-linear-gradient(90deg, color-mix(in srgb, var(--c-green) 27%, transparent) 0px, color-mix(in srgb, var(--c-green) 27%, transparent) 4px, transparent 4px, transparent 8px)",
          borderRadius: `0 ${height / 2}px ${height / 2}px 0`,
        }} />
      )}
      {/* Target line (at 100% = right edge of bar) */}
      <div style={{
        position: "absolute", top: -2, right: 0, bottom: -2, width: 2,
        background: "var(--ink)", opacity: 0.5,
      }} />
    </div>
  );
}

// ── Equipment 상태 뱃지 ─────────────────────────────────────────
function StatusBadge({ status }: { status: EqStatus }) {
  const m = EQ_STATUS_META[status] ?? EQ_STATUS_META.IDLE;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "1px 8px", borderRadius: 10,
      background: m.bg, border: `1px solid ${alpha(m.color, "55")}`,
      color: m.color, fontSize: 10, fontWeight: 700,
      letterSpacing: "0.04em",
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%", background: m.color,
        boxShadow: status === "RUNNING" ? `0 0 4px ${m.color}` : "none",
      }} />
      {m.label}
    </span>
  );
}

// ── Equipment Row ───────────────────────────────────────────────
function EqRow({ eq }: { eq: EquipmentStatus }) {
  return (
    <tr style={{ borderBottom: "1px solid var(--sand)" }}>
      <td style={{ padding: "5px 10px", color: "var(--ink)", fontSize: 12, fontFamily: "monospace", whiteSpace: "nowrap" }}>
        {eq.eq_id}
      </td>
      <td style={{ padding: "5px 10px" }}>
        <StatusBadge status={eq.status as EqStatus} />
      </td>
      <td style={{ padding: "5px 10px", color: eq.current_lot ? "var(--c-sky)" : "var(--faint)", fontSize: 12 }}>
        {eq.current_lot ?? "—"}
      </td>
      <td style={{ padding: "5px 10px", color: "var(--c-amber)", fontSize: 12, textAlign: "right", whiteSpace: "nowrap" }}>
        {eq.remaining_min !== null ? `${eq.remaining_min} min` : "—"}
      </td>
      <td style={{ padding: "5px 10px", fontSize: 12, textAlign: "right" }}>
        <span style={{ color: "var(--ink)" }}>{eq.lots_today}</span>
        <span style={{ color: "var(--faint)", fontSize: 10, marginLeft: 2 }}>lots</span>
      </td>
      <td style={{ padding: "5px 10px", fontSize: 12, textAlign: "right", whiteSpace: "nowrap" }}>
        <span style={{ color: eq.util_pct >= 80 ? "var(--c-green)" : eq.util_pct >= 50 ? "var(--c-amber)" : "var(--faint)" }}>
          {fmt1(eq.util_pct)}%
        </span>
      </td>
    </tr>
  );
}

// ── Process Group Card ──────────────────────────────────────────
function GroupCard({ group, defaultOpen }: { group: WipProcessGroup; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const ac = achieveColor(group.achieve_pct);

  const downCount  = group.equipments.filter((e) => e.status === "DOWN").length;
  const pmCount    = group.equipments.filter((e) => e.status === "PM").length;

  return (
    <div style={{
      background: "var(--sunken)",
      border: "1px solid var(--line-strong)",
      borderRadius: 10,
      overflow: "hidden",
    }}>
      {/* Group header — clickable to expand/collapse */}
      <div
        onClick={() => setOpen((p) => !p)}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 14px", cursor: "pointer",
          background: open ? "var(--sand)" : "transparent",
          borderBottom: open ? "1px solid var(--line-strong)" : "none",
          flexWrap: "wrap",
          userSelect: "none",
        }}
      >
        <span style={{ fontSize: 11, color: "var(--faint)", flexShrink: 0 }}>
          {open ? "▼" : "▶"}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)", flex: "0 0 auto" }}>
          {group.group_name}
        </span>
        <span style={{ fontSize: 10, color: "var(--faint)" }}>{group.desc}</span>

        {/* WIP chips */}
        <div style={{ display: "flex", gap: 6, marginLeft: "auto", flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--sub)" }}>
            WIP <strong style={{ color: "var(--ink)" }}>{group.wip_total}</strong>
            <span style={{ color: "var(--faint)" }}> (Run {group.wip_running} / Q {group.wip_queue})</span>
          </span>

          {/* Move mini stats */}
          <span style={{ fontSize: 11 }}>
            이동{" "}
            <strong style={{ color: "var(--ink)" }}>{group.move_actual}</strong>
            <span style={{ color: "var(--faint)" }}>/{group.move_target}</span>
            <span style={{ color: "var(--sub)" }}>  EOD </span>
            <strong style={{ color: ac }}>{group.move_projected}</strong>
            <span style={{ color: ac, fontSize: 10 }}> ({group.achieve_pct}%)</span>
          </span>

          {/* DOWN/PM alert */}
          {downCount > 0 && (
            <span style={{ fontSize: 10, color: "var(--c-red)", background: "color-mix(in srgb, var(--err-soft) 33%, transparent)", padding: "1px 7px", borderRadius: 8, border: "1px solid color-mix(in srgb, var(--c-red) 27%, transparent)" }}>
              DOWN {downCount}
            </span>
          )}
          {pmCount > 0 && (
            <span style={{ fontSize: 10, color: "var(--c-purple)", background: "color-mix(in srgb, var(--c-purple-soft) 33%, transparent)", padding: "1px 7px", borderRadius: 8, border: "1px solid color-mix(in srgb, var(--c-purple) 27%, transparent)" }}>
              PM {pmCount}
            </span>
          )}
        </div>
      </div>

      {/* Expanded: move bar + equipment table */}
      {open && (
        <div style={{ padding: "10px 14px" }}>
          {/* Move bar */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <span style={{ fontSize: 10, color: "var(--faint)", whiteSpace: "nowrap", width: 56 }}>
              이동 진척
            </span>
            <div style={{ flex: 1 }}>
              <MoveBar
                actual={group.move_actual}
                projected={group.move_projected}
                target={group.move_target}
                height={8}
              />
            </div>
            <span style={{ fontSize: 10, color: "var(--sub)", whiteSpace: "nowrap" }}>
              {group.move_actual}/{group.move_target}
            </span>
          </div>

          {/* Equipment table */}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--sunken)" }}>
                  {["장비", "Status", "Current Lot", "잔여", "금일 이동", "가동률"].map((h) => (
                    <th key={h} style={{
                      padding: "4px 10px", fontSize: 10, color: "var(--faint)",
                      fontWeight: 600, textAlign: "left", borderBottom: "1px solid var(--line-strong)",
                      whiteSpace: "nowrap",
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {group.equipments.map((eq) => (
                  <EqRow key={eq.eq_id} eq={eq} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main WipCard ────────────────────────────────────────────────
interface Props { data: WipStatusPayload }

export default function WipCard({ data }: Props) {
  const totalAc = achieveColor(data.total_achieve_pct);

  return (
    <div style={{
      background: "var(--sunken)",
      border: "1px solid var(--line-strong)",
      borderRadius: 12,
      padding: 16,
      marginTop: 12,
    }}>
      {/* ── Header ─────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 14, flexWrap: "wrap" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--ink)" }}>
            {data.area_name} — WIP 현황
          </div>
          <div style={{ fontSize: 11, color: "var(--faint)", marginTop: 2 }}>
            {data.timestamp}
            <span style={{ marginLeft: 10 }}>
              경과 <strong style={{ color: "var(--sub)" }}>{fmt1(data.shift_elapsed_h)}h</strong>
              {" / "}
              잔여 <strong style={{ color: "var(--sub)" }}>{fmt1(data.shift_remaining_h)}h</strong>
            </span>
          </div>
        </div>

        {/* KPI chips */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {/* Total WIP */}
          <div style={{
            background: "var(--sand)", border: "1px solid var(--line-strong)",
            borderRadius: 8, padding: "6px 12px", textAlign: "center",
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--c-sky)", lineHeight: 1.2 }}>
              {data.total_wip}
            </div>
            <div style={{ fontSize: 10, color: "var(--faint)" }}>Total WIP</div>
          </div>

          {/* Move actual/target */}
          <div style={{
            background: "var(--sand)", border: "1px solid var(--line-strong)",
            borderRadius: 8, padding: "6px 12px", textAlign: "center",
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.2 }}>
              <span style={{ color: "var(--c-green)" }}>{data.total_move_actual}</span>
              <span style={{ color: "var(--faint)", fontSize: 13 }}>/{data.total_move_target}</span>
            </div>
            <div style={{ fontSize: 10, color: "var(--faint)" }}>이동 실적/목표</div>
          </div>

          {/* EOD projected */}
          <div style={{
            background: "var(--sand)",
            border: `1px solid ${alpha(totalAc, "55")}`,
            borderRadius: 8, padding: "6px 12px", textAlign: "center",
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: totalAc, lineHeight: 1.2 }}>
              {data.total_move_projected}
            </div>
            <div style={{ fontSize: 10, color: "var(--faint)" }}>
              EOD 예상 <span style={{ color: totalAc }}>({fmt1(data.total_achieve_pct)}%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Overall Move Progress Bar ───────────────────────────── */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: "var(--faint)" }}>전체 이동 진척</span>
          <span style={{ fontSize: 10, color: "var(--sub)" }}>
            실적 {data.total_move_actual}　예상 {data.total_move_projected}　목표 {data.total_move_target}
          </span>
        </div>
        <MoveBar
          actual={data.total_move_actual}
          projected={data.total_move_projected}
          target={data.total_move_target}
          height={14}
        />
        <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
          <LegendItem color="var(--c-green)" label="이동 완료" />
          <LegendItem color="color-mix(in srgb, var(--c-green) 27%, transparent)" label="EOD 예상" />
          <LegendItem color="var(--ink)" label="목표선" opacity={0.5} />
        </div>
      </div>

      {/* ── Process Group Cards ─────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data.process_groups.map((g, i) => (
          <GroupCard key={g.group_id} group={g} defaultOpen={i < 2} />
        ))}
      </div>

      {/* ── Status Legend ───────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 12, marginTop: 12, flexWrap: "wrap" }}>
        {(Object.entries(EQ_STATUS_META) as [EqStatus, typeof EQ_STATUS_META[EqStatus]][]).map(([status, m]) => (
          <div key={status} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: m.color, display: "inline-block",
            }} />
            <span style={{ fontSize: 10, color: "var(--faint)" }}>{m.label}</span>
          </div>
        ))}
        <div style={{ marginLeft: "auto", fontSize: 10, color: "var(--faint)" }}>
          ▶ 그룹명 클릭으로 장비 목록 접기/펼치기
        </div>
      </div>
    </div>
  );
}

function LegendItem({ color, label, opacity = 1 }: { color: string; label: string; opacity?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <div style={{ width: 12, height: 8, background: color, borderRadius: 2, opacity }} />
      <span style={{ fontSize: 10, color: "var(--faint)" }}>{label}</span>
    </div>
  );
}
