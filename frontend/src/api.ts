// Hub 백엔드 API — 타입과 호출 함수

export interface Agent { id: string; name: string; description: string; tools: string[] }
export interface ToolInfo { name: string; label: string; category: string; description: string }
export interface Portal { id: string; name: string; description: string; status: "ok" | "warn" | "err"; note: string; url: string }
export interface Meta { agents: Agent[]; tools: ToolInfo[]; areas: string[]; portals: Portal[] }

export interface ToolRun { id?: string; name: string; args: Record<string, unknown>; ms: number | null; ok: boolean | null }
export interface StoredMessage { role: "user" | "assistant"; content: string; tools?: ToolRun[]; at: string }
export interface ConvHead {
  id: string; title: string; source: "chat" | "event"; event_id: string | null;
  agent_id: string; skill_id: string | null; summary: string;
  created_at: string; updated_at: string; turns: number;
}
export interface Conversation extends Omit<ConvHead, "turns"> { messages: StoredMessage[] }

export interface Skill {
  id: string; name: string; description: string; tools: string[]; instructions: string;
  uses: number; created_at: string; updated_at: string;
}
export type SkillInput = Pick<Skill, "name" | "description" | "tools" | "instructions">;

export interface Schedule { kind: "daily" | "weekly"; time: string; weekday: number | null }
export interface LastRun {
  at: string; status: "ok" | "error"; conversation_id: string | null;
  summary: string; tool_count: number; elapsed_s: number;
}
export interface HubEvent {
  id: string; name: string; schedule: Schedule; prompt: string; skill_id: string | null;
  agent_id: string; target: string; enabled: boolean; last_run: LastRun | null; next_run: string | null;
}
export type EventInput = Omit<HubEvent, "id" | "last_run" | "next_run">;

export interface Overview {
  area: string; updated_at: string; report_date: string;
  kpi: {
    wip: number; wip_delta: number; move_actual: number; move_target: number; move_projected: number;
    achieve_pct: number; open_holds: number; new_holds: number; down_count: number; down_eq: string[];
  };
  actions: { priority: number; urgency: "HIGH" | "MEDIUM" | "LOW"; category: string; target: string; summary: string; suggested_action: string }[];
  groups: {
    name: string; wip: number; running: number; queue: number; move_actual: number; move_target: number;
    achieve_pct: number; equipment: Record<string, number>; eq_total: number;
  }[];
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().then((j) => j.detail, () => res.statusText);
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}
const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const api = {
  meta: () => req<Meta>("/api/hub/meta"),
  overview: (area: string) => req<Overview>(`/api/hub/overview?area=${encodeURIComponent(area)}`),

  conversations: () => req<ConvHead[]>("/api/hub/conversations"),
  conversation: (id: string) => req<Conversation>(`/api/hub/conversations/${id}`),
  deleteConversation: (id: string) => req(`/api/hub/conversations/${id}`, { method: "DELETE" }),

  skills: () => req<Skill[]>("/api/hub/skills"),
  createSkill: (s: SkillInput) => req<Skill>("/api/hub/skills", json("POST", s)),
  updateSkill: (id: string, s: SkillInput) => req<Skill>(`/api/hub/skills/${id}`, json("PUT", s)),
  deleteSkill: (id: string) => req(`/api/hub/skills/${id}`, { method: "DELETE" }),

  events: () => req<HubEvent[]>("/api/hub/events"),
  createEvent: (e: EventInput) => req<HubEvent>("/api/hub/events", json("POST", e)),
  updateEvent: (id: string, e: EventInput) => req<HubEvent>(`/api/hub/events/${id}`, json("PUT", e)),
  toggleEvent: (id: string, enabled: boolean) => req<HubEvent>(`/api/hub/events/${id}`, json("PATCH", { enabled })),
  deleteEvent: (id: string) => req(`/api/hub/events/${id}`, { method: "DELETE" }),
  runEvent: (id: string) => req<HubEvent>(`/api/hub/events/${id}/run`, { method: "POST" }),
};

// ── 채팅 스트리밍 (SSE over fetch) ─────────────────────────────

export interface ChatRequest {
  messages: { role: "user" | "assistant"; content: string }[];
  conversation_id: string | null;
  agent_id: string;
  skill_id: string | null;
}
export interface ChatHandlers {
  onMeta: (conversationId: string) => void;
  onDelta: (text: string) => void;
  onToolStart: (run: ToolRun & { id: string }) => void;
  onToolEnd: (id: string, ms: number, ok: boolean) => void;
  onError: (message: string) => void;
}

export async function streamChat(body: ChatRequest, h: ChatHandlers, signal?: AbortSignal) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") return;
      let ev: any;
      try { ev = JSON.parse(payload); } catch { continue; }
      switch (ev.type) {
        case "meta": h.onMeta(ev.conversation_id); break;
        case "delta": h.onDelta(ev.delta); break;
        case "tool_start": h.onToolStart({ id: ev.id, name: ev.name, args: ev.args, ms: null, ok: null }); break;
        case "tool_end": h.onToolEnd(ev.id, ev.ms, ev.ok); break;
        case "error": h.onError(ev.message); break;
      }
    }
  }
}
