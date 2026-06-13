import React, { useEffect, useState, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { Download, Play, ChevronDown, ChevronUp } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ParamMeta {
  key: string;
  label: string;
  type: "pass" | "fail";
  unit: string;
}

interface GroupingCol {
  key: string;
  label: string;
}

interface StatEntry {
  mean: number;
  std: number;
  min: number;
  max: number;
  count: number;
}

interface AnalysisGroup {
  group_value: string;
  count: number;
  stats: Record<string, StatEntry>;
  wafers: Record<string, any>[];
}

interface AnalysisResult {
  group_by: string;
  lot_ids: string[];
  yield_params: string[];
  groups: AnalysisGroup[];
  total_wafers: number;
}

// ── Color palette for groups ───────────────────────────────────────────────────

const GROUP_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#06b6d4"];

const getColor = (idx: number) => GROUP_COLORS[idx % GROUP_COLORS.length];

// ── Stat coloring ──────────────────────────────────────────────────────────────

function statColor(value: number, allValues: number[], type: "pass" | "fail"): string {
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  if (max === min) return "transparent";
  const ratio = (value - min) / (max - min); // 0=worst, 1=best for pass; reversed for fail
  const goodRatio = type === "pass" ? ratio : 1 - ratio;
  if (goodRatio > 0.66) return "rgba(34,197,94,0.18)";
  if (goodRatio < 0.33) return "rgba(239,68,68,0.18)";
  return "rgba(245,158,11,0.12)";
}

// ── Custom tooltip ─────────────────────────────────────────────────────────────

const ChartTooltip = ({ active, payload, label, paramLabel }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: "#1e293b", border: "1px solid #334155",
      borderRadius: 8, padding: "10px 14px", fontSize: 12,
    }}>
      <div style={{ color: "#94a3b8", marginBottom: 4 }}>{label}</div>
      <div style={{ color: "#e2e8f0", fontWeight: 700 }}>{paramLabel}</div>
      <div style={{ color: "#60a5fa" }}>Mean: <b>{d.mean?.toFixed(2)}%</b></div>
      <div style={{ color: "#94a3b8" }}>±Std: {d.std?.toFixed(2)}</div>
      <div style={{ color: "#94a3b8" }}>Min: {d.min?.toFixed(2)} / Max: {d.max?.toFixed(2)}</div>
      <div style={{ color: "#94a3b8" }}>N = {d.count}</div>
    </div>
  );
};

// ── Single param chart ─────────────────────────────────────────────────────────

