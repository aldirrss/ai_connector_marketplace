/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // This is a local-first tool; lint errors should not block the production build.
  eslint: { ignoreDuringBuilds: true },
  // When building for the Tauri desktop shell we emit a fully static site to
  // `out/` (the app is entirely client-rendered, so static export is safe).
  // Set NEXT_OUTPUT=export — used by `npm run tauri:build`.
  ...(process.env.NEXT_OUTPUT === "export"
    ? { output: "export", images: { unoptimized: true } }
    : {}),
};

export default nextConfig;
