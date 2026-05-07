export function SourcePanel({ sources }: { sources: string[] }) {
  return (
    <section className="panel">
      <h2>Sources</h2>
      {sources.length ? sources.map((source) => <div key={source}>{source}</div>) : <div>No sources</div>}
    </section>
  );
}

