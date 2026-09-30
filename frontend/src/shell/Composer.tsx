import React, { KeyboardEvent, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, Blocks, ChevronDown, Square, X } from "lucide-react";
import { useHub } from "../hub";

interface Props {
  onSend: (text: string) => void;
  onStop?: () => void;
  busy: boolean;
  agentId: string;
  skillId: string | null;
  onAgentChange: (id: string) => void;
  onSkillChange: (id: string | null) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

// 입력 상태를 여기 가둬서 타이핑이 메시지 목록을 다시 그리지 않게 한다
function Composer({ onSend, onStop, busy, agentId, skillId, onAgentChange, onSkillChange, placeholder, autoFocus }: Props) {
  const { meta, skills } = useHub();
  const [text, setText] = useState("");
  const [menu, setMenu] = useState<"agent" | "skill" | null>(null);
  const [hl, setHl] = useState(0);
  const ta = useRef<HTMLTextAreaElement>(null);
  const root = useRef<HTMLDivElement>(null);

  const agent = meta?.agents.find((a) => a.id === agentId);
  const skill = skills.find((s) => s.id === skillId);
  const toolCount = skill ? skill.tools.length : agent?.tools.length ?? 0;

  // "/" 로 시작하면 스킬 메뉴 — 입력한 글자로 필터
  const slash = text.startsWith("/") ? text.slice(1).toLowerCase() : null;
  const slashSkills = slash === null ? [] : skills.filter((s) => s.name.toLowerCase().includes(slash));
  const showSlash = slash !== null && slashSkills.length > 0;

  useLayoutEffect(() => {
    const el = ta.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  useEffect(() => {
    if (!menu) return;
    const close = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setMenu(null); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menu]);

  useEffect(() => { setHl(0); }, [slash]);

  const pickSkill = (id: string | null) => {
    onSkillChange(id);
    setMenu(null);
    if (slash !== null) setText("");
    ta.current?.focus();
  };

  const send = () => {
    const t = text.trim();
    if (!t || busy || t.startsWith("/")) return;
    onSend(t);
    setText("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSlash) {
      if (e.key === "ArrowDown") { e.preventDefault(); setHl((h) => (h + 1) % slashSkills.length); return; }
      if (e.key === "ArrowUp") { e.preventDefault(); setHl((h) => (h - 1 + slashSkills.length) % slashSkills.length); return; }
      if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); pickSkill(slashSkills[hl].id); return; }
      if (e.key === "Escape") { setText(""); return; }
    }
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="composer" ref={root}>
      <div className="box">
        {showSlash && (
          <div className="menu">
            {slashSkills.map((s, i) => (
              <button key={s.id} className={i === hl ? "hl" : ""} onMouseDown={(e) => { e.preventDefault(); pickSkill(s.id); }}>
                <b>/{s.name}</b>
                <small>{s.description || `tool ${s.tools.length}개`}</small>
              </button>
            ))}
          </div>
        )}
        <textarea
          ref={ta}
          rows={1}
          value={text}
          autoFocus={autoFocus}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          placeholder={placeholder ?? "질문을 입력하세요.  / 로 스킬 불러오기"}
        />
        <div className="bar">
          <div style={{ position: "relative" }}>
            <button className="opt" onClick={() => setMenu(menu === "agent" ? null : "agent")}>
              에이전트 <b>{agent?.name ?? "자동 선택"}</b>
              <ChevronDown size={13} />
            </button>
            {menu === "agent" && (
              <div className="menu">
                {meta?.agents.map((a) => (
                  <button key={a.id} className={a.id === agentId ? "sel" : ""} onClick={() => { onAgentChange(a.id); setMenu(null); }}>
                    <b>{a.name}</b>
                    <small>{a.description} · tool {a.tools.length}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div style={{ position: "relative" }}>
            {skill ? (
              <span className="opt skill-on" role="button" onClick={() => onSkillChange(null)} title="스킬 해제">
                <Blocks size={14} />{skill.name}<X size={12} />
              </span>
            ) : (
              <button className="opt" onClick={() => setMenu(menu === "skill" ? null : "skill")}>
                <Blocks size={14} />스킬
              </button>
            )}
            {menu === "skill" && (
              <div className="menu">
                {skills.length === 0 && <button disabled><small>저장된 스킬이 없습니다</small></button>}
                {skills.map((s) => (
                  <button key={s.id} onClick={() => pickSkill(s.id)}>
                    <b>{s.name}</b>
                    <small>{s.description || `tool ${s.tools.length}개`}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
          <span className="limit">tool {toolCount}개 사용</span>
          {busy && onStop ? (
            <button className="send stop" onClick={onStop} aria-label="중지"><Square size={12} fill="currentColor" /></button>
          ) : (
            <button className="send" onClick={send} disabled={!text.trim() || busy} aria-label="전송"><ArrowUp size={17} strokeWidth={2.2} /></button>
          )}
        </div>
      </div>
    </div>
  );
}

export default React.memo(Composer);
