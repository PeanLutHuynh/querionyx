export function MetricsPanel({ response }: { response: any }) {
  const confidence = typeof response?.confidence === "number" ? `${Math.round(response.confidence * 100)}%` : "-";

  return (
    <section className="panel">
      <h2>Metrics</h2>
      {response ? (
        <div className="metric-grid">
          <span>Intent</span>
          <strong>{response.intent || "-"}</strong>
          <span>Latency</span>
          <strong>{response.latency_ms} ms</strong>
          <span>Confidence</span>
          <strong>{confidence}</strong>
          <span>Cache</span>
          <strong>{response.cache_hit ? "hit" : "miss"}</strong>
          <span>Fallback</span>
          <strong>{response.fallback_used ? "yes" : "no"}</strong>
          <span>Branches</span>
          <strong>{(response.branches || []).join(", ") || "-"}</strong>
        </div>
      ) : (
        <div>No query yet</div>
      )}
    </section>
  );
}
