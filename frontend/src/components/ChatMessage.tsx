import Markdown from "react-markdown";
import type { ChatMessage as ChatMessageType } from "../types";
import { parseCitations } from "../utils/parseCitations";
import CitationBadge from "./CitationBadge";

interface Props {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-3 animate-fade-in">
        <div className="bg-ink-600 rounded-2xl rounded-br-sm px-4 py-2 max-w-[85%]">
          <p className="text-sm whitespace-pre-wrap text-white">{message.content}</p>
        </div>
      </div>
    );
  }

  const segments = parseCitations(message.content, message.citations ?? []);

  const sourceLabel =
    message.source_type === "mixed"
      ? "Archive + Web"
      : message.source_type === "web_fallback"
        ? "Web sources"
        : null;

  return (
    <div className="flex justify-start mb-3 animate-fade-in">
      <div className="bg-stone-800/80 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
        <div className="text-sm prose prose-invert prose-sm max-w-none prose-p:text-stone-200 prose-strong:text-stone-100">
          {segments.map((seg, i) =>
            seg.type === "text" ? (
              <Markdown key={i}>{seg.content}</Markdown>
            ) : (
              <CitationBadge key={i} citation={seg.citation} />
            )
          )}
        </div>
        {sourceLabel && (
          <div className="mt-2 pt-2 border-t border-stone-700/50">
            <span className="text-xs text-stone-500 font-medium tracking-wide">{sourceLabel}</span>
          </div>
        )}
      </div>
    </div>
  );
}