function ParamChart({ param, groups }: { param: ParamMeta; groups: AnalysisGroup[] }) {
  const data = groups.map((g, i) => ({
    name: g.group_value,
    mean: g.stats[param.key]?.mean ?? 0,
    std: g.stats[param.key]?.std ?? 0,
    min: g.stats[param.key]?.min ?? 0,
    max: g.stats[param.key]?.max ?? 0,
    count: g.stats[param.key]?.count ?? 0,
    color: getColor(i),
  }));

  const vals = data.map((d) => d.mean).filter(Boolean);
  const yMin = vals.length ? Math.floor(Math.min(...vals) - 2) : 0;
  const yMax = vals.length ? Math.ceil(Math.max(...vals) + 2) : 100;

  return (
    <div className="ya-chart-card">
      <div className="ya-chart-title">
        <span className={`ya-param-badge ${param.type}`}>{param.type === "pass" ? "PASS" : "FAIL"}</span>
        {param.label}
        <span className="ya-chart-unit">(%)</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={38}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip content={<ChartTooltip paramLabel={param.label} />} />
          <Bar dataKey="mean" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Stats table ────────────────────────────────────────────────────────────────

function StatsTable({ result, paramsMeta }: { result: AnalysisResult; paramsMeta: ParamMeta[] }) {
  const visibleParams = paramsMeta.filter((p) => result.yield_params.includes(p.key));
  const [collapsed, setCollapsed] = useState(false);

  const meansByParam: Record<string, number[]> = {};
  visibleParams.forEach((p) => {
    meansByParam[p.key] = result.groups.map((g) => g.stats[p.key]?.mean ?? 0);
  });

  return (
    <div className="ya-table-section">
      <div className="ya-section-header" onClick={() => setCollapsed((v) => !v)} style={{ cursor: "pointer" }}>
        <span>Summary Statistics</span>
        <span style={{ color: "#94a3b8", fontSize: 12 }}>
          {result.total_wafers} wafers · {result.groups.length} groups
        </span>
        {collapsed ? <ChevronDown size={16} color="#94a3b8" /> : <ChevronUp size={16} color="#94a3b8" />}
      </div>
      {!collapsed && (
        <div style={{ overflowX: "auto" }}>
          <table className="ya-table">
            <thead>
              <tr>
                <th>Group</th>
                <th>Count</th>
                {visibleParams.map((p) => (
                  <th key={p.key} colSpan={4}>
                    <span className={`ya-param-badge ${p.type}`} style={{ marginRight: 4 }}>
                      {p.type === "pass" ? "P" : "F"}
                    </span>
                    {p.label}
                  </th>
                ))}
              </tr>
              <tr className="ya-sub-header">
                <th></th>
                <th></th>
                {visibleParams.map((p) =>
                  ["Mean", "±Std", "Min", "Max"].map((sub) => (
                    <th key={`${p.key}-${sub}`}>{sub}</th>
                  ))
                )}
              </tr>
            </thead>
            <tbody>
              {result.groups.map((g, gi) => (
                <tr key={g.group_value}>
                  <td style={{ fontWeight: 600, color: getColor(gi) }}>{g.group_value}</td>
                  <td>{g.count}</td>
                  {visibleParams.map((p) => {
                    const s = g.stats[p.key];
                    const bg = s ? statColor(s.mean, meansByParam[p.key], p.type) : "transparent";
                    return s ? (
                      <React.Fragment key={p.key}>
                        <td style={{ background: bg, fontWeight: 600 }}>{s.mean.toFixed(2)}</td>
                        <td style={{ color: "#94a3b8" }}>{s.std.toFixed(2)}</td>
                        <td style={{ color: "#64748b" }}>{s.min.toFixed(2)}</td>
                        <td style={{ color: "#64748b" }}>{s.max.toFixed(2)}</td>
                      </React.Fragment>
                    ) : (
                      <React.Fragment key={p.key}>
                        <td>-</td><td>-</td><td>-</td><td>-</td>
                      </React.Fragment>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function YieldAnalysis() {
  const [lots, setLots] = useState<string[]>([]);
  const [meta, setMeta] = useState<{ grouping_columns: GroupingCol[]; yield_params: ParamMeta[] } | null>(null);

  const [selectedLots, setSelectedLots] = useState<string[]>([]);
  const [groupBy, setGroupBy] = useState("recipe");
  const [selectedParams, setSelectedParams] = useState<string[]>([
    "PT1H", "PT1H_outer", "PT1H_center", "PT1H_inner", "bl_lkg", "ledic",
  ]);

  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/yield/lots").then((r) => r.json()),
      fetch("/api/yield/meta").then((r) => r.json()),
    ]).then(([lotsData, metaData]) => {
      setLots(lotsData.lots);
      setMeta(metaData);
      // default: select all lots
      setSelectedLots(lotsData.lots);
    });
  }, []);

  const toggleLot = useCallback((lot: string) => {
    setSelectedLots((prev) =>
      prev.includes(lot) ? prev.filter((l) => l !== lot) : [...prev, lot]
    );
  }, []);

  const toggleParam = useCallback((key: string) => {
    setSelectedParams((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    );
  }, []);

  const analyze = useCallback(async () => {
    if (selectedLots.length === 0 || selectedParams.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/yield/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lot_ids: selectedLots, group_by: groupBy, yield_params: selectedParams }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setError("분석 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, [selectedLots, groupBy, selectedParams]);

  const exportExcel = useCallback(async () => {
    if (!result) return;
    setExporting(true);
    try {
      const res = await fetch("/api/yield/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lot_ids: result.lot_ids, group_by: result.group_by, yield_params: result.yield_params }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `yield_analysis_${result.group_by}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }, [result]);

  const passParams = meta?.yield_params.filter((p) => p.type === "pass" && selectedParams.includes(p.key)) ?? [];
  const failParams = meta?.yield_params.filter((p) => p.type === "fail" && selectedParams.includes(p.key)) ?? [];

  return (
    <div className="ya-root">
      {/* ── Controls ── */}
      <div className="ya-controls">
        {/* Lot selection */}
        <div className="ya-ctrl-block">
          <div className="ya-ctrl-label">
            Lot 선택
            <span className="ya-ctrl-count">{selectedLots.length}/{lots.length}</span>
          </div>
          <div className="ya-chips">
            <button
              className="ya-chip ya-chip-all"
              onClick={() => setSelectedLots(selectedLots.length === lots.length ? [] : [...lots])}
            >
              {selectedLots.length === lots.length ? "전체 해제" : "전체 선택"}
            </button>
            {lots.map((lot) => (
              <button
                key={lot}
                className={`ya-chip ${selectedLots.includes(lot) ? "active" : ""}`}
                onClick={() => toggleLot(lot)}
              >
                {lot}
              </button>
            ))}
          </div>
        </div>

        {/* Grouping */}
        <div className="ya-ctrl-block">
          <div className="ya-ctrl-label">Grouping 기준</div>
          <div className="ya-chips">
            {meta?.grouping_columns.map((col) => (
              <button
                key={col.key}
                className={`ya-chip ${groupBy === col.key ? "active" : ""}`}
                onClick={() => setGroupBy(col.key)}
              >
                {col.label}
              </button>
            ))}
          </div>
        </div>

        {/* Yield params */}
        <div className="ya-ctrl-block">
          <div className="ya-ctrl-label">수율 파라미터</div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            {/* Pass rates */}
            <div>
              <div className="ya-param-group-label pass">Pass Rate</div>
              <div className="ya-chips" style={{ marginTop: 4 }}>
                {meta?.yield_params.filter((p) => p.type === "pass").map((p) => (
                  <button
                    key={p.key}
                    className={`ya-chip ${selectedParams.includes(p.key) ? "active pass" : ""}`}
                    onClick={() => toggleParam(p.key)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            {/* Fail rates */}
            <div>
              <div className="ya-param-group-label fail">Fail Rate</div>
              <div className="ya-chips" style={{ marginTop: 4 }}>
                {meta?.yield_params.filter((p) => p.type === "fail").map((p) => (
                  <button
                    key={p.key}
                    className={`ya-chip ${selectedParams.includes(p.key) ? "active fail" : ""}`}
                    onClick={() => toggleParam(p.key)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Action */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button
            className="ya-btn-primary"
            onClick={analyze}
            disabled={loading || selectedLots.length === 0 || selectedParams.length === 0}
          >
            <Play size={14} />
            {loading ? "분석 중..." : "분석 실행"}
          </button>
          {result && (
            <button className="ya-btn-excel" onClick={exportExcel} disabled={exporting}>
              <Download size={14} />
              {exporting ? "내보내는 중..." : "Excel 다운로드"}
            </button>
          )}
        </div>
      </div>

      {/* ── Error ── */}
      {error && <div className="ya-error">{error}</div>}

      {/* ── Results ── */}
      {result && (
        <div className="ya-results">
          {/* Stats table */}
          <StatsTable result={result} paramsMeta={meta?.yield_params ?? []} />

          {/* Pass rate charts */}
          {passParams.length > 0 && (
            <div className="ya-section-header" style={{ marginTop: 24 }}>
              <span>Pass Rate 분석</span>
            </div>
          )}
          <div className="ya-chart-grid">
            {passParams.map((p) => (
              <ParamChart key={p.key} param={p} groups={result.groups} />
            ))}
          </div>

          {/* Fail rate charts */}
          {failParams.length > 0 && (
            <div className="ya-section-header" style={{ marginTop: 24 }}>
              <span>Fail Rate 분석</span>
            </div>
          )}
          <div className="ya-chart-grid">
            {failParams.map((p) => (
              <ParamChart key={p.key} param={p} groups={result.groups} />
            ))}
          </div>

          {/* Bottom export */}
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16, paddingBottom: 32 }}>
            <button className="ya-btn-excel" onClick={exportExcel} disabled={exporting}>
              <Download size={14} />
              {exporting ? "내보내는 중..." : "Excel 다운로드"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
