"use client";

import { useEffect } from "react";

export type ToastKind = "success" | "error" | "restart";

export interface ToastState {
  kind: ToastKind;
  message: string;
}

const STYLES: Record<ToastKind, { box: string; icon: string }> = {
  success: { box: "border-emerald-200 bg-emerald-50 text-emerald-800", icon: "ti-circle-check" },
  error: { box: "border-rose-200 bg-rose-50 text-rose-800", icon: "ti-alert-circle" },
  restart: { box: "border-brand-200 bg-brand-50 text-brand-800", icon: "ti-refresh" },
};

export function Toast({
  toast,
  onDismiss,
}: {
  toast: ToastState | null;
  onDismiss: () => void;
}) {
  // Restart reminders persist until dismissed; success/error auto-dismiss.
  useEffect(() => {
    if (!toast || toast.kind === "restart") return;
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [toast, onDismiss]);

  if (!toast) return null;
  const style = STYLES[toast.kind];

  return (
    <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2">
      <div
        role="status"
        className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-sm shadow-lg ${style.box}`}
      >
        <i className={`ti ${style.icon} text-base`} aria-hidden />
        <span>{toast.message}</span>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="ml-1 rounded p-0.5 opacity-60 transition hover:opacity-100"
        >
          <i className="ti ti-x" aria-hidden />
        </button>
      </div>
    </div>
  );
}
