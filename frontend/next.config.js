/** @type {import('next').NextConfig} */
const backendBaseUrl = (process.env.BACKEND_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8001',
        pathname: '/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization' },
        ],
      },
    ]
  },
  async rewrites() {
    // Keep filesystem routes (for example /api/backend/* app route handlers)
    // and only proxy unmatched API routes to FastAPI.
    return {
      fallback: [
        {
          source: '/api/:path*',
          destination: `${backendBaseUrl}/api/:path*`,
        },
      ],
    }
  },
  // Turbopack配置
  turbopack: {
    // 启用Turbopack
  },
}

module.exports = nextConfig
