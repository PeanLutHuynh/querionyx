export function SourcePanel({ sources }: { sources: string[] }) {
  return (
    <section className="panel">
      <h2>Sources</h2>
      {sources.length ? (
        <div className="source-list">
          {sources.map((source) => (
            <span className="source-pill" key={source}>
              {source}
            </span>
          ))}
        </div>
      ) : (
        <div>No sources</div>
      )}
    </section>
  );
}
