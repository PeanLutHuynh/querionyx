"use client";

import { useState } from "react";
import { ChatInput } from "../components/ChatInput";
import { MessageList, Message } from "../components/MessageList";
import { SourcePanel } from "../components/SourcePanel";
import { MetricsPanel } from "../components/MetricsPanel";
import { DebugPanel } from "../components/DebugPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastResponse, setLastResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [debug, setDebug] = useState(false);

  async function send(question: string) {
    setLoading(true);
    const assistantId = crypto.randomUUID();
    setMessages((items) => [
      ...items,
      { id: crypto.randomUUID(), role: "user", content: question },
      { id: assistantId, role: "assistant", content: "", response: null }
    ]);
    const response = await fetch(`${API_BASE}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, debug })
    });
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload: any = null;

    if (reader) {
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
    }
    if (finalPayload) {
      setLastResponse(finalPayload);
    }
    setLoading(false);
  }

  return (
    <main className="shell">
      <section className="chat">
        <MessageList messages={messages} />
        <ChatInput disabled={loading} onSend={send} />
      </section>
      <aside className="side">
        <button className="debug-toggle" onClick={() => setDebug((value) => !value)}>
          Debug {debug ? "On" : "Off"}
        </button>
        <MetricsPanel response={lastResponse} />
        <SourcePanel sources={lastResponse?.sources || []} />
        <DebugPanel response={lastResponse} />
      </aside>
    </main>
  );
}
