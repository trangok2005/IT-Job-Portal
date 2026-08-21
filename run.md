# Chạy toàn bộ hệ thống bằng Docker (khuyên dùng)

Một lệnh duy nhất — DB (Postgres+pgvector :5432), Django BE (:8000), Django-Q worker, Next.js FE (:3000):

```powershell
docker compose -f job_portal_backend/deploy/docker/docker-compose.yml up -d --wait
```

- Lần đầu tiên (hoặc sau khi reset dữ liệu), seed dữ liệu mẫu:
  `docker exec job_portal_backend python manage.py seed_demo`
- Xem log: `docker logs -f job_portal_backend` (hoặc `_qcluster`, `_frontend`, `_db`)
- Tắt nhưng giữ dữ liệu: thêm lệnh `down`
- Reset sạch (MẤT HẾT DỮ LIỆU): `down -v --remove-orphans` rồi `up -d --wait` + migrate tự chạy + seed lại

Địa chỉ:

| Thành phần | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Health check | http://localhost:8000/api/v1/health/ |
| Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ (admin@jobportal.local/admin123) |

Tài khoản demo: `admin@jobportal.local/admin123` · `employer@jobportal.local/employer123` · `candidate@jobportal.local/candidate123`

BE tự động chạy `migrate` khi container start; BE và qcluster dùng chung volume `media` nên CV upload từ web sẽ được worker đọc được.

# Chạy bằng venv trên máy (khi cần debug)

```powershell
# 1. Chỉ bật DB
docker compose -f job_portal_backend/deploy/docker/docker-compose.yml up -d db

# 2. Backend (terminal 1)
job_portal_backend\.venv\Scripts\python job_portal_backend\manage.py migrate
job_portal_backend\.venv\Scripts\python job_portal_backend\manage.py seed_demo

# 3. Worker (terminal 2) — bắt buộc phải có để parse CV / embedding / thông báo
job_portal_backend\.venv\Scripts\python job_portal_backend\manage.py qcluster

# 4. Server (terminal 3)
job_portal_backend\.venv\Scripts\python job_portal_backend\manage.py runserver 0.0.0.0:8000

# 5. Frontend (terminal 4)
npm run dev --prefix job_portal_frontend -- --hostname 0.0.0.0 --port 3000
```

Lưu ý: sửa code BE/FE thì build lại image Docker (`docker compose -f job_portal_backend/deploy/docker/docker-compose.yml up -d --build`), hoặc dùng cách chạy venv ở dưới.
