import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    proxyTimeout: 300000,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    // In production, we should ideally use the full backend URL directly in the apiClient.
    // This rewrite is mainly for local development to avoid CORS.
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
