"use client";

import { useState, useRef, useEffect } from "react";

// -------------------------------------------------------------------
// Types
// -------------------------------------------------------------------
interface Message {
  role: "user" | "assistant";
  content: string;
}

// -------------------------------------------------------------------
// Configuration
// -------------------------------------------------------------------
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// -------------------------------------------------------------------
// Sub-components
// -------------------------------------------------------------------

/** Meridian branded header */
function Header() {
  return (
    <header className="bg-gradient-to-r from-[var(--meridian-blue)] to-[var(--meridian-blue-dark)] text-white shadow-lg">
      <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
        {/* Logo icon */}
        <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center text-xl font-bold">
          M
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Meridian Electronics
          </h1>
          <p className="text-xs text-blue-200">AI Customer Support</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-blue-200">Online</span>
        </div>
      </div>
    </header>
  );
}

/** Single chat bubble */
function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      {/* Bot avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--meridian-blue)] to-[var(--meridian-accent)] flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0">
          M
        </div>
      )}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl shadow-sm chat-message text-sm leading-relaxed ${isUser
          ? "bg-[var(--meridian-user-bg)] text-[var(--meridian-user-text)] rounded-br-md"
          : "bg-[var(--meridian-bot-bg)] text-[var(--meridian-bot-text)] rounded-bl-md border border-[var(--meridian-border)]"
          }`}
      >
        {/* Render simple markdown-like formatting */}
        {message.content.split("\n").map((line, i) => (
          <p key={i} className={line === "" ? "h-2" : ""}>
            {line}
          </p>
        ))}
      </div>
      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-white text-xs font-bold ml-2 mt-1 shrink-0">
          You
        </div>
      )}
    </div>
  );
}

/** Typing indicator */
function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--meridian-blue)] to-[var(--meridian-accent)] flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0">
        M
      </div>
      <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-md border border-[var(--meridian-border)] shadow-sm">
        <div className="flex gap-1.5">
          <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          <span className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
        </div>
      </div>
    </div>
  );
}

/** Quick-action suggestion chips */
function SuggestionChips({
  onSelect,
}: {
  onSelect: (text: string) => void;
}) {
  const suggestions = [
    "Browse monitors",
    "Search for keyboards",
    "I want to place an order",
    "Look up my order history",
  ];

  return (
    <div className="flex flex-wrap gap-2 justify-center py-4">
      {suggestions.map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className="px-4 py-2 text-sm rounded-full border border-[var(--meridian-blue-light)] text-[var(--meridian-blue)] bg-white hover:bg-[var(--meridian-blue)] hover:text-white transition-all duration-200 shadow-sm cursor-pointer"
        >
          {s}
        </button>
      ))}
    </div>
  );
}

// -------------------------------------------------------------------
// Main Chat Page
// -------------------------------------------------------------------
export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const sendMessage = async (text?: string) => {
    const content = text || input.trim();
    if (!content || isLoading) return;

    const userMessage: Message = { role: "user", content };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: updatedMessages }),
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I apologize, but I'm having trouble connecting to the server. Please try again in a moment.",
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <Header />

      {/* Chat area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {/* Welcome message when empty */}
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[var(--meridian-blue)] to-[var(--meridian-accent)] flex items-center justify-center text-white text-3xl font-bold shadow-lg">
                M
              </div>
              <h2 className="text-2xl font-semibold text-[var(--meridian-text)] mb-2">
                Welcome to Meridian Support
              </h2>
              <p className="text-[var(--meridian-text-secondary)] max-w-md mx-auto mb-6">
                I can help you browse products, place orders, check order
                status, and more. How can I assist you today?
              </p>
              <SuggestionChips onSelect={(text) => sendMessage(text)} />
            </div>
          )}

          {/* Messages */}
          {messages.map((msg, i) => (
            <ChatBubble key={i} message={msg} />
          ))}

          {/* Typing indicator */}
          {isLoading && <TypingIndicator />}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input area */}
      <footer className="border-t border-[var(--meridian-border)] bg-white">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-end gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-[var(--meridian-border)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--meridian-blue-light)] focus:border-transparent bg-[var(--meridian-bg)] text-[var(--meridian-text)] placeholder:text-[var(--meridian-text-secondary)]"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="px-5 py-3 rounded-xl bg-[var(--meridian-blue)] text-white font-medium text-sm hover:bg-[var(--meridian-blue-dark)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm cursor-pointer"
            >
              {isLoading ? (
                <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                "Send"
              )}
            </button>
          </div>
          <p className="text-xs text-center text-[var(--meridian-text-secondary)] mt-2">
            Powered by AI · Meridian Electronics Customer Support
          </p>
        </div>
      </footer>
    </div>
  );
}
