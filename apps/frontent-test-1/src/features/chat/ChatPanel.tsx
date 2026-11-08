import * as React from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { ArrowUp, CircleAlert, LoaderCircle, Paperclip, Square, X } from "lucide-react";

import { uploadAsset, type AssetResponse } from "@/api/assets";
import { ensureFreshToken } from "@/api/client";
import { createLangGraphClient } from "@/api/langgraph";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AssistantMessage } from "@/features/chat/messages/AssistantMessage";
import { HumanMessage } from "@/features/chat/messages/HumanMessage";
import {
  indexToolResults,
  isRenderableMessage,
  type ChatMessage,
} from "@/features/chat/messages/message-utils";
import { env } from "@/lib/env";

interface ChatState {
  messages: Message[];
}

const DO_NOT_RENDER_PREFIX = "do-not-render-";

/** 为中断（停止）后的悬空工具调用补齐响应，保证可以继续对话。 */
function ensureToolCallsHaveResponses(messages: ChatMessage[]): ChatMessage[] {
  const missing: ChatMessage[] = [];
  messages.forEach((message, index) => {
    if (message.type !== "ai" || !message.tool_calls?.length) return;
    const following = messages[index + 1];
    if (following && following.type === "tool") return;
    for (const toolCall of message.tool_calls) {
      missing.push({
        type: "tool",
        tool_call_id: toolCall.id ?? "",
        id: `${DO_NOT_RENDER_PREFIX}${crypto.randomUUID()}`,
        name: toolCall.name,
        content: "（已跳过）",
      });
    }
  });
  return missing;
}

function errorText(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string" && error) return error;
  return "生成失败，请重试";
}

function assetViewHint(contentType: string, path: string): string {
  const quoted = `'${path}'`;
  if (contentType.startsWith("text/")) {
    return `cat ${quoted}`;
  }
  if (contentType === "application/json") {
    return `cat ${quoted}`;
  }
  if (contentType.startsWith("image/")) {
    return `ls -l ${quoted}（图片请作为素材引用，不要 cat）`;
  }
  if (contentType.startsWith("audio/") || contentType.startsWith("video/")) {
    return `ls -l ${quoted}（不要 cat）`;
  }
  return `file ${quoted}（不要 cat）`;
}

function assetRecord(asset: AssetResponse): string {
  return [
    `- 文件名：${asset.filename}`,
    `- 沙盒路径：${asset.sandbox_path}`,
    `- 类型：${asset.content_type}，大小：${asset.size} 字节`,
    "- 该目录为只读；如需修改，请先复制到 /workspace/work/ 后再改。",
    `- 查看方式：${assetViewHint(asset.content_type, asset.sandbox_path)}`,
  ].join("\n");
}

function composeMessage(text: string, assets: AssetResponse[]): string {
  if (assets.length === 0) return text;
  return `${text}\n\n【附件记录】\n${assets.map(assetRecord).join("\n")}`;
}

