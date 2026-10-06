import React, { useCallback, useEffect, useState } from "react";
import { MessageSquare, RefreshCw } from "lucide-react";
import { api, Overview } from "../api";
import { useHub } from "../hub";
import Composer from "../shell/Composer";
import { fmtTime } from "../lib/hooks";
import { StatusRows, TodayEvents, SkillRows } from "./widgets";

function greeting() {
  const h = new Date().getHours();
  return h < 11 ? "좋은 아침입니다" : h < 18 ? "좋은 오후입니다" : "오늘도 수고하셨습니다";
}

export default function HomePage({ navigate }: { navigate: (p: string) => void }) {
  const { meta, startChat } = useHub();
  const areas = meta?.areas ?? ["M14 CMP"];
  const [area, setArea] = useState(areas[0]);
  const [ov, setOv] = useState<Overview | null>(null);
  const [err, setErr] = useState(false);
  const [agentId, setAgentId] = useState("auto");
  const [skillId, setSkillId] = useState<string | null>(null);
  const [tools, setTools] = useState<string[]>([]);

  const load = useCallback(() => {
    setErr(false);
    api.overview(area).then(setOv, () => setErr(true));
  }, [area]);
  useEffect(load, [load]);

  const ask = (text: string, agent = "auto") => startChat({ text, agentId: agent, skillId: null });
  const onSend = useCallback((text: string) => startChat({ text, agentId, skillId, tools }), [startChat, agentId, skillId, tools]);

  const k = ov?.kpi;
  const maxWip = Math.max(1, ...(ov?.groups.map((g) => g.wip) ?? [1]));
  const hotGroup = ov?.groups.reduce((a, b) => (b.wip > a.wip ? b : a), ov.groups[0]);
  const today = new Date().toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "short" });

  return (
    <section className="center">
      <header className="c-head"><b>홈</b></header>
      <div className="scroll">
        <div className="inner wide">
          <div className="dash-head">
            <div>
              <h1>{greeting()}</h1>
              <p>
                {today}
                {ov && <> · 전일 리포트 {ov.report_date} · 현황 {fmtTime(ov.updated_at.replace(" ", "T"))} 갱신</>}
              </p>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <div className="seg">
                {areas.map((a) => (
                  <button key={a} className={a === area ? "on" : ""} onClick={() => setArea(a)}>{a}</button>
                ))}
              </div>
              <button className="ib" onClick={load} title="새로고침"><RefreshCw size={14} /></button>
            </div>
          </div>

          {err && <div className="err-msg" style={{ marginBottom: 16 }}>현황을 불러오지 못했습니다. 백엔드 서버를 확인해주세요.</div>}

          <div className="kpis">
            {k ? (
              <>
                <div className="kpi">
                  <small>WIP</small>
                  <b className="num">{k.wip.toLocaleString()}</b>
                  <div className={`d num ${k.wip_delta > 0 ? "warn" : ""}`}>전일 대비 {k.wip_delta >= 0 ? "+" : ""}{k.wip_delta}</div>
                </div>
                <div className="kpi">
                  <small>이동 / 목표</small>
                  <b className="num">{k.move_actual.toLocaleString()}<em>/ {k.move_target.toLocaleString()}</em></b>
                  <div className="bar">
                    <i style={{ width: `${Math.min(100, (k.move_actual / k.move_target) * 100)}%` }} />
                    <i className="p" style={{ left: `${(k.move_actual / k.move_target) * 100}%`, width: `${Math.max(0, Math.min(100, ((k.move_projected - k.move_actual) / k.move_target) * 100))}%` }} />
                  </div>
                </div>
                <div className="kpi">
                  <small>EOD 예상</small>
                  <b className="num" style={{ color: k.achieve_pct < 100 ? "var(--warn)" : "var(--ok)" }}>{k.achieve_pct}%</b>
                  <div className={`d num ${k.achieve_pct < 100 ? "warn" : "good"}`}>
                    예상 {k.move_projected.toLocaleString()} · 목표 대비 {k.move_projected - k.move_target >= 0 ? "+" : ""}{k.move_projected - k.move_target}
                  </div>
                </div>
                <div className="kpi">
                  <small>Open Hold · DOWN</small>
                  <b className="num">{k.open_holds}<em>· {k.down_count}</em></b>
                  <div className={`d ${k.new_holds || k.down_count ? "bad" : ""}`}>
                    신규 Hold {k.new_holds}{k.down_eq.length ? ` · ${k.down_eq.slice(0, 2).join(", ")}${k.down_eq.length > 2 ? " 외" : ""}` : ""}
                  </div>
                </div>
              </>
            ) : (
              [0, 1, 2, 3].map((i) => <div key={i} className="kpi skeleton" style={{ height: 86 }} />)
            )}
          </div>

          <div className="dash">
            <div>
              <div className="panel">
                <div className="panel-h">
                  <b>오늘 우선 대응</b><small>전일 이슈 교차 분석</small>
                  <button className="link" onClick={() => ask(`${area} 전일 이슈 정리해줘`)}>리포트 열기</button>
                </div>
                <div className="panel-b">
                  {!ov && <div className="skeleton" style={{ height: 160, margin: "8px 0" }} />}
                  {ov?.actions.length === 0 && <div className="muted" style={{ padding: "12px 0" }}>우선 대응 항목이 없습니다</div>}
                  {ov?.actions.map((a) => (
                    <div key={a.priority} className="act">
                      <span className={`prio ${a.urgency}`}>P{a.priority}</span>
                      <div>
                        <b>{a.summary}</b>
                        <small>{a.category} · {a.suggested_action}</small>
                      </div>
                      <button
                        className="ghost"
                        onClick={() => ask(`${area} ${a.category}: ${a.summary} — 원인과 대응 방안 알려줘`, "auto")}
                      >
                        <MessageSquare size={13} />물어보기
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="panel-h">
                  <b>공정 그룹 WIP</b><small>Run + Queue · 장비</small>
                  <button className="link" onClick={() => ask(`${area} 지금 WIP 현황 알려줘`)}>WIP 상세</button>
                </div>
                <div className="panel-b">
                  {!ov && <div className="skeleton" style={{ height: 130, margin: "8px 0" }} />}
                  {ov?.groups.map((g) => {
                    const down = g.equipment.DOWN ?? 0;
                    const pm = g.equipment.PM ?? 0;
                    const hot = g === hotGroup && down > 0;
                    return (
                      <div key={g.name} className="grp">
                        <span className="ell" style={{ fontWeight: hot ? 700 : 400 }}>{g.name}</span>
                        <div className="track"><i className={hot ? "hot" : ""} style={{ width: `${(g.wip / maxWip) * 100}%` }} /></div>
                        <span className="v num" style={hot ? { color: "var(--err)", fontWeight: 700 } : undefined}>{g.wip}</span>
                        <span className={`eq num ${down ? "bad" : ""}`}>
                          {down ? `DOWN ${down}` : pm ? `PM ${pm}` : `RUN ${g.equipment.RUNNING ?? 0}/${g.eq_total}`}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div>
              <div className="panel">
                <div className="panel-h"><b>예정 이벤터</b><button className="link" onClick={() => navigate("/events")}>관리</button></div>
                <div className="panel-b"><TodayEvents onOpen={() => navigate("/events")} /></div>
              </div>
              <div className="panel">
                <div className="panel-h"><b>포탈</b><button className="link" onClick={() => navigate("/portals")}>전체</button></div>
                <div className="panel-b"><StatusRows /></div>
              </div>
              <div className="panel">
                <div className="panel-h"><b>내 스킬</b><button className="link" onClick={() => navigate("/skills/new")}>새로 만들기</button></div>
                <div className="panel-b"><SkillRows onOpen={(id) => navigate(`/skills/${id}`)} /></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Composer
        onSend={onSend}
        busy={false}
        agentId={agentId}
        skillId={skillId}
        onAgentChange={setAgentId}
        onSkillChange={setSkillId}
        selectedTools={tools}
        onToolsChange={setTools}
        placeholder="라인에 대해 질문하세요.  / 로 스킬 불러오기"
      />
    </section>
  );
}
