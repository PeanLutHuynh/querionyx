export function MetricsPanel({ response }: { response: any }) {
  return (
    <section className="panel">
      <h2>Metrics</h2>
      {response ? (
        <div>
          <div>Intent: {response.intent}</div>
          <div>Latency: {response.latency_ms} ms</div>
          <div>Cache: {response.cache_hit ? "hit" : "miss"}</div>
          <div>Router: {response.router_type_used}</div>
          <div>Branches: {(response.branches || []).join(", ")}</div>
        </div>
      ) : (
        <div>No query yet</div>
      )}
    </section>
  );
}

