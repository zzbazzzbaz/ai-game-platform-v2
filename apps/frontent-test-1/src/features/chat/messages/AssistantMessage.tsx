import { Gamepad2 } from "lucide-react";

import { MarkdownText } from "./MarkdownText";
import { ToolCallCard } from "./ToolCallCard";
import { contentToText, type ChatMessage } from "./message-utils";

/** AI 消息：Markdown 正文 + 工具调用卡片。 */
export function AssistantMessage({
  message,
  toolResults,
  isLoading,
}: {
  message: ChatMessage;
  toolResults: Map<string, ChatMessage>;
  isLoading: boolean;
}) {
  const text = contentToText(message.content);
  const toolCalls = message.tool_calls ?? [];
  const hasContent = text.length > 0;

  if (!hasContent && toolCalls.length === 0) return null;

  return (
    <div className="flex gap-3">
      <span className="bg-primary text-primary-foreground mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full">
        <Gamepad2 className="size-4" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        {hasContent && <MarkdownText content={text} />}
        {toolCalls.map((toolCall, index) => (
          <ToolCallCard
            key={toolCall.id ?? `${message.id ?? "msg"}-tool-${index}`}
            toolCall={toolCall}
            result={toolCall.id ? toolResults.get(toolCall.id) : undefined}
            pending={isLoading && toolCall.id !== undefined && !toolResults.has(toolCall.id)}
          />
        ))}
      </div>
    </div>
  );
}
