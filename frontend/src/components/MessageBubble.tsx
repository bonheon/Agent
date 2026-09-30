import React, { useEffect, useState } from "react";
import { Check, CircleAlert } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message, WaferMapPayload, TrendPayload, DefectMapPayload, YieldDefectPayload, DefectYieldHistoryPayload } from "../types";
import WaferMap from "./WaferMap";
import TrendChart from "./TrendChart";
import DefectMap from "./DefectMap";
import YieldDefectOverlay from "./YieldDefectOverlay";
import DefectYieldHistory from "./DefectYieldHistory";
import YieldAnalysisCard from "./YieldAnalysisCard";
import DefectStepOverlay from "./DefectStepOverlay";
import WipCard from "./WipCard";
import DailyReportCard from "./DailyReportCard";
import { DefectStepOverlayPayload, WipStatusPayload, DailyReportPayload } from "../types";
import { useHub } from "../hub";

interface Props {
  message: Message;
}

// 차트 태그를 파싱해서 섹션으로 분리
function parseContent(content: string) {
  const parts: Array<{ type: "text" | "wafer" | "trend" | "defect" | "defect_trend" | "yield_defect" | "defect_yield_history" | "yield_analysis" | "defect_step_overlay" | "wip_status" | "daily_report"; value: string }> = [];
  const regex = /\[(WAFER_MAP|TREND_CHART|DEFECT_MAP|DEFECT_TREND|YIELD_DEFECT|DEFECT_YIELD_HISTORY|YIELD_ANALYSIS|DEFECT_STEP_OVERLAY|WIP_STATUS|DAILY_REPORT):([^\]]+)\]/g;
  let last = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > last) {
      parts.push({ type: "text", value: content.slice(last, match.index) });
    }
    const tagMap: Record<string, string> = {
      WAFER_MAP: "wafer", TREND_CHART: "trend",
      DEFECT_MAP: "defect", DEFECT_TREND: "defect_trend",
      YIELD_DEFECT: "yield_defect", DEFECT_YIELD_HISTORY: "defect_yield_history",
      YIELD_ANALYSIS: "yield_analysis",
      DEFECT_STEP_OVERLAY: "defect_step_overlay",
      WIP_STATUS: "wip_status",
      DAILY_REPORT: "daily_report",
    };
    parts.push({ type: (tagMap[match[1]] ?? "text") as any, value: match[2] });
    last = match.index + match[0].length;
  }
  if (last < content.length) {
    parts.push({ type: "text", value: content.slice(last) });
  }
  return parts;
}

// 마크다운 — 스타일은 theme.css 의 .md 에서
const MD: Record<string, React.FC<any>> = {
  table: ({ children }) => (
    <div className="tbl-wrap"><table>{children}</table></div>
  ),
};

type ChartType = "wafer" | "trend" | "defect" | "defect_trend" | "yield_defect" | "defect_yield_history" | "yield_analysis" | "defect_step_overlay" | "wip_status" | "daily_report";

function ChartLoader({ type, value }: { type: ChartType; value: string }) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const parts = value.split(":");
    const [lotId, p2] = parts;

    const endpoints: Record<ChartType, string> = {
      wafer:                `/api/chart/wafer-map?lot_id=${lotId}`,
      trend:                `/api/chart/trend?lot_id=${lotId}&metric=${p2}`,
      defect:               `/api/chart/defect-map?lot_id=${lotId}&wafer_no=${p2}`,
      defect_trend:         `/api/chart/defect-trend?lot_id=${lotId}&defect_type=${p2}`,
      yield_defect:         `/api/chart/yield-defect?lot_id=${lotId}&wafer_no=${p2}`,
      defect_yield_history: `/api/chart/defect-yield-history?lot_id=${lotId}&defect_type=${p2}`,
      yield_analysis:       "",  // YieldAnalysisCard이 자체 fetch 처리
      defect_step_overlay:  "",  // DefectStepOverlayLoader가 자체 fetch 처리
      wip_status:           "",  // WipLoader가 자체 fetch 처리
      daily_report:         "",  // DailyReportLoader가 자체 fetch 처리
    };

    fetch(endpoints[type])
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, [type, value]);

  if (!data) {
    return <Loading label="차트 로딩 중" />;
  }

  const [lotId, p2] = value.split(":");

  if (type === "wafer")         return <WaferMap data={data as WaferMapPayload} />;
  if (type === "trend")         return <TrendChart data={data as TrendPayload} lotId={lotId} metric={p2} />;
  if (type === "defect")        return <DefectMap data={data as DefectMapPayload} />;
  if (type === "defect_trend")  return <TrendChart data={data as TrendPayload} lotId={lotId} metric={p2} />;
  if (type === "yield_defect")         return <YieldDefectOverlay data={data as YieldDefectPayload} />;
  if (type === "defect_yield_history") return <DefectYieldHistory data={data as DefectYieldHistoryPayload} />;
  return null;
}

