import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In production, put nginx in front and serve /api/ to the Django backend.
  // In local dev, the frontend calls NEXT_PUBLIC_API_URL directly (CORS is
  // enabled on the backend).
};

export default nextConfig;