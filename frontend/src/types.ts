import type { ToolRun } from "./api";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  at: string;              // ISO 시각
  streaming?: boolean;     // true 동안 마크다운 파싱 생략 (plain text)
  tools?: ToolRun[];       // 이 응답을 만들며 실행한 tool
  error?: string;
}

export interface WaferDie {
  row: number;
  col: number;
  thickness: number; // Å
}

export interface WaferData {
  wafer_no: number;
  dies: WaferDie[];
  avg_thickness: number;
}

export interface WaferMapPayload {
  lot_id: string;
  wafers: WaferData[];
  grid_size: number;
}

export interface TrendPoint {
  lot_id: string;
  slot: number;
  metric: string;
  value: number;
  index: number;
  ooc: boolean;
  timestamp: string;
}

export interface TrendPayload {
  points: TrendPoint[];
  avg: number;
  ucl: number;
  lcl: number;
  ooc: TrendPoint[];
}

export interface DefectPoint {
  defect_id: string;
  x_norm: number;
  y_norm: number;
  die_row: number;
  die_col: number;
  defect_type: string;
  size_um: number;
}

export interface DefectMapPayload {
  lot_id: string;
  wafer_no: number;
  defects: DefectPoint[];
  type_counts: Record<string, number>;
}

export interface YieldDie {
  row: number;
  col: number;
  bin: number;
  pass: boolean;
  defect_count: number;
  defect_types: string[];
}

export interface KillAnalysis {
  defect_type: string;
  dies_affected: number;
  killed_dies: number;
  kill_rate_pct: number;
}

export interface DefectYieldWafer {
  wafer_no: number;
  defect_count: number;
  yield_pct: number;
  kill_rate_pct: number;
  killed_dies: number;
  dies_affected: number;
}

export interface TopWafer extends DefectYieldWafer {
  dies: YieldDie[];
  defects: DefectPoint[];
}

export interface DefectYieldHistoryPayload {
  lot_id: string;
  defect_type: string;
  wafers: DefectYieldWafer[];
  top_wafers: TopWafer[];
  correlation: number;
  avg_yield_pct: number;
  avg_kill_rate_pct: number;
  high_risk_wafers: number;
  kill_prob_base: number;
}

// ── Daily Report ──────────────────────────────────────────────
export interface DailyReportKpi {
  total_wip_start: number;
  total_wip_end: number;
  wip_delta: number;
  total_move: number;
  total_move_target: number;
  move_achieve_pct: number;
  new_holds: number;
  open_holds: number;
  defect_spike_count: number;
  down_count: number;
  still_down_count: number;
  pm_count: number;
}

export interface WipGroupDaily {
  group_id: string;
  group_name: string;
  wip_start: number;
  wip_end: number;
  move_in: number;
  move_out: number;
  move_target: number;
  achieve_pct: number;
  delta: number;
}

export interface HoldLot {
  lot_id: string;
  process: string;
  group_id: string;
  equipment: string;
  reason_code: string;
  reason_desc: string;
  hold_time: string;
  status: "OPEN" | "RELEASED";
}

export interface HoldByReason {
  reason_code: string;
  count: number;
  pct: number;
}

export interface HoldByProcess {
  process: string;
  count: number;
  alert: boolean;
}

export interface HoldSummary {
  new_holds: number;
  open_holds: number;
  released_holds: number;
  lots: HoldLot[];
  by_reason: HoldByReason[];
  by_process: HoldByProcess[];
}

export interface DefectIssue {
  process: string;
  group_id: string;
  equipment: string;
  defect_count: number;
  baseline: number;
  spike_ratio: number;
  spike_pct: number;
  dominant_type: string;
  affected_lots: string[];
  still_down: boolean;
}

export interface EquipmentIssue {
  eq_id: string;
  process: string;
  group_id: string;
  issue_type: "DOWN" | "PM";
  down_start: string;
  down_end: string | null;
  down_time_h: number;
  cause: string;
  status_now: string;
  wip_waiting: number;
  defect_correlated: boolean;
}

export interface PriorityAction {
  priority: number;
  urgency: "HIGH" | "MEDIUM" | "LOW";
  category: string;
  target: string;
  target_process: string;
  summary: string;
  details: string[];
  suggested_action: string;
}

export interface DailyReportPayload {
  area_key: string;
  area_name: string;
  report_date: string;
  generated_at: string;
  kpi: DailyReportKpi;
  wip_groups: WipGroupDaily[];
  hold_summary: HoldSummary;
  defect_issues: DefectIssue[];
  equipment_issues: EquipmentIssue[];
  priority_actions: PriorityAction[];
}

// ── WIP ───────────────────────────────────────────────────────
export type EqStatus = "RUNNING" | "IDLE" | "DOWN" | "PM" | "SETUP";

export interface EquipmentStatus {
  eq_id: string;
  status: EqStatus;
  current_lot: string | null;
  remaining_min: number | null;
  lots_today: number;
  util_pct: number;
}

export interface WipProcessGroup {
  group_id: string;
  group_name: string;
  desc: string;
  wip_running: number;
  wip_queue: number;
  wip_total: number;
  move_target: number;
  move_actual: number;
  move_projected: number;
  achieve_pct: number;
  process_time_min: number;
  equipments: EquipmentStatus[];
}

export interface WipStatusPayload {
  area_key: string;
  area_name: string;
  timestamp: string;
  shift_elapsed_h: number;
  shift_remaining_h: number;
  shift_progress_pct: number;
  total_wip: number;
  total_move_target: number;
  total_move_actual: number;
  total_move_projected: number;
  total_achieve_pct: number;
  process_groups: WipProcessGroup[];
}

export interface StepDefectPoint extends DefectPoint {
  carryover_id: string | null;
}

export interface ProcessStep {
  step_name: string;
  step_order: number;
  step_desc: string;
  is_current: boolean;
  defect_count: number;
  type_counts: Record<string, number>;
  defects: StepDefectPoint[];
}

export interface CarryoverAppearance {
  defect_id: string;
  defect_type: string;
}

export interface CarryoverCluster {
  cluster_id: string;
  x_center: number;
  y_center: number;
  appearances: Record<string, CarryoverAppearance>;  // step_name → {defect_id, defect_type}
}

export interface DefectStepOverlayPayload {
  lot_id: string;
  wafer_no: number;
  current_step: string;
  steps: ProcessStep[];
  carryover_clusters: CarryoverCluster[];
}

export interface YieldDefectPayload {
  lot_id: string;
  wafer_no: number;
  dies: YieldDie[];
  grid_size: number;
  defects: DefectPoint[];
  total_dies: number;
  passing_dies: number;
  wafer_yield_pct: number;
  kill_analysis: KillAnalysis[];
}
