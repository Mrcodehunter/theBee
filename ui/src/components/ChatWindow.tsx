import { useEffect, useRef, useState } from "react";
import { getMessages, streamApprove, streamMessage } from "../api";
import { buildBlocks } from "../render";
import type { ApprovalRequest, ChatMessage, LivePart, ModelInfo, SSEEvent } from "../types";
import ApprovalCard from "./ApprovalCard";
import ChatInput from "./ChatInput";
import MessageBubble from "./MessageBubble";
import ToolCallChip from "./ToolCallChip";

interface Props {
  sessionId: string;
  onActivity: () => void;
  models: ModelInfo[];
  selectedModel: string;
  onSelectModel: (id: string) => void;
}

export default function ChatWindow({ sessionId, onActivity, models, selectedModel, onSelectModel }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [liveParts, setLiveParts] = useState<LivePart[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(true);
  const awaitingApproval = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getMessages(sessionId).then(({ messages, pending_interrupt }) => {
      if (cancelled) return;
      setMessages(messages);
      if (pending_interrupt) {
        awaitingApproval.current = true;
        setLiveParts([{ type: "approval", payload: pending_interrupt, resolved: false }]);
      } else {
        setLiveParts([]);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveParts]);

  function applyEvent(e: SSEEvent) {
    if (e.type === "token") {
      setLiveParts((prev) => {
        const parts = [...prev];
        const last = parts[parts.length - 1];
        if (last && last.type === "text") {
          parts[parts.length - 1] = { type: "text", content: last.content + e.content };
        } else {
          parts.push({ type: "text", content: e.content });
        }
        return parts;
      });
    } else if (e.type === "tool_call") {
      setLiveParts((prev) => [...prev, { type: "tool", name: e.name, args: e.args, result: null }]);
    } else if (e.type === "tool_result") {
      setLiveParts((prev) => {
        const parts = [...prev];
        for (let i = parts.length - 1; i >= 0; i--) {
          const p = parts[i];
          if (p.type === "tool" && p.name === e.name && p.result === null) {
            parts[i] = { ...p, result: e.content };
            break;
          }
        }
        return parts;
      });
    } else if (e.type === "approval_request") {
      awaitingApproval.current = true;
      const payload: ApprovalRequest = e;
      setLiveParts((prev) => [...prev, { type: "approval", payload, resolved: false }]);
      setIsStreaming(false);
    } else if (e.type === "error") {
      setLiveParts((prev) => [...prev, { type: "text", content: `⚠️ ${e.message}` }]);
    }
  }

  function afterStreamEnds() {
    if (awaitingApproval.current) {
      // Paused waiting for a human decision; leave liveParts showing the card.
      setIsStreaming(false);
      return;
    }
    getMessages(sessionId).then(({ messages }) => {
      setMessages(messages);
      setLiveParts([]);
      setIsStreaming(false);
      onActivity();
    });
  }

  function handleSend(content: string) {
    setMessages((prev) => [...prev, { role: "user", content }]);
    setLiveParts([]);
    awaitingApproval.current = false;
    setIsStreaming(true);
    streamMessage(sessionId, content, selectedModel, applyEvent)
      .then(afterStreamEnds)
      .catch((err) => {
        setLiveParts((prev) => [...prev, { type: "text", content: `⚠️ ${err.message}` }]);
        setIsStreaming(false);
      });
  }

  function handleDecide(approved: boolean) {
    setLiveParts((prev) => {
      const parts = [...prev];
      for (let i = parts.length - 1; i >= 0; i--) {
        if (parts[i].type === "approval" && !(parts[i] as { resolved: boolean }).resolved) {
          parts[i] = { ...parts[i], resolved: true, approved } as LivePart;
          break;
        }
      }
      return parts;
    });
    awaitingApproval.current = false;
    setIsStreaming(true);
    streamApprove(sessionId, approved, selectedModel, applyEvent)
      .then(afterStreamEnds)
      .catch((err) => {
        setLiveParts((prev) => [...prev, { type: "text", content: `⚠️ ${err.message}` }]);
        setIsStreaming(false);
      });
  }

  if (loading) {
    return <div className="flex flex-1 items-center justify-center text-neutral-500">Loading…</div>;
  }

  const blocks = buildBlocks(messages);

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-end border-b border-neutral-800 px-4 py-2">
        <select
          value={selectedModel}
          onChange={(e) => onSelectModel(e.target.value)}
          className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs text-neutral-200 outline-none"
        >
          {models.map((m) => (
            <option
              key={m.id}
              value={m.id}
              disabled={!m.available}
              title={m.available ? undefined : "Not configured on the backend"}
            >
              {m.label}
              {m.available ? "" : " (unavailable)"}
            </option>
          ))}
        </select>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-2">
          {blocks.length === 0 && liveParts.length === 0 && (
            <div className="mt-24 text-center text-neutral-500">Ask the agent to do something in your project.</div>
          )}

          {blocks.map((b) =>
            b.kind === "tool" ? (
              <ToolCallChip key={b.key} name={b.name!} args={b.args!} result={b.result ?? null} />
            ) : (
              <MessageBubble key={b.key} role={b.kind} content={b.content ?? ""} />
            )
          )}

          {liveParts.map((p, i) =>
            p.type === "text" ? (
              <MessageBubble key={`live-${i}`} role="assistant" content={p.content} />
            ) : p.type === "tool" ? (
              <ToolCallChip key={`live-${i}`} name={p.name} args={p.args} result={p.result} />
            ) : (
              <ApprovalCard
                key={`live-${i}`}
                request={p.payload}
                resolved={p.resolved}
                approved={p.approved}
                onDecide={handleDecide}
              />
            )
          )}

          {isStreaming && liveParts.length === 0 && (
            <div className="text-sm text-neutral-500">
              <span className="animate-pulse">Thinking…</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>
      <ChatInput disabled={isStreaming} onSend={handleSend} />
    </div>
  );
}
