import type { ChatMessage } from "./types";

export interface RenderBlock {
  key: string;
  kind: "user" | "assistant" | "tool";
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string | null;
}

/** Flatten the backend's raw message list (user/assistant/tool) into blocks
 * that pair each tool call with its result, in the order they happened. */
export function buildBlocks(messages: ChatMessage[]): RenderBlock[] {
  const blocks: RenderBlock[] = [];
  const pendingTools: RenderBlock[] = [];
  let k = 0;

  for (const msg of messages) {
    if (msg.role === "user") {
      blocks.push({ key: `b${k++}`, kind: "user", content: msg.content });
    } else if (msg.role === "assistant") {
      for (const tc of msg.tool_calls ?? []) {
        const block: RenderBlock = { key: `b${k++}`, kind: "tool", name: tc.name, args: tc.args, result: null };
        blocks.push(block);
        pendingTools.push(block);
      }
      if (msg.content) {
        blocks.push({ key: `b${k++}`, kind: "assistant", content: msg.content });
      }
    } else if (msg.role === "tool") {
      const match = pendingTools.shift();
      if (match) match.result = msg.content;
    }
  }
  return blocks;
}
