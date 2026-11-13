/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  async rewrites() {
    const djangoUrl = process.env.DJANGO_URL || 'http://localhost:8082';
    const aiUrl = process.env.AI_URL || 'http://localhost:8000';
    return [
      {
        source: '/api-django/:path*',
        destination: `${djangoUrl}/api/:path*`,
      },
      {
        source: '/api-ai/:path*',
        destination: `${aiUrl}/:path*`,
      },
      {
        source: '/backend_php/api/:path*',
        destination: `${djangoUrl}/api/:path*`,
      },
      {
        source: '/backend_php/auth/:path*',
        destination: `${djangoUrl}/auth/:path*`,
      },
      {
        source: '/backend_php/uploads/:path*',
        destination: `${djangoUrl}/uploads/:path*`,
      },
      {
        source: '/uploads/:path*',
        destination: `${djangoUrl}/uploads/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