export function ChatPanel({
  gameId,
  threadId,
  suggestions,
}: {
  gameId: string;
  threadId: string;
  suggestions: string[];
}) {
  const [input, setInput] = React.useState("");
  const [lastSubmitted, setLastSubmitted] = React.useState<string | null>(null);
  const [pendingAssets, setPendingAssets] = React.useState<AssetResponse[]>([]);
  const [uploadingCount, setUploadingCount] = React.useState(0);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const client = React.useMemo(() => createLangGraphClient(), []);

  const stream = useStream<ChatState>({
    client,
    assistantId: env.lgAssistantId,
    threadId,
    fetchStateHistory: true,
  });

  const streamMessages = stream.messages;
  const rawMessages = React.useMemo(
    () => (streamMessages ?? []) as unknown as ChatMessage[],
    [streamMessages],
  );
  const messages = React.useMemo(
    () => rawMessages.filter((message) => isRenderableMessage(message) && message.type !== "system"),
    [rawMessages],
  );
  const toolResults = React.useMemo(() => indexToolResults(messages), [messages]);
  const isLoading = stream.isLoading;
  const error = stream.error;

  // 新消息到达时自动贴底（用户上翻查看时不打断）
  React.useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    const distance = element.scrollHeight - element.scrollTop - element.clientHeight;
    if (distance < 160) {
      element.scrollTop = element.scrollHeight;
    }
  }, [messages.length, isLoading]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadError(null);
    const selected = Array.from(files);
    setUploadingCount((count) => count + selected.length);
    for (const file of selected) {
      try {
        const asset = await uploadAsset(gameId, file);
        setPendingAssets((current) => [...current, asset]);
      } catch (error) {
        setUploadError(errorText(error));
      } finally {
        setUploadingCount((count) => Math.max(0, count - 1));
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeAsset = (assetId: string) => {
    setPendingAssets((current) => current.filter((asset) => asset.asset_id !== assetId));
  };

  const submit = (text: string) => {
    const trimmed = text.trim();
    if ((!trimmed && pendingAssets.length === 0) || isLoading || uploadingCount > 0) return;

    // 长时间停留后 access_token 可能已过期：提交前先确保续期
    void ensureFreshToken();

    const content = composeMessage(trimmed || "请查看我上传的附件。", pendingAssets);
    const toolResponses = ensureToolCallsHaveResponses(messages);
    const humanMessage = {
      id: crypto.randomUUID(),
      type: "human",
      content,
    };

    stream.submit(
      { messages: [...toolResponses, humanMessage] } as Partial<ChatState>,
      {
        streamMode: ["values"],
        streamSubgraphs: true,
        streamResumable: true,
        optimisticValues: (prev) => ({
          ...prev,
          messages: [
            ...((prev as ChatState).messages ?? []),
            ...toolResponses,
            humanMessage,
          ] as Message[],
        }),
      },
    );
    setLastSubmitted(content);
    setInput("");
    setPendingAssets([]);
    setUploadError(null);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit(input);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit(input);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={scrollRef} className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && !isLoading ? (
          <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center gap-4 text-center">
            <div>
              <p className="font-medium">描述你想玩的游戏</p>
              <p className="text-muted-foreground mt-1 text-sm">
                AI 会在沙盒里编写、运行并调试，你可以随时在右侧预览
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  onClick={() => setInput(suggestion)}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((message, index) => {
              if (message.type === "human") {
                return <HumanMessage key={message.id ?? `human-${index}`} message={message} />;
              }
              if (message.type === "ai") {
                return (
                  <AssistantMessage
                    key={message.id ?? `ai-${index}`}
                    message={message}
                    toolResults={toolResults}
                    isLoading={isLoading}
                  />
                );
              }
              return null;
            })}
            {isLoading && (
              <div className="text-muted-foreground flex items-center gap-2 text-xs">
                <LoaderCircle className="size-3.5 animate-spin" />
                正在生成…
              </div>
            )}
            {error !== null && error !== undefined && (
              <div className="border-destructive/40 bg-destructive/5 flex items-start gap-2 rounded-lg border p-3 text-sm">
                <CircleAlert className="text-destructive mt-0.5 size-4 shrink-0" />
                <div className="flex flex-col gap-2">
                  <p className="text-destructive">{errorText(error)}</p>
                  {lastSubmitted !== null && !isLoading && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="self-start"
                      onClick={() => submit(lastSubmitted)}
                    >
                      重发上一条
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="border-t p-3">
        {(pendingAssets.length > 0 || uploadingCount > 0 || uploadError !== null) && (
          <div className="mx-auto mb-2 flex max-w-3xl flex-wrap items-center gap-2">
            {pendingAssets.map((asset) => (
              <span
                key={asset.asset_id}
                className="bg-muted flex items-center gap-1 rounded-full px-2 py-1 text-xs"
              >
                <Paperclip className="size-3 shrink-0" />
                <span className="max-w-48 truncate">{asset.filename}</span>
                <button
                  type="button"
                  aria-label={`移除 ${asset.filename}`}
                  onClick={() => removeAsset(asset.asset_id)}
                  className="hover:text-destructive"
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
            {uploadingCount > 0 && (
              <span className="text-muted-foreground flex items-center gap-1 text-xs">
                <LoaderCircle className="size-3 animate-spin" />
                正在上传…
              </span>
            )}
            {uploadError !== null && (
              <span className="text-destructive text-xs">{uploadError}</span>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(event) => void handleFiles(event.target.files)}
          />
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="上传附件"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || uploadingCount > 0}
          >
            <Paperclip />
          </Button>
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="描述你想做的游戏，或继续提修改意见（Enter 发送，Shift+Enter 换行）"
            className="max-h-40 min-h-[2.5rem] flex-1 resize-none"
            rows={1}
            disabled={isLoading}
          />
          {isLoading ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              aria-label="停止生成"
              onClick={() => stream.stop()}
            >
              <Square />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              aria-label="发送"
              disabled={
                (input.trim().length === 0 && pendingAssets.length === 0) || uploadingCount > 0
              }
            >
              <ArrowUp />
            </Button>
          )}
        </form>
      </div>
    </div>
  );
}