// YIELD_ANALYSIS는 자체 fetch를 하므로 ChartLoader를 거치지 않고 직접 렌더링
function YieldAnalysisLoader({ value }: { value: string }) {
  return <YieldAnalysisCard value={value} />;
}

// DAILY_REPORT — 자체 fetch
function DailyReportLoader({ value }: { value: string }) {
  const [data, setData] = useState<DailyReportPayload | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const area = encodeURIComponent(value);
    fetch(`/api/report/daily?area=${area}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError(true));
  }, [value]);

  if (error) return <div className="err-msg">리포트 로드 실패</div>;
  if (!data)  return <Loading label="전일 이슈 리포트 로딩 중" />;
  return <DailyReportCard data={data} />;
}

// WIP_STATUS — 자체 fetch
function WipLoader({ value }: { value: string }) {
  const [data, setData] = useState<WipStatusPayload | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const area = encodeURIComponent(value);
    fetch(`/api/wip/status?area=${area}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError(true));
  }, [value]);

  if (error) return <div className="err-msg">WIP 데이터 로드 실패</div>;
  if (!data)  return <Loading label="WIP 현황 로딩 중" />;
  return <WipCard data={data} />;
}

// DEFECT_STEP_OVERLAY — 자체 fetch
function DefectStepOverlayLoader({ value }: { value: string }) {
  const [data, setData] = useState<DefectStepOverlayPayload | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const [lotId, waferNo] = value.split(":");
    fetch(`/api/chart/defect-step-overlay?lot_id=${lotId}&wafer_no=${waferNo}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError(true));
  }, [value]);

  if (error) return <div className="err-msg">Step Overlay 로드 실패</div>;
  if (!data)  return <Loading label="Step Overlay 로딩 중" />;
  return <DefectStepOverlay data={data} />;
}

function Loading({ label }: { label: string }) {
  return <div className="chart-loading"><span className="spin" />{label}</div>;
}

function ToolRuns({ runs }: { runs: NonNullable<Message["tools"]> }) {
  const { toolLabel } = useHub();
  return (
    <div className="run">
      {runs.map((r, i) => (
        <span key={r.id ?? i} className={`t ${r.ok === false ? "fail" : ""}`} title={JSON.stringify(r.args)}>
          {r.ok === null ? <span className="spin" /> : r.ok ? <Check size={12} strokeWidth={2.6} /> : <CircleAlert size={12} />}
          {toolLabel(r.name)}
          {r.ms !== null && <span className="num" style={{ color: "var(--faint)" }}>{r.ms < 1000 ? `${r.ms}ms` : `${(r.ms / 1000).toFixed(1)}s`}</span>}
        </span>
      ))}
    </div>
  );
}

function renderPart(p: ReturnType<typeof parseContent>[number], i: number) {
  if (p.type === "text") {
    return p.value.trim() ? (
      <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} components={MD}>{p.value}</ReactMarkdown>
    ) : null;
  }
  const chart =
    p.type === "yield_analysis" ? <YieldAnalysisLoader value={p.value} /> :
    p.type === "defect_step_overlay" ? <DefectStepOverlayLoader value={p.value} /> :
    p.type === "daily_report" ? <DailyReportLoader value={p.value} /> :
    p.type === "wip_status" ? <WipLoader value={p.value} /> :
    <ChartLoader type={p.type as ChartType} value={p.value} />;
  return <div key={i} className="chart-slot">{chart}</div>;
}

function MessageBubbleInner({ message }: Props) {
  if (message.role === "user") {
    return <div className="u"><div>{message.content}</div></div>;
  }

  const waiting = message.streaming && !message.content && !message.tools?.length;
  return (
    <div className="bot">
      <div className="av">F</div>
      <div className="body">
        {!!message.tools?.length && <ToolRuns runs={message.tools} />}
        {waiting && <div className="thinking"><i /><i /><i /></div>}
        {message.streaming ? (
          // 스트리밍 중 — 마크다운 파싱 생략 (매 토큰 재파싱 방지)
          <div className="md" style={{ whiteSpace: "pre-wrap" }}>{message.content.replace(/\[[A-Z_]+:[^\]]*\]?/g, "")}</div>
        ) : (
          <div className="md">{parseContent(message.content).map(renderPart)}</div>
        )}
        {message.error && <div className="err-msg" style={{ marginTop: 8 }}>{message.error}</div>}
      </div>
    </div>
  );
}

const MessageBubble = React.memo(MessageBubbleInner);
export default MessageBubble;
