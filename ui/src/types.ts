export interface Session {
  id: string;
  title: string;
  created_at: string;
}

export type ChatRole = "user" | "assistant" | "tool";

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  tool_calls?: ToolCall[];
  name?: string;
}

export interface ApprovalRequest {
  kind: "approval";
  action: "write_file" | "run_command";
  path?: string;
  command?: string;
  summary: string;
  preview?: string;
}

export type LivePart =
  | { type: "text"; content: string }
  | { type: "tool"; name: string; args: Record<string, unknown>; result: string | null }
  | { type: "approval"; payload: ApprovalRequest; resolved: boolean; approved?: boolean };

export type SSEEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; content: string }
  | ({ type: "approval_request" } & ApprovalRequest)
  | { type: "done" }
  | { type: "error"; message: string };
