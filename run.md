# Chạy local

## Chuẩn bị lần đầu

Từ thư mục gốc repository, tạo file cấu hình local:

```powershell
Copy-Item job_portal_backend/.env.local.example job_portal_backend/.env.local
Copy-Item job_portal_frontend/.env.local.example job_portal_frontend/.env.local
```

Điền credential của bucket Cloudflare R2 development vào `job_portal_backend/.env.local`:

```env
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=
```

Các luồng AI, Google Login và gửi mail chỉ hoạt động khi điền thêm
`GEMINI_API_KEY`, `GOOGLE_CLIENT_ID` và các biến SMTP tương ứng. Không commit
các file `.env.local`.

## Khởi động PostgreSQL

Docker chỉ chạy PostgreSQL 16 với pgvector:

```powershell
docker compose up -d --wait
```

Cài backend dependencies và chạy migration:

```powershell
python -m pip install -r job_portal_backend/requirements/base.txt
python job_portal_backend/manage.py migrate
```

## Chạy ứng dụng

Mở terminal thứ nhất cho QStash Dev:

```powershell
npx @upstash/qstash-cli dev
```

Mở terminal thứ hai cho Django:

```powershell
python job_portal_backend/manage.py runserver 127.0.0.1:8000
```

Khi QStash và Django đã chạy, đăng ký schedules một lần:

```powershell
python job_portal_backend/manage.py setup_qstash_schedules
```

Seed dữ liệu mẫu nếu database chưa có dữ liệu:

```powershell
python job_portal_backend/manage.py seed_demo
```

Mở terminal thứ ba cho Next.js:

```powershell
npm ci --prefix job_portal_frontend
npm run dev --prefix job_portal_frontend
```

Local Django luôn dùng `LocMemCache`; `REDIS_URL` production không được sử dụng. File CV/JD được lưu trong bucket R2 development private, không lưu dưới `MEDIA_ROOT`.

Dừng database khi không sử dụng:

```powershell
docker compose down
```

## Địa chỉ local

| Thành phần | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/ |
| Health check | http://localhost:8000/api/health/ |
| Swagger | http://localhost:8000/api/docs/ |
| Django Admin | http://localhost:8000/admin/ |
| QStash Dev | http://localhost:8080 |

## Kiểm tra trước khi commit

```powershell
python job_portal_backend/manage.py test --settings=config.settings.test
python job_portal_backend/manage.py makemigrations --check --dry-run --settings=config.settings.test
npm run lint --prefix job_portal_frontend
npm run typecheck --prefix job_portal_frontend
npm run build --prefix job_portal_frontend
```
