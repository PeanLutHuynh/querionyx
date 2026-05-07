export function DebugPanel({ response }: { response: any }) {
  return (
    <section className="panel">
      <h2>Debug</h2>
      {response ? <pre>{JSON.stringify(response, null, 2)}</pre> : <div>No trace</div>}
    </section>
  );
}

