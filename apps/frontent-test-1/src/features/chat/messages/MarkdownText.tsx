import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import css from "react-syntax-highlighter/dist/esm/languages/prism/css";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

import { useTheme } from "@/theme/ThemeProvider";

// 只注册游戏开发常用的几种语言，避免打包全部 Prism 语言
SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("js", javascript);
SyntaxHighlighter.registerLanguage("typescript", typescript);
SyntaxHighlighter.registerLanguage("ts", typescript);
SyntaxHighlighter.registerLanguage("json", json);
SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("sh", bash);
SyntaxHighlighter.registerLanguage("shell", bash);
SyntaxHighlighter.registerLanguage("css", css);
SyntaxHighlighter.registerLanguage("markdown", markdown);

/** 对话内容渲染：GFM Markdown + 代码高亮。 */
export const MarkdownText = React.memo(function MarkdownText({ content }: { content: string }) {
  const { resolvedTheme } = useTheme();
  const codeStyle = resolvedTheme === "dark" ? oneDark : oneLight;

  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className ?? "");
            const text = String(children).replace(/\n$/, "");
            if (match || text.includes("\n")) {
              return (
                <SyntaxHighlighter
                  language={match?.[1] ?? "text"}
                  style={codeStyle}
                  customStyle={{
                    margin: 0,
                    borderRadius: "0.5rem",
                    fontSize: "0.8125rem",
                  }}
                  wrapLongLines
                >
                  {text}
                </SyntaxHighlighter>
              );
            }
            return (
              <code className="bg-muted rounded px-1 py-0.5 font-mono text-[0.8125rem]" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
