"use client";

import { Activity, Database, FileText, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { ChatInput } from "../components/ChatInput";
import { MessageList, Message } from "../components/MessageList";
import { SourcePanel } from "../components/SourcePanel";
import { MetricsPanel } from "../components/MetricsPanel";
import { DebugPanel } from "../components/DebugPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
const DEMO_PROMPTS = [
  { label: "Product Count", value: "Có bao nhiêu sản phẩm trong cơ sở dữ liệu?", icon: Database },
  { label: "Top Customers", value: "Top 5 customers by order count.", icon: Activity },
  { label: "FPT Risks", value: "Tóm tắt rủi ro trong báo cáo của FPT.", icon: ShieldCheck },
  { label: "Vinamilk Growth", value: "Chiến lược tăng trưởng của Vinamilk là gì?", icon: FileText },
  { label: "Masan Opportunity", value: "Masan đề cập cơ hội nào trong tài liệu?", icon: FileText },
  { label: "Unsupported", value: "Công thức bí mật sản xuất sữa của Vinamilk là gì?", icon: ShieldCheck }
];

type HealthState = {
  status?: string;
  db_status?: string;
  rag_status?: { chunks_file?: string; chunk_count?: number };
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastResponse, setLastResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [debug, setDebug] = useState(false);
  const [health, setHealth] = useState<HealthState | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/health`)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(`Health ${response.status}`))))
      .then((payload) => {
        if (!cancelled) setHealth(payload);
      })
      .catch((error) => {
        if (!cancelled) setApiError(error instanceof Error ? error.message : "Health check failed");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function send(question: string) {
    setLoading(true);
    setApiError(null);
    const assistantId = crypto.randomUUID();
    setMessages((items) => [
      ...items,
      { id: crypto.randomUUID(), role: "user", content: question },
      { id: assistantId, role: "assistant", content: "", response: null }
    ]);
    try {
      const response = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, debug })
      });
      if (!response.ok) {
        throw new Error(`API request failed (${response.status})`);
      }
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("API response stream is empty.");
      }
      const decoder = new TextDecoder();
      let buffer = "";
      let finalPayload: any = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";
        for (const chunk of chunks) {
          const lines = chunk.split("\n");
          const event = lines.find((line) => line.startsWith("event:"))?.replace("event:", "").trim();
          const dataLine = lines.find((line) => line.startsWith("data:"));
          if (!event || !dataLine) continue;
          const payload = JSON.parse(dataLine.replace("data:", "").trim());
          if (event === "meta") {
            setMessages((items) =>
              items.map((item) => (item.id === assistantId ? { ...item, content: payload.cache_hit ? "Cache response ready..." : "Running query..." } : item))
            );
          }
          if (event === "result") {
            finalPayload = payload;
            setMessages((items) =>
              items.map((item) => (item.id === assistantId ? { ...item, content: payload.answer || "", response: payload } : item))
            );
          }
        }
      }
      if (finalPayload) {
        setLastResponse(finalPayload);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown API error";
      setApiError(message);
      setMessages((items) =>
        items.map((item) => (item.id === assistantId ? { ...item, content: `Request failed: ${message}` } : item))
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="chat">
        <header className="topbar">
          <div>
            <h1>Querionyx</h1>
            <div className="subtitle">Hybrid RAG + SQL demo</div>
          </div>
          <div className="status-strip" aria-label="Service status">
            <span className={`status-dot ${health?.status === "ok" ? "ok" : apiError ? "bad" : ""}`} />
            <span>API {health?.status || (apiError ? "offline" : "checking")}</span>
            <span>DB {health?.db_status || "-"}</span>
            <span>Chunks {health?.rag_status?.chunk_count ?? "-"}</span>
          </div>
        </header>
        <div className="prompt-row">
          {DEMO_PROMPTS.map((prompt) => {
            const Icon = prompt.icon;
            return (
              <button key={prompt.value} className="prompt-chip" disabled={loading} onClick={() => send(prompt.value)}>
                <Icon size={15} />
                <span>{prompt.label}</span>
              </button>
            );
          })}
        </div>
        <MessageList messages={messages} />
        <ChatInput disabled={loading} onSend={send} />
      </section>
      <aside className="side">
        <button className="debug-toggle" onClick={() => setDebug((value) => !value)}>
          Debug {debug ? "On" : "Off"}
        </button>
        <MetricsPanel response={lastResponse} />
        <SourcePanel sources={lastResponse?.sources || []} />
        {debug ? <DebugPanel response={lastResponse} /> : null}
      </aside>
    </main>
  );
}
