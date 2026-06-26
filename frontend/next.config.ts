import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/outputs/**',
      },
    ],
  },
  async rewrites() {
    const analyzer = process.env.ANALYZER_URL || 'http://127.0.0.1:8000';
    return [
      // 번역 결과 이미지 + ZIP 다운로드를 분석기로 프록시 (브라우저는 same-origin만 호출)
      { source: '/outputs/:path*', destination: `${analyzer}/outputs/:path*` },
    ];
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
};

export default nextConfig;
