import type { ApprovalRequest, ChatMessage, ModelInfo, SSEEvent, Session } from "./types";

const API_BASE = "http://localhost:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function createSession(): Promise<Session> {
  return fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  }).then(json<Session>);
}

export function listSessions(): Promise<Session[]> {
  return fetch(`${API_BASE}/api/sessions`).then(json<Session[]>);
}

export function deleteSession(id: string): Promise<void> {
  return fetch(`${API_BASE}/api/sessions/${id}`, { method: "DELETE" }).then(() => undefined);
}

export function listModels(): Promise<ModelInfo[]> {
  return fetch(`${API_BASE}/api/models`).then(json<ModelInfo[]>);
}

export function getMessages(
  id: string
): Promise<{ messages: ChatMessage[]; pending_interrupt: ApprovalRequest | null }> {
  return fetch(`${API_BASE}/api/sessions/${id}/messages`).then(
    json<{ messages: ChatMessage[]; pending_interrupt: ApprovalRequest | null }>
  );
}

/** Parse a raw SSE byte stream into {event, data} pairs and hand each to onEvent. */
async function consumeSSE(res: Response, onEvent: (e: SSEEvent) => void): Promise<void> {
  if (!res.ok || !res.body) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      let eventName = "message";
      let dataLine = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!dataLine) continue;
      const data = JSON.parse(dataLine);
      onEvent({ type: eventName, ...data } as SSEEvent);
    }
  }
}

export function streamMessage(
  sessionId: string,
  content: string,
  model: string,
  onEvent: (e: SSEEvent) => void
): Promise<void> {
  return fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, model }),
  }).then((res) => consumeSSE(res, onEvent));
}

export function streamApprove(
  sessionId: string,
  approved: boolean,
  model: string,
  onEvent: (e: SSEEvent) => void
): Promise<void> {
  return fetch(`${API_BASE}/api/sessions/${sessionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, model }),
  }).then((res) => consumeSSE(res, onEvent));
}
