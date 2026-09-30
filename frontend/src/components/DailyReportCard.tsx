import React, { useState } from "react";
import { alpha } from "../lib/color";
import {
  DailyReportPayload, PriorityAction, WipGroupDaily,
  HoldSummary, DefectIssue, EquipmentIssue,
} from "../types";

// ── 긴급도 색상 ──────────────────────────────────────────────────
const URGENCY = {
  HIGH:   { color: "var(--c-red)", bg: "color-mix(in srgb, var(--err-soft) 20%, transparent)", border: "color-mix(in srgb, var(--c-red) 27%, transparent)", label: "긴급", dot: "●" },
  MEDIUM: { color: "var(--c-amber)", bg: "color-mix(in srgb, var(--warn-soft) 20%, transparent)", border: "color-mix(in srgb, var(--c-amber) 27%, transparent)", label: "주의", dot: "◆" },
  LOW:    { color: "var(--c-green)", bg: "color-mix(in srgb, var(--ok-soft) 13%, transparent)", border: "color-mix(in srgb, var(--c-green) 20%, transparent)", label: "관찰", dot: "○" },
};

// ── KPI Chip ────────────────────────────────────────────────────
function KpiChip({
  label, value, sub, color = "var(--ink)", alert = false,
}: {
  label: string; value: React.ReactNode; sub?: string; color?: string; alert?: boolean;
}) {
  return (
    <div style={{
      background: "var(--sand)",
      border: `1px solid ${alert ? "color-mix(in srgb, var(--c-red) 33%, transparent)" : "var(--line-strong)"}`,
      borderRadius: 8,
      padding: "8px 14px",
      minWidth: 80,
      textAlign: "center",
    }}>
      <div style={{ fontSize: 20, fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: "var(--faint)", marginTop: 1 }}>{sub}</div>}
      <div style={{ fontSize: 10, color: "var(--faint)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

// ── Priority Action Item ─────────────────────────────────────────
function ActionItem({ action }: { action: PriorityAction }) {
  const [open, setOpen] = useState(action.priority <= 2);
  const u = URGENCY[action.urgency] ?? URGENCY.LOW;

  return (
    <div style={{
      border: `1px solid ${u.border}`,
      borderLeft: `3px solid ${u.color}`,
      borderRadius: 8,
      background: u.bg,
      overflow: "hidden",
    }}>
      {/* Header row */}
      <div
        onClick={() => setOpen((p) => !p)}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 14px", cursor: "pointer",
          flexWrap: "wrap",
        }}
      >
        {/* Priority badge */}
        <span style={{
          width: 22, height: 22, borderRadius: "50%",
          background: alpha(u.color, "33"), border: `1px solid ${u.color}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, fontWeight: 700, color: u.color, flexShrink: 0,
        }}>
          {action.priority}
        </span>

        {/* Urgency label */}
        <span style={{
          fontSize: 10, fontWeight: 700, color: u.color,
          background: alpha(u.color, "22"), padding: "2px 7px", borderRadius: 8,
          flexShrink: 0,
        }}>
          {u.dot} {u.label}
        </span>

        {/* Category */}
        <span style={{ fontSize: 11, color: "var(--sub)", flexShrink: 0 }}>
          [{action.category}]
        </span>

        {/* Target */}
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--ink)" }}>
          {action.target}
        </span>
        <span style={{ fontSize: 10, color: "var(--faint)" }}>
          {action.target_process}
        </span>

        <span style={{ marginLeft: "auto", color: "var(--faint)", fontSize: 11 }}>
          {open ? "▲" : "▼"}
        </span>
      </div>

      {/* Summary line (always visible) */}
      <div style={{ padding: "0 14px 8px 46px", fontSize: 12, color: "var(--ink)" }}>
        {action.summary}
      </div>

      {/* Expanded: details + action */}
      {open && (
        <div style={{ borderTop: `1px solid ${u.border}`, padding: "10px 14px 12px 46px" }}>
          <ul style={{ margin: "0 0 10px", padding: "0 0 0 14px" }}>
            {action.details.map((d, i) => (
              <li key={i} style={{ fontSize: 12, color: "var(--sub)", marginBottom: 4, lineHeight: 1.6 }}>
                {d}
              </li>
            ))}
          </ul>
          <div style={{
            background: "var(--sunken)",
            borderRadius: 6, padding: "8px 12px",
            borderLeft: `2px solid ${u.color}`,
          }}>
            <span style={{ fontSize: 10, color: u.color, fontWeight: 700, display: "block", marginBottom: 3 }}>
              → 권고 조치
            </span>
            <span style={{ fontSize: 12, color: "var(--ink)", lineHeight: 1.6 }}>
              {action.suggested_action}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── WIP Tab ─────────────────────────────────────────────────────
function WipTab({ groups }: { groups: WipGroupDaily[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "var(--sunken)" }}>
            {["공정 그룹", "WIP 시작", "WIP 종료", "변동", "Move In", "Move Out", "목표", "달성률"].map((h) => (
              <th key={h} style={{
                padding: "5px 10px", color: "var(--faint)", fontWeight: 600,
                textAlign: "center", borderBottom: "1px solid var(--line-strong)", whiteSpace: "nowrap",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const deltaColor = g.delta > 0 ? "var(--c-red)" : g.delta < 0 ? "var(--c-green)" : "var(--faint)";
            const achieveColor = g.achieve_pct >= 95 ? "var(--c-green)" : g.achieve_pct >= 80 ? "var(--c-amber)" : "var(--c-red)";
            return (
              <tr key={g.group_id} style={{ borderBottom: "1px solid var(--sand)" }}>
                <td style={{ padding: "6px 10px", color: "var(--ink)", fontWeight: 600 }}>{g.group_name}</td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: "var(--sub)" }}>{g.wip_start}</td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: "var(--sub)" }}>{g.wip_end}</td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: deltaColor, fontWeight: 700 }}>
                  {g.delta > 0 ? `+${g.delta}` : g.delta}
                </td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: "var(--faint)" }}>{g.move_in}</td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: "var(--ink)" }}>{g.move_out}</td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: "var(--faint)" }}>{g.move_target}</td>
                <td style={{ padding: "6px 10px", textAlign: "center", color: achieveColor, fontWeight: 700 }}>
                  {g.achieve_pct}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Hold Tab ─────────────────────────────────────────────────────
function HoldTab({ hold }: { hold: HoldSummary }) {
  return (
    <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
      {/* Lot 목록 */}
      <div style={{ flex: 2, minWidth: 260, overflowX: "auto" }}>
        <div style={{ fontSize: 11, color: "var(--faint)", marginBottom: 6, fontWeight: 600 }}>Lot 목록</div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "var(--sunken)" }}>
              {["Lot ID", "공정", "장비", "원인", "시각", "상태"].map((h) => (
                <th key={h} style={{
                  padding: "4px 8px", color: "var(--faint)", fontWeight: 600,
                  textAlign: "left", borderBottom: "1px solid var(--line-strong)", whiteSpace: "nowrap",
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {hold.lots.map((h) => (
              <tr key={h.lot_id + h.hold_time} style={{ borderBottom: "1px solid var(--sand)" }}>
                <td style={{ padding: "5px 8px", color: "var(--c-sky)", fontFamily: "monospace" }}>{h.lot_id}</td>
                <td style={{ padding: "5px 8px", color: "var(--sub)" }}>{h.process}</td>
                <td style={{ padding: "5px 8px", color: "var(--sub)", fontFamily: "monospace" }}>{h.equipment}</td>
                <td style={{ padding: "5px 8px", color: "var(--c-amber)", fontSize: 11 }}>{h.reason_code}</td>
                <td style={{ padding: "5px 8px", color: "var(--faint)", fontSize: 11 }}>{h.hold_time.slice(11, 16)}</td>
                <td style={{ padding: "5px 8px" }}>
                  <span style={{
                    fontSize: 10, padding: "1px 7px", borderRadius: 8, fontWeight: 700,
                    background: h.status === "OPEN" ? "color-mix(in srgb, var(--err-soft) 33%, transparent)" : "color-mix(in srgb, var(--ok-soft) 20%, transparent)",
                    color: h.status === "OPEN" ? "var(--c-red)" : "var(--c-green)",
                    border: `1px solid ${h.status === "OPEN" ? "color-mix(in srgb, var(--c-red) 27%, transparent)" : "color-mix(in srgb, var(--c-green) 20%, transparent)"}`,
                  }}>{h.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 원인별 / 공정별 집계 */}
      <div style={{ flex: 1, minWidth: 160 }}>
        <div style={{ fontSize: 11, color: "var(--faint)", marginBottom: 6, fontWeight: 600 }}>원인별</div>
        {hold.by_reason.map((r) => (
          <div key={r.reason_code} style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: "var(--sub)" }}>{r.reason_code}</span>
            <span style={{ fontSize: 11, color: "var(--c-amber)", fontWeight: 700 }}>
              {r.count}건 <span style={{ color: "var(--faint)" }}>({r.pct}%)</span>
            </span>
          </div>
        ))}
        <div style={{ height: 1, background: "var(--line-strong)", margin: "8px 0" }} />
        <div style={{ fontSize: 11, color: "var(--faint)", marginBottom: 6, fontWeight: 600 }}>공정별</div>
        {hold.by_process.map((p) => (
          <div key={p.process} style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
            <span style={{ fontSize: 11, color: p.alert ? "var(--c-amber)" : "var(--sub)" }}>
              {p.alert && "⚠ "}{p.process}
            </span>
            <span style={{ fontSize: 11, color: p.alert ? "var(--c-amber)" : "var(--ink)", fontWeight: p.alert ? 700 : 400 }}>
              {p.count}건
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Defect Tab ───────────────────────────────────────────────────
function DefectTab({ issues }: { issues: DefectIssue[] }) {
  if (issues.length === 0) {
    return <div style={{ color: "var(--faint)", fontSize: 13, padding: "12px 0" }}>전일 Defect 스파이크 없음</div>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "var(--sunken)" }}>
            {["장비", "공정", "Defect 건수", "기준", "스파이크", "주요 유형", "영향 Lot", "현재 상태"].map((h) => (
              <th key={h} style={{
                padding: "5px 10px", color: "var(--faint)", fontWeight: 600,
                textAlign: "left", borderBottom: "1px solid var(--line-strong)", whiteSpace: "nowrap",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {issues.map((d) => {
            const spikeColor = d.spike_pct >= 200 ? "var(--c-red)" : d.spike_pct >= 100 ? "var(--c-amber)" : "var(--warn)";
            return (
              <tr key={d.equipment} style={{ borderBottom: "1px solid var(--sand)" }}>
                <td style={{ padding: "6px 10px", color: "var(--ink)", fontFamily: "monospace", fontWeight: 600 }}>
                  {d.still_down && <span style={{ color: "var(--c-red)" }}>● </span>}
                  {d.equipment}
                </td>
                <td style={{ padding: "6px 10px", color: "var(--sub)" }}>{d.process}</td>
                <td style={{ padding: "6px 10px", color: spikeColor, fontWeight: 700 }}>{d.defect_count}</td>
                <td style={{ padding: "6px 10px", color: "var(--faint)" }}>{d.baseline}</td>
                <td style={{ padding: "6px 10px", color: spikeColor, fontWeight: 700 }}>
                  +{d.spike_pct.toFixed(0)}% ({d.spike_ratio}×)
                </td>
                <td style={{ padding: "6px 10px" }}>
                  <span style={{
                    fontSize: 10, padding: "1px 6px", borderRadius: 6,
                    background: "var(--sand)", color: "var(--c-amber)", border: "1px solid color-mix(in srgb, var(--c-amber) 20%, transparent)",
                  }}>{d.dominant_type}</span>
                </td>
                <td style={{ padding: "6px 10px", color: "var(--c-sky)", fontSize: 11 }}>
                  {d.affected_lots.slice(0, 2).join(", ")}{d.affected_lots.length > 2 ? "..." : ""}
                </td>
                <td style={{ padding: "6px 10px" }}>
                  {d.still_down ? (
                    <span style={{ fontSize: 10, color: "var(--c-red)", fontWeight: 700 }}>🔴 DOWN</span>
                  ) : (
                    <span style={{ fontSize: 10, color: "var(--c-green)" }}>✅ 복구</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Equipment Tab ────────────────────────────────────────────────
function EquipmentTab({ issues }: { issues: EquipmentIssue[] }) {
  if (issues.length === 0) {
    return <div style={{ color: "var(--faint)", fontSize: 13, padding: "12px 0" }}>전일 장비 이슈 없음</div>;
  }

  const sorted = [...issues].sort((a, b) => {
    if (a.status_now === "DOWN" && b.status_now !== "DOWN") return -1;
    if (a.status_now !== "DOWN" && b.status_now === "DOWN") return 1;
    return b.wip_waiting - a.wip_waiting;
  });

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "var(--sunken)" }}>
            {["장비", "공정", "유형", "발생 시각", "복구 시각", "경과(h)", "원인", "대기 Lot", "현재"].map((h) => (
              <th key={h} style={{
                padding: "5px 10px", color: "var(--faint)", fontWeight: 600,
                textAlign: "left", borderBottom: "1px solid var(--line-strong)", whiteSpace: "nowrap",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((e) => {
            const isDown = e.status_now === "DOWN";
            return (
              <tr key={e.eq_id + e.down_start} style={{
                borderBottom: "1px solid var(--sand)",
                background: isDown ? "color-mix(in srgb, var(--err-soft) 9%, transparent)" : "transparent",
              }}>
                <td style={{ padding: "6px 10px", color: isDown ? "var(--c-red)" : "var(--ink)", fontFamily: "monospace", fontWeight: 700 }}>
                  {isDown && "🔴 "}{e.eq_id}
                </td>
                <td style={{ padding: "6px 10px", color: "var(--sub)" }}>{e.process}</td>
                <td style={{ padding: "6px 10px" }}>
                  <span style={{
                    fontSize: 10, padding: "1px 7px", borderRadius: 8, fontWeight: 700,
                    background: e.issue_type === "DOWN" ? "color-mix(in srgb, var(--err-soft) 33%, transparent)" : "color-mix(in srgb, var(--c-purple-soft) 33%, transparent)",
                    color: e.issue_type === "DOWN" ? "var(--c-red)" : "var(--c-purple)",
                    border: `1px solid ${e.issue_type === "DOWN" ? "color-mix(in srgb, var(--c-red) 27%, transparent)" : "color-mix(in srgb, var(--c-purple) 27%, transparent)"}`,
                  }}>{e.issue_type}</span>
                </td>
                <td style={{ padding: "6px 10px", color: "var(--sub)", fontSize: 11 }}>{e.down_start.slice(11, 16)}</td>
                <td style={{ padding: "6px 10px", color: e.down_end ? "var(--faint)" : "var(--c-red)", fontSize: 11 }}>
                  {e.down_end ? e.down_end.slice(11, 16) : "복구 중"}
                </td>
                <td style={{ padding: "6px 10px", color: isDown ? "var(--c-red)" : "var(--faint)", fontWeight: isDown ? 700 : 400 }}>
                  {e.down_time_h.toFixed(1)}h
                </td>
                <td style={{ padding: "6px 10px", color: "var(--sub)", fontSize: 11, maxWidth: 140 }}>
                  {e.cause}
                </td>
                <td style={{ padding: "6px 10px", textAlign: "center" }}>
                  {e.wip_waiting > 0 ? (
                    <span style={{ color: "var(--c-amber)", fontWeight: 700 }}>{e.wip_waiting}개</span>
                  ) : (
                    <span style={{ color: "var(--faint)" }}>—</span>
                  )}
                </td>
                <td style={{ padding: "6px 10px" }}>
                  {isDown ? (
                    <span style={{ fontSize: 10, color: "var(--c-red)", fontWeight: 700 }}>🔴 DOWN</span>
                  ) : (
                    <span style={{ fontSize: 10, color: "var(--c-green)" }}>✅ 복구</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {/* WIP vs DOWN 교차 설명 */}
      {issues.some(e => e.status_now === "DOWN" && e.wip_waiting > 0) && (
        <div style={{ marginTop: 10, padding: "8px 12px", background: "var(--sand)", borderRadius: 8, fontSize: 11, color: "var(--sub)" }}>
          <span style={{ color: "var(--c-amber)", fontWeight: 700 }}>⚠ WIP 병목 주의</span>
          {" — "}아직 DOWN 중인 장비에 대기 중인 Lot이 있습니다. 우선 복구 또는 대체 장비 투입이 필요합니다.
        </div>
      )}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────
type Tab = "wip" | "hold" | "defect" | "equipment";

interface Props { data: DailyReportPayload }

export default function DailyReportCard({ data }: Props) {
  const [tab, setTab] = useState<Tab>("wip");
  const { kpi } = data;

  const deltaColor = kpi.wip_delta > 3 ? "var(--c-red)" : kpi.wip_delta < -3 ? "var(--c-green)" : "var(--sub)";
  const moveColor  = kpi.move_achieve_pct >= 95 ? "var(--c-green)" : kpi.move_achieve_pct >= 80 ? "var(--c-amber)" : "var(--c-red)";

  const TABS: { key: Tab; label: string; count?: number }[] = [
    { key: "wip",       label: "WIP 변동" },
    { key: "hold",      label: "Hold",      count: kpi.new_holds },
    { key: "defect",    label: "Defect 스파이크", count: kpi.defect_spike_count },
    { key: "equipment", label: "장비 이슈", count: kpi.down_count + kpi.pm_count },
  ];

  return (
    <div style={{
      background: "var(--sunken)",
      border: "1px solid var(--line-strong)",
      borderRadius: 12,
      padding: 16,
      marginTop: 12,
    }}>
      {/* ── Header ───────────────────────────────────────────── */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: "var(--ink)" }}>
            전일 이슈 리포트 — {data.area_name}
          </span>
          <span style={{ fontSize: 11, color: "var(--faint)" }}>{data.report_date}</span>
          <span style={{ fontSize: 10, color: "var(--faint)", marginLeft: "auto" }}>
            생성 {data.generated_at}
          </span>
        </div>
      </div>

      {/* ── KPI Chips ────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <KpiChip
          label="WIP 변동"
          value={kpi.wip_delta >= 0 ? `+${kpi.wip_delta}` : kpi.wip_delta}
          sub={`${kpi.total_wip_start} → ${kpi.total_wip_end}`}
          color={deltaColor}
        />
        <KpiChip
          label="이동 달성률"
          value={`${kpi.move_achieve_pct}%`}
          sub={`${kpi.total_move}/${kpi.total_move_target}`}
          color={moveColor}
        />
        <KpiChip
          label="신규 Hold"
          value={kpi.new_holds}
          sub={`Open ${kpi.open_holds}건`}
          color={kpi.new_holds >= 5 ? "var(--c-red)" : "var(--c-amber)"}
          alert={kpi.new_holds >= 5}
        />
        <KpiChip
          label="Defect 스파이크"
          value={kpi.defect_spike_count}
          sub="장비 기준"
          color={kpi.defect_spike_count >= 3 ? "var(--c-red)" : kpi.defect_spike_count >= 1 ? "var(--c-amber)" : "var(--c-green)"}
          alert={kpi.defect_spike_count >= 3}
        />
        <KpiChip
          label="장비 DOWN"
          value={kpi.still_down_count}
          sub={`전일 총 ${kpi.down_count}건`}
          color={kpi.still_down_count >= 1 ? "var(--c-red)" : "var(--c-green)"}
          alert={kpi.still_down_count >= 1}
        />
        <KpiChip
          label="PM"
          value={kpi.pm_count}
          sub="전일 실시"
          color="var(--c-purple)"
        />
      </div>

      {/* ── Priority Actions ─────────────────────────────────── */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--sub)", marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: "var(--c-red)" }}>▶</span> 오늘 우선 대응 사항
          <span style={{ fontSize: 10, color: "var(--faint)", fontWeight: 400 }}>
            (WIP 병목 · Defect · Hold 교차 분석)
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {data.priority_actions.length === 0 ? (
            <div style={{ color: "var(--c-green)", fontSize: 13, padding: "8px 0" }}>
              ✅ 전일 특이 이슈 없음 — 정상 운영 중
            </div>
          ) : (
            data.priority_actions.map((a) => (
              <ActionItem key={a.priority} action={a} />
            ))
          )}
        </div>
      </div>

      {/* ── Detail Tabs ──────────────────────────────────────── */}
      <div style={{ borderTop: "1px solid var(--line-strong)", paddingTop: 14 }}>
        {/* Tab bar */}
        <div style={{ display: "flex", gap: 4, marginBottom: 12, flexWrap: "wrap" }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                padding: "5px 14px",
                borderRadius: 8,
                border: `1px solid ${tab === t.key ? "var(--c-blue)" : "var(--line-strong)"}`,
                background: tab === t.key ? "color-mix(in srgb, var(--c-blue) 13%, transparent)" : "transparent",
                color: tab === t.key ? "var(--c-sky)" : "var(--faint)",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: tab === t.key ? 700 : 400,
                transition: "all 0.15s",
                display: "flex", alignItems: "center", gap: 6,
              }}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span style={{
                  background: t.count >= 3 ? "color-mix(in srgb, var(--c-red) 20%, transparent)" : "color-mix(in srgb, var(--c-amber) 20%, transparent)",
                  color: t.count >= 3 ? "var(--c-red)" : "var(--c-amber)",
                  borderRadius: 10, padding: "0 5px", fontSize: 10, fontWeight: 700,
                }}>
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "wip"       && <WipTab groups={data.wip_groups} />}
        {tab === "hold"      && <HoldTab hold={data.hold_summary} />}
        {tab === "defect"    && <DefectTab issues={data.defect_issues} />}
        {tab === "equipment" && <EquipmentTab issues={data.equipment_issues} />}
      </div>
    </div>
  );
}
