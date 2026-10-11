import { contentToText, type ChatMessage } from "./message-utils";

/** 用户消息：右对齐气泡。 */
export function HumanMessage({ message }: { message: ChatMessage }) {
  const text = contentToText(message.content);
  if (!text) return null;

  return (
    <div className="flex justify-end">
      <p className="bg-muted max-w-[85%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap">
        {text}
      </p>
    </div>
  );
}
