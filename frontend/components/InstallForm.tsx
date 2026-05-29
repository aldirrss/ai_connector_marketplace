"use client";

import { useState } from "react";
import type { ConfigFieldSchema } from "@/lib/types";

export function InstallForm({
  schema,
  installing,
  initialValues,
  submitLabel = "Install",
  busyLabel = "Installing…",
  onSubmit,
  onCancel,
}: {
  schema: Record<string, ConfigFieldSchema>;
  installing: boolean;
  initialValues?: Record<string, string>;
  submitLabel?: string;
  busyLabel?: string;
  onSubmit: (values: Record<string, string>) => void;
  onCancel: () => void;
}) {
  const fields = Object.entries(schema);
  const [values, setValues] = useState<Record<string, string>>(
    initialValues ?? {},
  );

  const missingRequired = fields.some(
    ([key, field]) => field.required && !values[key]?.trim(),
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (missingRequired || installing) return;
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {fields.map(([key, field]) => (
        <div key={key}>
          <label
            htmlFor={`cfg-${key}`}
            className="block text-sm font-medium text-slate-700"
          >
            {field.label}
            {field.required && <span className="text-rose-500"> *</span>}
          </label>
          {field.description && (
            <p className="mt-0.5 text-xs text-slate-500">{field.description}</p>
          )}
          <input
            id={`cfg-${key}`}
            type={field.type === "secret" ? "password" : "text"}
            autoComplete={field.type === "secret" ? "new-password" : "off"}
            placeholder={field.placeholder}
            required={field.required}
            value={values[key] ?? ""}
            onChange={(e) =>
              setValues((v) => ({ ...v, [key]: e.target.value }))
            }
            className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {field.type === "secret" && (
            <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
              <i className="ti ti-lock" aria-hidden />
              Sent straight to your local config — never stored in the browser.
            </p>
          )}
        </div>
      ))}

      <div className="flex items-center gap-2 pt-1">
        <button
          type="submit"
          disabled={missingRequired || installing}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {installing ? (
            <i className="ti ti-loader-2 animate-spin" aria-hidden />
          ) : (
            <i className="ti ti-download" aria-hidden />
          )}
          {installing ? busyLabel : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={installing}
          className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
