import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Sparkles, Loader2, Mic, MicOff } from "lucide-react";
import { aiApi } from "../services/api";
import type { AIResponse } from "../types";

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
  intent?: string;
  source?: string;
}

const SUGGESTIONS = [
  "Where is Amit seated?",
  "Show available seats on Floor 3",
  "How many seats are occupied for Project Indigo?",
  "Which project is sara@ethara.ai assigned to?",
  "Who is sitting near me? My email is test@ethara.ai",
  "Allocate a seat for a new employee joining today",
];

let msgId = 0;

export function AIAssistant() {
  const [sessionId] = useState(() =>
    Math.random().toString(36).substring(2, 15),
  );
  const [messages, setMessages] = useState<Message[]>([
    {
      id: ++msgId,
      role: "assistant",
      text: 'Hello! I\'m the Ethara AI assistant. Ask me anything about seats, employees, or projects.\n\nTry: "Where is Amit seated?" or "Show available seats on Floor 2"',
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => (prev ? prev + " " + transcript : transcript));
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert(
        "Speech Recognition is not supported in this browser. Please try Chrome, Edge, or Safari.",
      );
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  async function send(query: string) {
    if (!query.trim() || loading) return;
    const userMsg: Message = { id: ++msgId, role: "user", text: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: AIResponse = await aiApi.query({
        query,
        session_id: sessionId,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: ++msgId,
          role: "assistant",
          text: res.answer,
          intent: res.intent,
          source: res.source,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: ++msgId,
          role: "assistant",
          text: "Sorry, I couldn't connect to the backend. Make sure the API is running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ethara-primary to-ethara-secondary flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">AI Assistant</h2>
          <p className="text-ethara-muted text-sm">
            Powered by Grok (xAI) — queries live Neon data
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-ethara-success bg-ethara-success/10 border border-ethara-success/20 px-2.5 py-1 rounded-full">
          <span className="w-1.5 h-1.5 bg-ethara-success rounded-full animate-pulse-slow" />
          Online
        </div>
      </div>

      {/* Message area */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {m.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-ethara-primary/20 to-ethara-secondary/20 border border-ethara-primary/20 flex items-center justify-center shrink-0 mt-1">
                <Bot className="w-4 h-4 text-ethara-primary" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                m.role === "user"
                  ? "bg-ethara-primary/20 border border-ethara-primary/30 rounded-tr-sm"
                  : "bg-ethara-card border border-ethara-border rounded-tl-sm"
              }`}
            >
              <p className="text-sm text-white whitespace-pre-wrap leading-relaxed">
                {m.text}
              </p>
              {m.role === "assistant" && m.intent && m.intent !== "unknown" && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-ethara-border/50">
                  <span className="text-[10px] text-ethara-muted">
                    Intent:{" "}
                    <span className="text-ethara-accent">{m.intent}</span>
                  </span>
                  {m.source && (
                    <span className="text-[10px] text-ethara-muted">
                      · Source:{" "}
                      <span className="text-ethara-muted/70">{m.source}</span>
                    </span>
                  )}
                </div>
              )}
            </div>
            {m.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-ethara-hover border border-ethara-border flex items-center justify-center shrink-0 mt-1">
                <User className="w-4 h-4 text-ethara-muted" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-ethara-card border border-ethara-border flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-ethara-primary" />
            </div>
            <div className="bg-ethara-card border border-ethara-border rounded-2xl rounded-tl-sm px-4 py-3">
              <Loader2 className="w-4 h-4 text-ethara-primary animate-spin" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className="mb-4">
          <p className="text-xs text-ethara-muted mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Try these questions
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs bg-ethara-hover border border-ethara-border hover:border-ethara-primary/40 text-ethara-muted hover:text-white px-3 py-1.5 rounded-full transition-all duration-200"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
          placeholder="Ask about seats, employees, or projects…"
          className="ethara-input flex-1"
          disabled={loading}
        />
        <button
          onClick={toggleListening}
          disabled={loading}
          type="button"
          title={isListening ? "Stop listening" : "Start voice dictation"}
          className={`px-4 py-2.5 rounded-lg border transition-all duration-300 flex items-center justify-center cursor-pointer ${
            isListening
              ? "bg-fuchsia-600 hover:bg-fuchsia-700 border-fuchsia-500 text-white animate-pulse shadow-[0_0_15px_rgba(219,39,119,0.5)]"
              : "bg-ethara-hover hover:bg-ethara-border border-ethara-border text-ethara-muted hover:text-white"
          }`}
        >
          {isListening ? (
            <MicOff className="w-4 h-4" />
          ) : (
            <Mic className="w-4 h-4" />
          )}
        </button>
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="ethara-btn-primary px-4 py-2.5 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
