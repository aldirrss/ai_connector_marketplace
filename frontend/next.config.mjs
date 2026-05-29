/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // This is a local-first tool; lint errors should not block the production build.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
