# IT Job Portal

IT Job Portal là hệ thống tuyển dụng dành cho lĩnh vực công nghệ thông tin, kết nối ứng viên với nhà tuyển dụng và cung cấp công cụ quản trị dữ liệu tuyển dụng. Gemini được dùng để trích xuất dữ liệu từ CV/JD và sinh vector; backend tự tính Match Score theo quy tắc nghiệp vụ, không giao quyết định tuyển dụng cho AI.

## 1. Giới thiệu

Hệ thống hỗ trợ quản lý hồ sơ, tìm kiếm và gợi ý việc làm, quản lý tuyển dụng và quản trị dữ liệu dùng chung. Match Score chỉ cung cấp thông tin tham khảo; quyết định tuyển dụng luôn thuộc về người sử dụng.

## 2. Nhóm người dùng

- **Khách:** xem và tìm kiếm các tin tuyển dụng đang hoạt động.
- **Ứng viên:** quản lý hồ sơ, CV, tìm việc, nhận gợi ý, ứng tuyển và theo dõi trạng thái.
- **Nhà tuyển dụng:** quản lý doanh nghiệp, tin tuyển dụng, hồ sơ ứng tuyển và ứng viên gợi ý.
- **Quản trị viên:** quản lý tài khoản, xét duyệt doanh nghiệp, chuẩn hóa kỹ năng và cấu hình trọng số Match Score.

## 3. Chức năng chính

- Đăng ký và đăng nhập bằng email/password hoặc Google OAuth; xác thực API bằng JWT.
- Quản lý hồ sơ ứng viên gồm thông tin cá nhân, học vấn, kinh nghiệm, kỹ năng và nhiều CV.
- Nhập hồ sơ thủ công hoặc tải CV để Gemini trích xuất dữ liệu, sau đó người dùng xem lại trước khi lưu.
- Tạo, chỉnh sửa, đăng và đóng tin tuyển dụng; hỗ trợ trích xuất JD bằng Gemini.
- Tìm kiếm việc làm bằng bộ lọc, từ khóa và vector ngữ nghĩa; có cơ chế tìm kiếm cơ bản khi semantic search không khả dụng.
- Gợi ý công việc cho ứng viên và gợi ý ứng viên công khai cho nhà tuyển dụng.
- Nộp hồ sơ với CV chính tùy chọn, theo dõi lịch sử và cập nhật trạng thái tuyển dụng theo state machine.
- Tính Match Score từ độ tương đồng ngữ nghĩa, kỹ năng, kinh nghiệm, học vấn và trọng số do quản trị viên cấu hình.
- Gửi email khi trạng thái hồ sơ ứng tuyển thay đổi.

## 4. Kiến trúc tổng thể

Backend tổ chức thao tác ghi và quy tắc nghiệp vụ trong service, truy vấn đọc trong selector, còn view chủ yếu xử lý HTTP. Business service phát hành message qua `integrations/qstash`; callback có chữ ký được chuyển vào dispatcher trung lập tại `apps/core/background_tasks`, rồi thực thi task trong từng domain app.

Gemini chỉ trích xuất dữ liệu có cấu trúc và sinh embedding. Backend kiểm tra dữ liệu trích xuất, lưu vector bằng pgvector và tính Match Score từ semantic similarity, skill, experience, education cùng cấu hình trọng số đang hoạt động.

## 5. Công nghệ sử dụng

| Thành phần | Công nghệ chính |
| --- | --- |
| Frontend | Next.js 16.3.1, React 19.2.8, TypeScript 5, Tailwind CSS 4 |
| Backend | Python 3.11, Django 5.2.17, Django REST Framework 3.18.0 |
| Xác thực | SimpleJWT JWT, Google OAuth |
| Cơ sở dữ liệu | PostgreSQL 16, pgvector |
| AI | Gemini parsing và embedding |
| Tác vụ nền | Upstash QStash |
| Cache | LocMemCache ở local, Redis TLS ở production |
| Lưu trữ file | Cloudflare R2 với URL ký có thời hạn |
| API contract | drf-spectacular, OpenAPI, openapi-typescript |

## 6. Cấu trúc repository

```text
IT-Job-Portal/
|-- docker-compose.yml          # PostgreSQL 16 + pgvector cho local
|-- run.md                      # Hướng dẫn chạy local chi tiết
|-- job_portal_backend/
|   |-- api/                    # Ghép URL API
|   |-- apps/                   # Các domain Django
|   |-- common/                 # Permission, pagination, throttle, xử lý tài liệu
|   |-- config/                 # URL, WSGI/ASGI và settings theo môi trường
|   |-- integrations/           # Gemini, R2 và SMTP
|   |-- requirements/           # Dependency base và production
|   `-- deploy/render/          # Script build/start cho Render
`-- job_portal_frontend/
    |-- src/app/                # Route và layout của Next.js App Router
    |-- src/features/           # API và UI theo domain
    |-- src/components/         # UI primitive và layout dùng chung
    |-- src/lib/                # API client, auth và tiện ích
    |-- src/proxy.ts            # Kiểm tra guest/role ở lớp proxy
    `-- src/types/generated/    # Type sinh từ OpenAPI
