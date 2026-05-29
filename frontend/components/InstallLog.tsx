"use client";

import { useEffect, useRef } from "react";

// Live console for streamed install output (POST /install/stream).
export function InstallLog({ lines }: { lines: string[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest line as output streams in.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [lines]);

  if (lines.length === 0) return null;

  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Install log
      </p>
      <div className="scroll-thin max-h-48 overflow-y-auto rounded-lg bg-slate-900 px-3 py-2 font-mono text-xs leading-relaxed text-slate-100">
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-words">
            {line || " "}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
