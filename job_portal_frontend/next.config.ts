import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Trong production, đặt nginx phía trước và chuyển /api/ tới Django backend.
  // Trong development cục bộ, frontend gọi trực tiếp NEXT_PUBLIC_API_URL
  // (CORS được bật ở backend).
};

export default nextConfig;
