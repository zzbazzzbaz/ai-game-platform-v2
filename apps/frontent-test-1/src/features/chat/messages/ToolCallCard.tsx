import * as React from "react";
import {
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Database,
  FilePen,
  FilePlus,
  FileText,
  FolderTree,
  ListTodo,
  LoaderCircle,
  Rocket,
  Terminal,
  Wrench,
} from "lucide-react";

import { cn } from "@/lib/utils";

import { contentToText, toolCallSummary, type ChatMessage, type ChatToolCall } from "./message-utils";

interface ToolMeta {
  label: string;
  icon: typeof Terminal;
}

const TOOL_META: Record<string, ToolMeta> = {
  execute: { label: "终端执行", icon: Terminal },
  ls: { label: "查看目录", icon: FolderTree },
  read_file: { label: "读取文件", icon: FileText },
  write_file: { label: "写入文件", icon: FilePlus },
  edit_file: { label: "修改文件", icon: FilePen },
  write_todos: { label: "任务清单", icon: ListTodo },
  provision_database: { label: "开通数据库", icon: Database },
  publish_game: { label: "发布游戏", icon: Rocket },
};

function toolMeta(name: string): ToolMeta {
  return TOOL_META[name] ?? { label: name, icon: Wrench };
}

function stringifyArgs(args: unknown): string {
  if (args === null || args === undefined) return "（无参数）";
  try {
    return JSON.stringify(args, null, 2);
  } catch {
    return String(args);
  }
}

/** 工具调用卡片：折叠展示参数与结果。 */
export function ToolCallCard({
  toolCall,
  result,
  pending,
}: {
  toolCall: ChatToolCall;
  result?: ChatMessage;
  pending: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const meta = toolMeta(toolCall.name);
  const summary = toolCallSummary(toolCall);
  const resultText = result ? contentToText(result.content) : "";
  const failed = result?.status === "error";

  return (
    <div className="bg-muted/40 rounded-lg border text-xs">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        {open ? (
          <ChevronDown className="text-muted-foreground size-3.5 shrink-0" />
        ) : (
          <ChevronRight className="text-muted-foreground size-3.5 shrink-0" />
        )}
        <meta.icon className="text-muted-foreground size-3.5 shrink-0" />
        <span className="font-medium">{meta.label}</span>
        {summary && (
          <code className="text-muted-foreground truncate font-mono text-[0.6875rem]">{summary}</code>
        )}
        <span className="ml-auto shrink-0">
          {pending ? (
            <LoaderCircle className="text-muted-foreground size-3.5 animate-spin" />
          ) : failed ? (
            <CircleAlert className="text-destructive size-3.5" />
          ) : null}
        </span>
      </button>
      {open && (
        <div className="flex flex-col gap-2 border-t px-3 py-2">
          <div>
            <p className="text-muted-foreground mb-1">参数</p>
            <pre className="bg-background/60 max-h-48 overflow-auto rounded p-2 font-mono text-[0.6875rem] whitespace-pre-wrap">
              {stringifyArgs(toolCall.args)}
            </pre>
          </div>
          {result && (
            <div>
              <p className="text-muted-foreground mb-1">结果{failed ? "（失败）" : ""}</p>
              <pre
                className={cn(
                  "bg-background/60 max-h-64 overflow-auto rounded p-2 font-mono text-[0.6875rem] whitespace-pre-wrap",
                  failed && "text-destructive",
                )}
              >
                {resultText || "（空）"}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
