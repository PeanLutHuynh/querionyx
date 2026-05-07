export function SQLTableRenderer({ text }: { text: string }) {
  const lines = text.split("\n").filter((line) => line.trim().startsWith("|"));
  if (lines.length < 2) return null;
  const rows = lines
    .filter((line) => !line.includes("---"))
    .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));

  return (
    <table>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={rowIndex}>
            {row.map((cell, cellIndex) => (rowIndex === 0 ? <th key={cellIndex}>{cell}</th> : <td key={cellIndex}>{cell}</td>))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

