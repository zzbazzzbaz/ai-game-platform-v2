/** 对话消息读取工具：兼容字符串 / 内容块 / 工具调用结构。 */

export interface ChatToolCall {
  id?: string;
  name: string;
  args?: unknown;
}

export interface ChatMessage {
  id?: string;
  type: string;
  content?: unknown;
  tool_calls?: ChatToolCall[];
  tool_call_id?: string;
  name?: string;
  status?: string;
}

/** 平台侧为工具补齐的空响应，不渲染。 */
const DO_NOT_RENDER_PREFIX = "do-not-render-";

export function contentToText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block === "string") return block;
        if (block !== null && typeof block === "object") {
          const text = (block as Record<string, unknown>).text;
          if (typeof text === "string") return text;
        }
        return "";
      })
      .join("")
      .trim();
  }
  if (content === null || content === undefined) return "";
  return String(content);
}

export function isRenderableMessage(message: ChatMessage): boolean {
  return !(message.id ?? "").startsWith(DO_NOT_RENDER_PREFIX);
}

/** tool_call_id → 工具结果消息 */
export function indexToolResults(messages: ChatMessage[]): Map<string, ChatMessage> {
  const results = new Map<string, ChatMessage>();
  for (const message of messages) {
    if (message.type === "tool" && message.tool_call_id) {
      results.set(message.tool_call_id, message);
    }
  }
  return results;
}

/** 工具调用的一句话摘要（用于折叠状态展示）。 */
export function toolCallSummary(toolCall: ChatToolCall): string {
  const args = toolCall.args;
  if (args === null || typeof args !== "object") return "";
  const record = args as Record<string, unknown>;
  for (const key of ["command", "file_path", "path", "pattern", "name", "query"]) {
    const value = record[key];
    if (typeof value === "string" && value) {
      return value.length > 120 ? `${value.slice(0, 120)}…` : value;
    }
  }
  if (Array.isArray(record.todos)) {
    return `${record.todos.length} 项任务`;
  }
  return "";
}
