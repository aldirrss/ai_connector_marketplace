"use client";

import { useState } from "react";

const STEPS = [
  "Open claude.ai and sign in.",
  "Go to Settings → Connectors (Integrations).",
  'Click "Add custom connector".',
  "Paste the URL below and follow the prompts.",
];

// For remote (http/sse) MCPs: there is no API to auto-register on Claude Web,
// so we surface the URL + a copy button + a short manual guide instead.
export function ClaudeWebGuide({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);
  const isTemplated = url.includes("{");

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable; user can still select the text
    }
  }

  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-brand-800">
        <i className="ti ti-world" aria-hidden />
        Use on Claude Web
      </p>
      <p className="mt-1 text-xs text-brand-700">
        This remote MCP works on claude.ai. There&apos;s no API to add it
        automatically, so add it manually:
      </p>

      <ol className="mt-3 list-decimal space-y-1 pl-5 text-xs text-slate-600">
        {STEPS.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>

      <div className="mt-3 flex items-center gap-2">
        <code className="scroll-thin flex-1 overflow-x-auto rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700">
          {url}
        </code>
        <button
          type="button"
          onClick={copy}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-brand-700"
        >
          <i className={`ti ${copied ? "ti-check" : "ti-copy"}`} aria-hidden />
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {isTemplated && (
        <p className="mt-2 text-xs text-amber-700">
          <i className="ti ti-alert-triangle" aria-hidden /> Replace the{" "}
          <code>{"{...}"}</code> placeholder with your actual server URL first.
        </p>
      )}
    </div>
  );
}
