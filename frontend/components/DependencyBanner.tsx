"use client";

import type { DependencyCheck } from "@/lib/types";

// Map a missing tool to a helpful install hint (principle: fail helpfully).
const HINTS: Record<string, string> = {
  npx: "Install Node.js from nodejs.org",
  npm: "Install Node.js from nodejs.org",
  pip: "Install Python from python.org",
  docker: "Install Docker Desktop from docker.com",
  uvx: "Install uv from astral.sh/uv",
};

// Tools we surface to the user (pip3/uv/npm are covered by their primary alias).
const PRIMARY_TOOLS = ["npx", "pip", "docker"] as const;

export function DependencyBanner({ deps }: { deps?: DependencyCheck }) {
  if (!deps) return null;

  const missing = PRIMARY_TOOLS.filter((tool) => {
    if (deps[tool]) return false;
    // Treat aliases as satisfying the requirement.
    if (tool === "npx" && deps["npm"]) return false;
    if (tool === "pip" && deps["pip3"]) return false;
    return true;
  });

  if (missing.length === 0) return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <i className="ti ti-alert-triangle mt-0.5 text-base" aria-hidden />
      <div>
        <p className="font-medium">Some install tools are missing.</p>
        <p className="mt-0.5 text-amber-700">
          MCPs that rely on them can&apos;t be installed until you add:{" "}
          {missing.map((tool, i) => (
            <span key={tool}>
              <span className="font-semibold">{tool}</span>
              <span className="text-amber-600"> ({HINTS[tool]})</span>
              {i < missing.length - 1 ? "; " : ""}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}
