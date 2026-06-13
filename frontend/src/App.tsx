import React, { useState, useRef, useEffect, useCallback, useMemo, KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Message } from "./types";
import MessageBubble from "./components/MessageBubble";
import "./App.css";

const INITIAL_QUESTIONS = [
  "M14 CMP 전일 이슈 정리해줘",
  "M14 CMP Area 지금 WIP 현황 알려줘",
  "전체 Lot Recipe 기준으로 수율 분석해줘",
  "TE2FE35 Defect Map 보여줘",
];

const DEFECT_TYPES_ALL = ["PARTICLE", "SCRATCH", "BRIDGE", "PIT", "RESIDUE", "CLUSTER"];

function extractLot(content: string): string {
  const m = content.match(/TE2F[EFC]\d+/);
  return m ? m[0] : "TE2FE35";
}
function extractWafer(content: string): string {
  const m = content.match(/[Ww]afer\s*(\d+)/);
  return m ? m[1] : "5";
}
function extractDefectType(content: string): string {
  return DEFECT_TYPES_ALL.find((t) => content.includes(t)) ?? "PARTICLE";
}

function getFollowUpSuggestions(content: string): string[] {
  const lot    = extractLot(content);
  const wafer  = extractWafer(content);
  const defect = extractDefectType(content);

  if (content.includes("[DAILY_REPORT:")) {
    return [
      "지금 WIP 현황도 보여줘",
      `${lot} Hold 원인 확인해줘`,
      `${lot} Defect Map 보여줘`,
      "전체 Lot Recipe 기준 수율 분석해줘",
    ];
  }
  if (content.includes("[WIP_STATUS:")) {
    return [
      "M14 CMP 전일 이슈 정리해줘",
      `${lot} Hold 원인 확인해줘`,
      `${lot} Defect Map 보여줘`,
      "전체 Lot Equipment 기준 수율 비교해줘",
    ];
  }
  if (content.includes("[DEFECT_STEP_OVERLAY:")) {
    return [
      `${lot} Defect Map 전체 현황 보여줘`,
      `${lot} ${defect} 수율 이력 분석해줘`,
      `${lot} Wafer ${wafer}번 수율 Chip Kill 분석해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  if (content.includes("[DEFECT_YIELD_HISTORY:")) {
    return [
      `${lot} Wafer ${wafer}번 Step 간 Defect 비교해줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} 두께 트렌드 분석해줘`,
      "전체 Lot 수율 분석해줘",
    ];
  }
  if (content.includes("[YIELD_DEFECT:")) {
    return [
      `${lot} Wafer ${wafer}번 Step 간 Defect 비교해줘`,
      `${lot} ${defect} Defect Trend 보여줘`,
      `${lot} ${defect} 수율 이력 분석해줘`,
      "전체 Lot Recipe 기준 수율 비교해줘",
    ];
  }
  if (content.includes("[DEFECT_MAP:") || content.includes("[DEFECT_TREND:")) {
    return [
      `${lot} Wafer ${wafer}번 Step 간 Defect 비교해줘`,
      `${lot} ${defect} 수율 이력 분석해줘`,
      `${lot} Wafer ${wafer}번 수율 Chip Kill 분석해줘`,
      "전체 Lot Equipment 기준 수율 비교해줘",
    ];
  }
  if (content.includes("[YIELD_ANALYSIS:")) {
    return [
      "Equipment 기준으로도 수율 비교해줘",
      "Process ID 기준 수율 분석해줘",
      `${lot} Defect Map 보여줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  if (content.includes("[WAFER_MAP:")) {
    return [
      `${lot} 두께 트렌드 분석해줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} Hold 원인 확인해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  if (content.includes("[TREND_CHART:")) {
    return [
      `${lot} Wafer Map 보여줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} Hold 원인 확인해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  // Hold 답변 또는 일반 텍스트 응답
  if (content.includes("HOLD") || content.includes("Hold")) {
    return [
      `${lot} Wafer Map 보여줘`,
      `${lot} Defect Map 보여줘`,
      `${lot} 두께 트렌드 분석해줘`,
      "M14 CMP 전일 이슈 정리해줘",
    ];
  }
  return INITIAL_QUESTIONS;
}

let msgId = 0;
const newId = () => String(++msgId);

// ── 입력 전용 컴포넌트 — App 상태와 분리해 타이핑 시 메시지 목록 재렌더 방지 ──
interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

const ChatInput = React.memo(({ onSend, disabled }: ChatInputProps) => {
  const [input, setInput] = useState("");

  const doSend = useCallback(() => {
    const text = input.trim();
    if (!text || disabled) return;
    onSend(text);
    setInput("");
  }, [input, disabled, onSend]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      doSend();
    }
  };

  return (
    <div className="input-area">
      <textarea
        className="input-box"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKey}
        placeholder="질문을 입력하세요... (예: TE2FE35~TE2FE38 Equipment 기준 수율 비교해줘)"
        rows={1}
        disabled={disabled}
      />
      <button
        className="send-btn"
        onClick={doSend}
        disabled={!input.trim() || disabled}
      >
        <Send size={18} />
      </button>
    </div>
  );
});

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: newId(),
      role: "assistant",
      content:
        "안녕하세요! Fab LLM 어시스턴트입니다.\nLot Hold 원인 조회, Wafer Map, 트렌드, Defect 분석, 수율 Chip Kill 분석은 물론\nLot별 수율 Grouping 분석(Recipe/Equipment/Process ID 기준 비교)도 도와드립니다.\n\n어떤 분석을 도와드릴까요?",
      timestamp: new Date(),
    },
  ]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 마지막 완료된 AI 응답 기반 후속 추천 질문 계산
  const suggestions = useMemo(() => {
    const lastAI = [...messages].reverse().find(
      (m) => m.role === "assistant" && !m.streaming
    );
    if (!lastAI || messages.length <= 1) return INITIAL_QUESTIONS;
    return getFollowUpSuggestions(lastAI.content);
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async (text: string) => {
    if (loading) return;

    const userMsg: Message = {
      id: newId(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    const history = [...messages, userMsg];
    setMessages(history);
    setLoading(true);

    const assistantId = newId();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", timestamp: new Date(), streaming: true },
    ]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") break;
          try {
            const { delta } = JSON.parse(payload);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + delta } : m
              )
            );
          } catch {}
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "오류가 발생했습니다. 백엔드 서버를 확인해주세요.", streaming: false }
            : m
        )
      );
    } finally {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, streaming: false } : m
        )
      );
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, messages]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-dot" />
        <span className="header-title">Fab LLM Assistant</span>
        <span className="header-badge">GPT-4o</span>
      </header>

      <div className="messages">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "0 8px" }}>
            <div className="typing-dot" />
            <div className="typing-dot" style={{ animationDelay: "0.2s" }} />
            <div className="typing-dot" style={{ animationDelay: "0.4s" }} />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {!loading && (
        <div className="suggestions">
          {suggestions.map((q) => (
            <button key={q} className="suggestion-btn" onClick={() => sendMessage(q)}>
              {q}
            </button>
          ))}
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={loading} />
    </div>
  );
}
