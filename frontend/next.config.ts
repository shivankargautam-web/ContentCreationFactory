import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  // Same-origin proxy to the API so the browser never needs a separate backend origin (no CORS).
  async rewrites() {
    const backend = (process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "");
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
