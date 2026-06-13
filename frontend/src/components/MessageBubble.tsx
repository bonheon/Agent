import React, { useEffect, useState } from "react";
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

// 마크다운 컴포넌트 — 다크 테마 스타일
const MD: Record<string, React.FC<any>> = {
  table: ({ children }) => (
    <div style={{ overflowX: "auto", margin: "8px 0" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead style={{ background: "#0f172a" }}>{children}</thead>
  ),
  th: ({ children }) => (
    <th
      style={{
        padding: "6px 12px",
        color: "#94a3b8",
        textAlign: "left",
        fontWeight: 600,
        borderBottom: "2px solid #334155",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td
      style={{
        padding: "5px 12px",
        color: "#e2e8f0",
        borderBottom: "1px solid #1e293b",
      }}
    >
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr style={{ borderBottom: "1px solid #1e293b" }}>{children}</tr>
  ),
  p: ({ children }) => (
    <p style={{ margin: "0 0 6px", lineHeight: 1.65 }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong style={{ color: "#f1f5f9", fontWeight: 600 }}>{children}</strong>
  ),
  ul: ({ children }) => (
    <ul style={{ paddingLeft: 18, margin: "4px 0 8px" }}>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol style={{ paddingLeft: 18, margin: "4px 0 8px" }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li style={{ marginBottom: 2, color: "#e2e8f0" }}>{children}</li>
  ),
  code: ({ inline, children }: any) =>
    inline ? (
      <code
        style={{
          background: "#0f172a",
          borderRadius: 4,
          padding: "1px 6px",
          fontSize: 12,
          color: "#38bdf8",
        }}
      >
        {children}
      </code>
    ) : (
      <pre
        style={{
          background: "#0f172a",
          borderRadius: 6,
          padding: "10px 14px",
          fontSize: 12,
          color: "#e2e8f0",
          overflowX: "auto",
          margin: "6px 0",
        }}
      >
        <code>{children}</code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote
      style={{
        borderLeft: "3px solid #3b82f6",
        paddingLeft: 12,
        margin: "6px 0",
        color: "#94a3b8",
      }}
    >
      {children}
    </blockquote>
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
    return <div style={{ color: "#64748b", fontSize: 13, padding: "8px 0" }}>차트 로딩 중...</div>;
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

  if (error) return <div style={{ color: "#ef4444", fontSize: 13 }}>리포트 로드 실패</div>;
  if (!data)  return <div style={{ color: "#64748b", fontSize: 13, padding: "8px 0" }}>전일 이슈 리포트 로딩 중...</div>;
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

  if (error) return <div style={{ color: "#ef4444", fontSize: 13 }}>WIP 데이터 로드 실패</div>;
  if (!data)  return <div style={{ color: "#64748b", fontSize: 13, padding: "8px 0" }}>WIP 현황 로딩 중...</div>;
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

  if (error) return <div style={{ color: "#ef4444", fontSize: 13 }}>Step Overlay 로드 실패</div>;
  if (!data)  return <div style={{ color: "#64748b", fontSize: 13, padding: "8px 0" }}>Step Overlay 로딩 중...</div>;
  return <DefectStepOverlay data={data} />;
}

function MessageBubbleInner({ message }: Props) {
  const isUser = message.role === "user";
  const parts = isUser ? null : parseContent(message.content);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 16,
      }}
    >
      {!isUser && (
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            fontWeight: 700,
            color: "#fff",
            flexShrink: 0,
            marginRight: 10,
            marginTop: 2,
          }}
        >
          AI
        </div>
      )}

      <div
        style={{
          maxWidth: "75%",
          background: isUser ? "#3b82f6" : "#1e293b",
          borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
          padding: "12px 16px",
          color: "#e2e8f0",
          fontSize: 14,
          lineHeight: 1.6,
          border: isUser ? "none" : "1px solid #334155",
          wordBreak: "break-word",
          // user 메시지만 pre-wrap (줄바꿈 보존)
          whiteSpace: isUser ? "pre-wrap" : "normal",
        }}
      >
        {isUser ? (
          message.content
        ) : message.streaming ? (
          // 스트리밍 중 — plain text로 빠르게 렌더링 (마크다운 파싱 생략)
          <span style={{ whiteSpace: "pre-wrap" }}>{message.content}</span>
        ) : (
          // 스트리밍 완료 — 마크다운 렌더링
          <>
            {parts!.map((p, i) => {
              if (p.type === "text") {
                return (
                  <ReactMarkdown
                    key={i}
                    remarkPlugins={[remarkGfm]}
                    components={MD}
                  >
                    {p.value}
                  </ReactMarkdown>
                );
              }
              if (p.type === "yield_analysis") {
                return <YieldAnalysisLoader key={i} value={p.value} />;
              }
              if (p.type === "defect_step_overlay") {
                return <DefectStepOverlayLoader key={i} value={p.value} />;
              }
              if (p.type === "daily_report") {
                return <DailyReportLoader key={i} value={p.value} />;
              }
              if (p.type === "wip_status") {
                return <WipLoader key={i} value={p.value} />;
              }
              return (
                <ChartLoader
                  key={i}
                  type={p.type as ChartType}
                  value={p.value}
                />
              );
            })}
          </>
        )}

        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            marginTop: 6,
            textAlign: "right",
          }}
        >
          {message.timestamp.toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}

const MessageBubble = React.memo(MessageBubbleInner);
export default MessageBubble;
