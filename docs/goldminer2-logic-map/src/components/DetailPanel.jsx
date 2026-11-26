import React from "react";
import { ArrowLeft, CircleHelp, Copy, Sparkles, X } from "lucide-react";

export default function DetailPanel({ selection, view, open, onClose, ui, legend }) {
  const [promptOpen, setPromptOpen] = React.useState(false);
  const [prompt, setPrompt] = React.useState("");
  const [copied, setCopied] = React.useState(false);

  const node = selection?.kind === "node" ? selection.node : null;
  const edge = selection?.kind === "edge" ? selection.edge : null;
  const edgeContent = edge?.data?.content;

  const source = edge ? view.nodes.find((item) => item.id === edge.source) : null;
  const target = edge ? view.nodes.find((item) => item.id === edge.target) : null;

  const title = node
    ? node.data.title
    : edge
      ? edgeContent?.title || `${source?.title ?? edge.source} → ${target?.title ?? edge.target}`
      : "";

  const detail = node
    ? node.data.detail
    : edge
      ? edgeContent?.detail ||
        `从「${source?.title ?? edge.source}」走到「${target?.title ?? edge.target}」`
      : "";

  const attributes = node
    ? node.data.attributes ?? []
    : edgeContent?.attributes ?? [];

  const selectionKey = node?.id ?? edge?.id ?? "none";

  React.useEffect(() => {
    setPromptOpen(false);
    setCopied(false);
    setPrompt(node || edge ? `【${view.tab}·${title}】${detail} 我想改成：` : "");
  }, [selectionKey, view.tab, title, detail, node, edge]);

  if (!node && !edge) {
    return (
      <aside className={`detail-panel ${open ? "is-open" : ""}`}>
        <div className="detail-card overview-card">
          <div className="overview-head">
            <div className="detail-eyebrow">
              <CircleHelp size={13} />
              {ui.info}
            </div>
            <button className="icon-btn" onClick={onClose} aria-label={ui.close}>
              <X size={15} />
            </button>
          </div>

          <h3>{ui.overviewTitle}</h3>
          <p className="detail-desc">{ui.overviewDesc}</p>

          <div className="section-label">{ui.colorTitle}</div>
          <div className="legend-list">
            {legend.map((item) => (
              <div className="legend-item" key={item.label}>
                <span
                  className={`legend-dot ${item.dashed ? "is-dashed" : ""}`}
                  style={{ "--legend-color": item.color }}
                />
                {item.label}
              </div>
            ))}
          </div>

          <div className="overview-note">{ui.overviewNote}</div>
        </div>
      </aside>
    );
  }

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <aside className={`detail-panel ${open ? "is-open" : ""}`}>
      <div className="detail-card">
        <div className="detail-top">
          <span className="detail-title">{title}</span>
          <button className="icon-btn" onClick={onClose} aria-label={ui.close}>
            <X size={15} />
          </button>
        </div>

        <p className="detail-desc">{detail}</p>

        {attributes.length > 0 && (
          <div className="detail-values">
            {attributes.map((value) => (
              <span className="value-chip" key={value}>
                {value}
              </span>
            ))}
          </div>
        )}

        <button
          className="primary-btn"
          onClick={() => {
            setPromptOpen(true);
            setCopied(false);
          }}
        >
          <Sparkles size={15} />
          {ui.cta}
        </button>

        {promptOpen && (
          <div className="prompt-box">
            <div className="prompt-head">
              <span>{ui.promptHead}</span>
              <button className="icon-btn" onClick={() => setPromptOpen(false)}>
                <ArrowLeft size={14} />
              </button>
            </div>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={5}
              spellCheck={false}
            />
            <div className="prompt-actions">
              <span className="prompt-hint">{ui.promptHint}</span>
              <button className="copy-btn" onClick={copyPrompt}>
                <Copy size={12} />
                {copied ? ui.copied : ui.copy}
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
