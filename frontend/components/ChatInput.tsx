"use client";

import { Send } from "lucide-react";
import { FormEvent, useState } from "react";

export function ChatInput({ disabled, onSend }: { disabled: boolean; onSend: (value: string) => void }) {
  const [value, setValue] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <form className="composer" onSubmit={submit}>
      <textarea value={value} onChange={(event) => setValue(event.target.value)} />
      <button disabled={disabled} title="Send query" aria-label="Send query">
        <Send size={18} />
      </button>
    </form>
  );
}

