import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Proxy API requests to the FastAPI backend during development.
   * In production, configure a reverse proxy (nginx, etc.) instead.
   */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
