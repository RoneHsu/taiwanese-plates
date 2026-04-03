import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "image.uniqlo.com" },
      { protocol: "https", hostname: "www.uniqlo.com" },
    ],
  },
};

export default nextConfig;
