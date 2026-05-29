import { PLATFORMS } from "@/lib/labels";

// Renders all known platforms, highlighting the ones this MCP supports and
// dimming the rest — so users can see at a glance where an MCP works.
export function PlatformBadges({
  platforms,
  size = "sm",
}: {
  platforms: string[];
  size?: "sm" | "md";
}) {
  const supported = new Set(platforms);
  const dim = size === "md" ? "text-sm" : "text-xs";

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {PLATFORMS.map((p) => {
        const ok = supported.has(p.key);
        return (
          <span
            key={p.key}
            title={ok ? `Works on ${p.label}` : `Not available on ${p.label}`}
            className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 ${dim} font-medium ${
              ok
                ? "bg-slate-100 text-slate-700"
                : "bg-transparent text-slate-300 line-through"
            }`}
          >
            <i className={`ti ${p.icon}`} aria-hidden />
            {p.label}
          </span>
        );
      })}
    </div>
  );
}