```


## 7. Yêu cầu môi trường

- Python 3.11.
- Node.js 20.9 trở lên; CI đang dùng Node.js 20.
- npm và Docker Compose.
- Tài khoản hoặc credential development cho Cloudflare R2.
- Gemini API key nếu sử dụng parsing, embedding và semantic search.
- Google OAuth client ID nếu sử dụng đăng nhập Google.
- SMTP server nếu kiểm tra chức năng gửi email.

## 8. Chạy local

Các lệnh dưới đây chạy từ thư mục gốc repository.

Tạo file môi trường:

```powershell
Copy-Item job_portal_backend/.env.local.example job_portal_backend/.env.local
Copy-Item job_portal_frontend/.env.local.example job_portal_frontend/.env.local
```

Điền credential cần thiết, sau đó khởi động PostgreSQL:

```powershell
docker compose up -d --wait
```

Cài dependency và chuẩn bị database:

```powershell
python -m venv job_portal_backend/.venv
job_portal_backend/.venv/Scripts/python.exe -m pip install -r job_portal_backend/requirements/base.txt
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py migrate
npm ci --prefix job_portal_frontend
```

Mở ba terminal riêng:

```powershell
npx @upstash/qstash-cli dev
```

```powershell
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py runserver 127.0.0.1:8000
```

```powershell
npm run dev --prefix job_portal_frontend
```

Sau khi QStash Dev và Django hoạt động, đăng ký lịch định kỳ:

```powershell
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py setup_qstash_schedules
```

Có thể tạo dữ liệu demo cho môi trường local:

```powershell
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py seed_demo
```

Lệnh này chỉ dành cho môi trường development. Hướng dẫn vận hành chi tiết nằm trong [`run.md`](run.md).

Các địa chỉ local:

| Thành phần | URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| API | `http://localhost:8000/api/` |
| Health check | `http://localhost:8000/api/health/` |
| OpenAPI schema | `http://localhost:8000/api/schema/` |
| Swagger UI | `http://localhost:8000/api/docs/` |
| Django Admin | `http://localhost:8000/admin/` |
| QStash Dev | `http://localhost:8080` |

## 9. Cấu hình biến môi trường

Không commit `.env`, `.env.local` hoặc credential thật. Các file mẫu là:

- `job_portal_backend/.env.local.example`
- `job_portal_backend/.env.production.example`
- `job_portal_frontend/.env.local.example`
- `job_portal_frontend/.env.production.example`

Các nhóm biến backend chính:

| Nhóm | Biến |
| --- | --- |
| Django và origin | `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `BACKEND_PUBLIC_URL` |
| PostgreSQL | `DATABASE_URL` hoặc `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| JWT và Google | `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`, `GOOGLE_CLIENT_ID` |
| QStash | `QSTASH_DEV`, `QSTASH_URL`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY` |
| Cloudflare R2 | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`, `R2_SIGNED_URL_TTL_SECONDS` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_PARSER_MODEL`, `GEMINI_EMBEDDING_MODEL`, `GEMINI_TIMEOUT_MS`, `TASK_PROCESSING_LEASE_SECONDS` |
| Redis | `REDIS_URL` |
| Email | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_TIMEOUT`, `DEFAULT_FROM_EMAIL` |
| Upload | `MAX_RESUME_SIZE_BYTES`, `MAX_JD_SIZE_BYTES` |

Frontend sử dụng `NEXT_PUBLIC_API_URL`, `API_URL` và `NEXT_PUBLIC_GOOGLE_CLIENT_ID`. Biến có tiền tố `NEXT_PUBLIC_` được đưa vào mã phía trình duyệt và không được chứa bí mật.

Local dùng `config.settings.local` và `LocMemCache`. Production dùng `config.settings.production`, yêu cầu Redis qua `rediss://` và kiểm tra chặt các biến bảo mật khi khởi động.

## 10. Chạy kiểm tra

Chạy từ thư mục gốc repository:

```powershell
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py check --settings=config.settings.test
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py makemigrations --check --dry-run --settings=config.settings.test
job_portal_backend/.venv/Scripts/python.exe job_portal_backend/manage.py test --settings=config.settings.test
npm run lint --prefix job_portal_frontend
npm run typecheck --prefix job_portal_frontend
npm run build --prefix job_portal_frontend
```

Frontend chưa khai báo script test. CI hiện chạy backend test và frontend lint.

## 11. Mô hình triển khai

- **Frontend:** có thể triển khai dự án Next.js trong `job_portal_frontend` lên Vercel và cấu hình ba biến frontend theo file `.env.production.example`.
- **Backend:** repository có `deploy/render/build.sh` và `deploy/render/start.sh` để cài dependency production, collect static, migrate và chạy Gunicorn trên Render.
- **Database:** PostgreSQL phải hỗ trợ extension pgvector.
- **Tác vụ nền:** production dùng Upstash QStash và các signing key để xác minh callback.
- **Cache và throttle:** production dùng Redis qua TLS.
- **File:** CV và JD được lưu riêng tư trên Cloudflare R2.
