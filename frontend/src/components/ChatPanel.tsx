import { useRef, useEffect } from "react";
import { useAppStore } from "../stores/useAppStore";
import ChatMessage from "./ChatMessage";
import CategoryFilter from "./CategoryFilter";

export default function ChatPanel() {
  const messages = useAppStore((s) => s.messages);
  const isQuerying = useAppStore((s) => s.isQuerying);
  const queryError = useAppStore((s) => s.queryError);
  const chatInput = useAppStore((s) => s.chatInput);
  const setChatInput = useAppStore((s) => s.setChatInput);
  const sendQuery = useAppStore((s) => s.sendQuery);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, isQuerying]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = chatInput.trim();
    if (!trimmed || isQuerying) return;
    setChatInput("");
    sendQuery(trimmed);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm text-center">
              Ask a question about the colonial archives
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isQuerying && (
          <div className="flex justify-start mb-3">
            <div className="bg-gray-800 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        {queryError && (
          <div className="mb-3 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm">{queryError}</p>
            <button
              className="text-red-400 text-xs underline mt-1"
              onClick={() => {
                const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
                if (lastUserMsg) sendQuery(lastUserMsg.content);
              }}
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <CategoryFilter />

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="border-t border-gray-800 px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask about the archives..."
            className="flex-1 bg-gray-800 text-gray-100 rounded-lg px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-gray-500"
            disabled={isQuerying}
          />
          <button
            type="submit"
            disabled={isQuerying || !chatInput.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
