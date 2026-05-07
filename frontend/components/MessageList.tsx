import { SQLTableRenderer } from "./SQLTableRenderer";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: any | null;
};

export function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div className="messages">
      {messages.map((message) => (
        <article key={message.id} className={`message ${message.role}`}>
          <div>{message.content}</div>
          {message.response ? (
            <div className="badges">
              <span className="badge intent">{message.response.intent}</span>
              <span className="badge">{message.response.latency_ms} ms</span>
              <span className="badge cache">{message.response.cache_hit ? "CACHE HIT" : "CACHE MISS"}</span>
              <span className="badge">{message.response.router_type_used}</span>
              <span className="badge">{message.response.trace_id}</span>
            </div>
          ) : null}
          {message.response ? <SQLTableRenderer text={message.content} /> : null}
        </article>
      ))}
    </div>
  );
}
