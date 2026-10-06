import React, { useEffect, useMemo, useState } from "react";
import { CalendarClock, Check, CircleAlert, Blocks, RotateCw } from "lucide-react";
import { api, Overview, RouteInfo, ToolRun } from "../api";
import { Message } from "../types";
import { useHub } from "../hub";
import { skillDraft } from "../lib/draft";
import { fmtTime } from "../lib/hooks";
import { StatusRows, TodayEvents, SkillRows } from "./widgets";

interface Props {
  messages: Message[];
  route: RouteInfo | null;   // 마지막 응답의 분기 결과
  agentId: string;
  skillId: string | null;
  hasConversation: boolean;
  busy: boolean;
  navigate: (p: string) => void;
  onSchedule: () => void;
}

const fmtArgs = (args: Record<string, unknown>) =>
  Object.entries(args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");

export default function ChatContext(props: Props) {
  return props.hasConversation || props.messages.length ? <ConversationContext {...props} /> : <TodayContext />;
}

function ConversationContext({ messages, route, agentId, skillId, busy, navigate, onSchedule }: Props) {
  const { meta, skills, toolLabel, agentName } = useHub();
  const skill = skills.find((s) => s.id === skillId);
  const agent = meta?.agents.find((a) => a.id === route?.agent_id) ?? meta?.agents.find((a) => a.id === agentId);
  // 실제로 켜졌던 tool (분기 결과) — 없으면(옛 대화) 선택 기준으로 추정
  const available = route?.tools ?? skill?.tools ?? agent?.tools ?? [];
  const locked = new Set(route?.locked ?? []);

  const runs = useMemo(() => messages.flatMap((m) => m.tools ?? []) as ToolRun[], [messages]);
  const used = useMemo(() => new Set(runs.map((r) => r.name)), [runs]);

  // 대화에서 다룬 대상 — tool 인자에서 우선, 없으면 본문에서
  const target = useMemo(() => {
    let lot: string | undefined, wafer: string | undefined, area: string | undefined;
    for (const r of runs) {
      const a = r.args as Record<string, any>;
      if (a.lot_id) lot = String(a.lot_id);
      if (a.lot_ids) lot = String(a.lot_ids).replace(/[[\]"]/g, "");
      if (a.wafer_no) wafer = String(a.wafer_no);
      if (a.area_key) area = String(a.area_key);
    }
    if (!lot) lot = messages.map((m) => m.content).join(" ").match(/TE2F[EFC]\d+/)?.[0];
    return { lot, wafer, area };
  }, [runs, messages]);

  const saveAsSkill = () => {
    skillDraft.tools = Array.from(used);
    navigate("/skills/new");
  };

  return (
    <aside className="ctx">
      <div className="ctx-sec">
        <h3>이 대화</h3>
        <dl className="kv">
          <dt>에이전트</dt>
          <dd>{agentId === "auto" && route ? <>자동 → {route.agent_name}</> : agentName(agentId)}</dd>
          {skill && <><dt>스킬</dt><dd>{skill.name}</dd></>}
          {target.area && <><dt>Area</dt><dd>{target.area}</dd></>}
          {target.lot && <><dt>Lot</dt><dd className="mono" style={{ fontSize: 12.5 }}>{target.lot}</dd></>}
          {target.wafer && <><dt>Wafer</dt><dd className="num">{target.wafer}</dd></>}
          <dt>사용 tool</dt><dd className="num">{available.length}개 중 {used.size}개</dd>
        </dl>
      </div>

      <div className="ctx-sec">
        <h3>실행 기록</h3>
        {runs.length === 0 && <div className="muted" style={{ fontSize: 12.5 }}>아직 실행한 tool이 없습니다</div>}
        {runs.map((r, i) => (
          <div key={r.id ?? i} className={`tc ${r.ok === false ? "fail" : ""}`}>
            {r.ok === null ? <span className="spin" style={{ marginTop: 3 }} /> : r.ok ? <Check size={14} strokeWidth={2.4} /> : <CircleAlert size={14} />}
            <div>
              <span className="mono">{r.name}</span>
              <small>{fmtArgs(r.args) || "인자 없음"}</small>
            </div>
            <span className="ms num">{r.ms === null ? "" : r.ms < 1000 ? `${r.ms}ms` : `${(r.ms / 1000).toFixed(1)}s`}</span>
          </div>
        ))}
      </div>

      <div className="ctx-sec">
        <h3>
          {route ? "마지막 응답에 켜진 tool" : "에이전트가 쓸 수 있는 tool"}
          {used.size > 0 && !skill && <button onClick={saveAsSkill}>스킬로 저장</button>}
        </h3>
        <div className="skillcard">
          <b>{skill ? skill.name : agent?.name ?? agentName(agentId)}</b>
          <p>{skill ? skill.description : agent?.description}</p>
          <div className="tools-mini">
            {available.map((t) => <span key={t} className={used.has(t) ? "used" : ""}>{toolLabel(t)}{locked.has(t) && " · 필수"}</span>)}
          </div>
          {route && route.dropped.length > 0 && (
            <p className="muted" style={{ marginTop: 8, fontSize: 11.5 }}>
              제외: {route.dropped.map((d) => toolLabel(d.name)).join(", ")}
            </p>
          )}
        </div>
      </div>

      <div className="ctx-sec"><h3>MCP 서버</h3><McpRows /></div>

      <div className="ctx-sec">
        <button className="cta" onClick={onSchedule} disabled={busy || !messages.some((m) => m.role === "user")}>
          <CalendarClock size={15} />이 질문을 매일 실행
        </button>
        {!skill && used.size > 0 && (
          <button className="cta" onClick={saveAsSkill}><Blocks size={15} />사용한 tool로 스킬 만들기</button>
        )}
      </div>
    </aside>
  );
}

function McpRows() {
  const { meta, refreshMeta, toast } = useHub();
  const [busy, setBusy] = useState(false);
  const servers = meta?.mcp_servers ?? [];
  const refresh = async () => {
    setBusy(true);
    try {
      const r = await api.refreshCatalog();
      await refreshMeta();
      toast(`MCP tool ${r.tools}개를 다시 불러왔습니다`);
    } catch {
      toast("MCP 새로고침 실패");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      {servers.length === 0 && <div className="muted" style={{ fontSize: 12.5 }}>설정된 서버가 없습니다</div>}
      {servers.map((s) => (
        <div key={s.name} className="mcp-row" title={s.error ?? s.url}>
          <span className={`dot ${s.status === "ok" ? "ok" : "err"}`} />
          <b>{s.name}</b>
          <small className="mono">{s.url.replace(/^https?:\/\//, "")}</small>
          <span className="num">{s.status === "ok" ? `tool ${s.tools.length}` : "응답 없음"}</span>
        </div>
      ))}
      <button className="ghost" style={{ marginTop: 8 }} onClick={refresh} disabled={busy}>
        <RotateCw size={12} className={busy ? "spinning" : ""} />tool 목록 새로고침
      </button>
    </>
  );
}

function TodayContext() {
  const { meta } = useHub();
  const area = meta?.areas[0] ?? "M14 CMP";
  const [ov, setOv] = useState<Overview | null>(null);

  useEffect(() => {
    api.overview(area).then(setOv).catch(() => setOv(null));
  }, [area]);

  return (
    <aside className="ctx">
      <div className="ctx-sec">
        <h3>오늘 라인 · {area}</h3>
        {ov ? (
          <dl className="kv">
            <dt>WIP</dt>
            <dd className="num">{ov.kpi.wip.toLocaleString()} <span className="muted" style={{ fontWeight: 500 }}>{ov.kpi.wip_delta >= 0 ? "+" : ""}{ov.kpi.wip_delta}</span></dd>
            <dt>EOD 예상</dt>
            <dd className="num" style={{ color: ov.kpi.achieve_pct < 100 ? "var(--warn)" : "var(--ok)" }}>{ov.kpi.achieve_pct}%</dd>
            <dt>Open Hold</dt>
            <dd className="num">{ov.kpi.open_holds} <span style={{ color: "var(--err)", fontWeight: 500 }}>신규 {ov.kpi.new_holds}</span></dd>
            <dt>DOWN</dt>
            <dd>{ov.kpi.down_eq.length ? ov.kpi.down_eq.join(", ") : "없음"}</dd>
            <dt>기준</dt>
            <dd className="muted" style={{ fontWeight: 500 }}>{fmtTime(ov.updated_at.replace(" ", "T"))}</dd>
          </dl>
        ) : (
          <div className="skeleton" style={{ height: 96 }} />
        )}
      </div>
      <div className="ctx-sec"><h3>포탈</h3><StatusRows /></div>
      <div className="ctx-sec"><h3>예정 이벤터</h3><TodayEvents /></div>
      <div className="ctx-sec"><h3>내 스킬</h3><SkillRows /></div>
    </aside>
  );
}
