# Frontend IT Job Portal

Frontend của IT Job Portal được xây dựng bằng Next.js App Router, React và TypeScript. Ứng dụng cung cấp giao diện công khai và các khu vực riêng cho ứng viên, nhà tuyển dụng và quản trị viên.

## Yêu cầu

- Node.js 20.9 trở lên; CI đang dùng Node.js 20.
- npm với dependency được khóa trong `package-lock.json`.
- Backend API đang hoạt động nếu cần sử dụng dữ liệu thật hoặc sinh lại OpenAPI types.

## Cài đặt

Chạy từ thư mục `job_portal_frontend`:

```powershell
npm ci
Copy-Item .env.local.example .env.local
```

## Biến môi trường

| Biến | Phạm vi | Ý nghĩa |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Trình duyệt | URL công khai của Django backend |
| `API_URL` | Server | URL backend dùng bởi Server Components và proxy |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Trình duyệt | Google OAuth client ID, phải khớp với backend |

Không đặt secret, API key hoặc token vào biến có tiền tố `NEXT_PUBLIC_`.

## Chạy development server

```powershell
npm run dev
```

Mở `http://localhost:3000`. Mặc định frontend local kết nối backend tại `http://localhost:8000` theo `.env.local.example`.

## Kiểm tra và build

```powershell
npm run lint
npm run typecheck
npm run build
```

Chạy bản production đã build:

```powershell
npm run start
```

Frontend chưa có script test hoặc framework kiểm thử tự động. Không có lệnh test frontend được khai báo trong `package.json`.

Khi backend đang chạy tại `http://localhost:8000`, có thể sinh lại type từ OpenAPI:

```powershell
npm run api:types
```

File `src/types/generated/api-schema.ts` là kết quả sinh tự động, không chỉnh sửa thủ công.

## Cấu trúc mã nguồn

```text
src/
|-- app/                  # Route, layout, loading và error boundary
|-- features/             # API, type, hook và component theo domain
|   |-- admin/
|   |-- applications/
|   |-- auth/
|   |-- candidates/
|   |-- dashboard/
|   |-- employer/
|   `-- jobs/
|-- components/
|   |-- layout/           # Navbar, Footer và public shell
|   `-- ui/               # UI primitive dùng lại
|-- lib/                  # API client, auth, polling và tiện ích
|-- types/generated/      # Type sinh từ OpenAPI
`-- proxy.ts              # Kiểm tra guest và role qua backend
```

Các route chính:

- Public: `/`, `/jobs`, `/jobs/[jobId]`, `/login`, `/register`.
- Ứng viên: `/candidate/profile`, `/candidate/applications`, `/candidate/applications/[id]`.
- Nhà tuyển dụng: `/employer`, `/employer/company`, `/employer/jobs` và các route quản lý hồ sơ ứng tuyển.
- Quản trị viên: `/admin`, `/admin/users`, `/admin/companies`, `/admin/skills`.

## Kết nối backend

Frontend chỉ giao tiếp với Django qua REST API và JSON. `src/lib/api-client.ts` xử lý request, JWT và refresh token; `src/proxy.ts` xác minh phiên và role cho các route được bảo vệ. Trình duyệt không gọi trực tiếp Gemini, QStash, Redis, SMTP hoặc Cloudflare R2.

API schema được cung cấp tại `http://localhost:8000/api/schema/` và Swagger UI tại `http://localhost:8000/api/docs/` khi backend local đang chạy.