import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return process.env.NODE_ENV === "development"
      ? [
        {
          source: "/api/:path*",
          destination: "http://127.0.0.1:8000/api/:path*",
        },
      ]
      : [
        {
          source: "/api/:path*",
          destination: "/api/index",
        },
      ];
  },
};

export default nextConfig;
