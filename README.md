# IT Job Portal — Context Document cho AI Coding Agent

## 1. Tổng quan dự án & mục tiêu

**IT Job Portal** là cổng thông tin tuyển dụng CNTT tích hợp AI, kết nối
**Ứng viên** và **Nhà tuyển dụng**, có **Admin** quản trị hệ thống.

Vấn đề cần giải quyết:
- CV có cấu trúc không đồng nhất, ứng viên phải nhập lại thông tin nhiều lần.
- Tìm kiếm việc làm theo từ khóa bỏ sót các job phù hợp về mặt ngữ nghĩa.
- Nhà tuyển dụng mất nhiều thời gian sàng lọc hồ sơ thủ công.
- Skill trong CV và JD được biểu diễn theo nhiều cách khác nhau, khó so khớp.

Giải pháp: kết hợp **Resume/JD Parsing bằng Gemini AI**, **Skill
Normalization**, **Vector Embedding**, **Semantic Search (pgvector)** và
**Business Rule Ranking** để tính `match_score` hỗ trợ sàng lọc.


- FE gọi BE qua `NEXT_PUBLIC_API_URL + /api/`, không gọi trực tiếp Gemini
  hay Cloudflare R2 — mọi tích hợp bên ngoài đi qua BE (`integrations/`).
- Auth: JWT (kèm Google OAuth), FE dùng `middleware.ts` để chặn route theo
  role, khớp với role ở BE (`accounts.Role`).
- Các tác vụ nặng/không cần realtime (sinh embedding, đóng job hết hạn) chạy
  bất đồng bộ qua **QStash**, không chạy đồng bộ trong request-response.


## 3. Cấu trúc thư mục và vai trò từng module

### Backend — `job_portal_backend/`

```
```

Mỗi app trong `apps/` có cấu trúc nội bộ **giống nhau** (ví dụ `apps/jobs/`):

| File | Vai trò |
| --- | --- |
| `models.py` | Định nghĩa model, không chứa business logic phức tạp |
| `selectors.py` | Đọc dữ liệu phức tạp (`get_active_jobs_for()`, `search_jobs_by_vector()`) |
| `services.py` | Ghi dữ liệu + business logic (`publish_job()`, `close_job()`) |
| `serializers.py` | Chỉ lo shape input/output, KHÔNG chứa logic nghiệp vụ |
| `perms.py` | Permission phụ thuộc object/nghiệp vụ riêng (`IsJobOwner`, `IsApprovedEmployer`) |
| `views.py` | ViewSet mỏng: gọi service/selector, trả response — không chứa logic |
| `tasks.py` | Job async do dispatcher QStash gọi (tính embedding, đóng job hết hạn) |
| `tests/` | `factories.py`, `test_models.py`, `test_services.py`, `test_api.py` |

**Quy tắc bắt buộc:** khi thêm business logic mới, luôn đặt trong
`services.py` hoặc `selectors.py`, KHÔNG đặt trong `views.py` hay
`serializers.py`.

Permission chỉ kiểm tra role và dùng ở nhiều app (`IsAdmin`, `IsCandidate`,
`IsEmployer`) đặt tại `common/permissions.py`; permission phụ thuộc model hoặc
object cụ thể vẫn đặt trong `apps/<app>/perms.py`.

### Frontend — `job_portal_frontend/`

```
src/
├── app/                    # CHỈ routing + layout, không chứa business logic
│   ├── (auth)/              # ↔ apps/accounts — login, register
│   ├── (candidate)/         # ↔ Role.CANDIDATE — guard theo role
│   │   ├── profile/         # ↔ apps/candidates
│   │   ├── jobs/             # ↔ apps/jobs (UC-03 tìm kiếm)
│   │   └── applications/     # ↔ apps/applications (theo dõi trạng thái)
│   ├── (employer)/          # ↔ Role.EMPLOYER
│   │   ├── company/          # ↔ apps/companies
│   │   └── jobs/[jobId]/applications/  # ↔ UC-05 xử lý ứng tuyển
│   └── (admin)/             # ↔ Role.ADMIN — companies, skills, users
│
├── features/                # LÕI logic — mỗi thư mục = 1 app Django tương ứng
│   └── <feature>/{api.ts, types.ts, hooks.ts, components/}
│
├── components/{ui, layout, shared}/
├── lib/{api-client.ts, query-client.ts, utils.ts}
├── types/generated/api-schema.ts   # SINH TỰ ĐỘNG từ OpenAPI — không viết tay
├── middleware.ts            # đọc JWT, chặn route theo role
└── config/env.ts             # validate biến môi trường bằng zod
```

**Quy tắc bắt buộc:** business logic (gọi API, quản lý state, transform dữ
liệu) đặt trong `features/<feature>/`, KHÔNG đặt trực tiếp trong `app/`.
`app/` chỉ layout + gọi component từ `features/`.

---

## 4. Domain Model & ràng buộc nghiệp vụ


### Entities

- **User** — `role` (candidate / employer / admin), `is_active`
- **CandidateProfile** — liên kết User; học vấn, kinh nghiệm, kỹ năng (đã
  chuẩn hóa theo Skill Taxonomy); `embedding` (vector); `profile_version`
  (tăng +1 mỗi lần cập nhật thành công); Resume lưu private trên Cloudflare
  R2 và chỉ truy cập qua URL ký ngắn hạn sau khi backend kiểm tra quyền.
- **Company** — hồ sơ công ty; trạng thái phê duyệt (Charter dùng giá trị
  `APPROVED` làm điều kiện đăng tin — các giá trị khác của trạng thái này
  **(Đề xuất, cần xác nhận)**)
- **JobPost** — tiêu đề, mô tả, kỹ năng yêu cầu (chuẩn hóa), mức lương,
  `embedding` (vector), `status` (`DRAFT` / `ACTIVE` / `CLOSED` / `EXPIRED`)
- **JobApplication** — `candidate_id`, `job_id`, snapshot input chấm điểm,
  CV chính được chọn (tùy chọn), `cover_letter` (tùy chọn), `status`,
  `applied_at`
- **ApplicationMatchResult** — kết quả chấm điểm bất biến của một `JobApplication`, có
  thể chưa tồn tại trong lúc task nền chưa hoàn thành
- **Skill Taxonomy** — danh mục kỹ năng chuẩn hóa, do Admin quản trị

### State machine — `JobApplication.status` (BẮT BUỘC, không được vi phạm)

```
applied      → shortlisted, rejected
shortlisted  → interviewed, rejected
interviewed  → hired, rejected
hired        → (trạng thái cuối — KHÔNG chuyển tiếp)
rejected     → (trạng thái cuối — KHÔNG chuyển tiếp)
```

Không cho phép chuyển ngược trạng thái trong **bất kỳ trường hợp nào**, kể cả
khi Nhà tuyển dụng từ chối nhầm. Xử lý bằng liên hệ trực tiếp ứng viên ngoài
hệ thống, không đảo trạng thái, để giữ tính nhất quán của lịch sử tuyển dụng.
Mọi endpoint đổi `status` phải kiểm tra bảng chuyển trạng thái này trước khi
ghi DB, trả lỗi rõ ràng nếu chuyển không hợp lệ.

### Business rules bắt buộc

- AI chỉ hỗ trợ scoring/ranking, không bao giờ tự quyết định tuyển/loại.
- `JobPost` ở `DRAFT`: **không** kích hoạt tác vụ sinh embedding. Chỉ khi
  chuyển sang `ACTIVE` mới publish task `generate_job_embedding` vào QStash.
- Nhà tuyển dụng chỉ đăng tin được khi `Company` ở trạng thái đã phê duyệt.
- Ứng viên chỉ được ứng tuyển khi hồ sơ có họ tên, số điện thoại, vị trí mong
  muốn và ít nhất một kỹ năng hợp lệ. Đính kèm CV chính là tùy chọn.
- Input chấm điểm và bộ trọng số được snapshot cùng transaction tạo đơn.
  QStash chỉ nhận `application_id`; retry luôn dùng lại snapshot này.
- Embedding được sinh sẵn khi hồ sơ/job được lưu. Nếu vector snapshot chưa
  sẵn sàng, task application được phép gọi Gemini từ text snapshot nhưng
  không ghi đè embedding toàn cục của CandidateProfile/JobPost.
- `ApplicationMatchResult` đã tính thành công không bị ghi đè và hồ sơ ứng viên thay đổi
  sau đó không kích hoạt tính lại application cũ.
- Mỗi cặp `(candidate_id, job_id)` chỉ được có **tối đa 1** `JobApplication`.
- Resume/JD Parsing lỗi/timeout: phải cho 2 lựa chọn — thử lại upload, hoặc
  chuyển sang nhập thủ công. Không được chặn luồng hoàn toàn.
- `profile_version` tăng +1 mỗi khi `CandidateProfile` được cập nhật và lưu
  thành công.
- Job đã đóng (`CLOSED`) không chặn việc cập nhật trạng thái các
  `JobApplication` đã nộp từ trước — chỉ chặn nhận thêm ứng viên mới.

### Quy tắc Match Score

- `MatchingWeightConfig` mới mặc định dùng trọng số semantic/skill/experience/
  education lần lượt là `0.35/0.40/0.20/0.05`; hệ số kỹ năng bắt buộc
  `required_skill_multiplier` (ρ) mặc định là `2`. Bốn trọng số phải thuộc
  `[0, 1]`, không âm và có tổng bằng `1`; ρ phải hữu hạn và không nhỏ hơn `1`.
- Kỹ năng được đối sánh bằng định danh ổn định `Skill.id`, không so sánh tên tại
  thời điểm tính điểm. Kỹ năng `PENDING` còn active được phép tham gia hồ sơ đầy
  đủ và đối sánh nếu phía ứng viên và công việc cùng tham chiếu một `Skill.id`.
- Kinh nghiệm dùng ngày đầy đủ từ `DateField`. Mỗi quá trình làm việc là khoảng
  nửa mở `[start_date, end_date)`; công việc hiện tại dùng ngày tạo snapshot đơn
  ứng tuyển làm `end_date`. Các khoảng chồng lấn được hợp nhất trước khi cộng số
  ngày, sau đó số năm kinh nghiệm bằng tổng số ngày chia `365.25`.
- Ngưỡng kinh nghiệm quy đổi theo cấp độ là `ENTRY=0`, `JUNIOR=1`,
  `MID_SENIOR=3`, `LEAD=5` năm. Với yêu cầu `R > 0`, điểm `E = min(1, Y/R)`;
  `ENTRY` đạt `E=1`. Nếu tin không khai cấp độ kinh nghiệm thì tiêu chí không áp
  dụng; nếu có yêu cầu nhưng hồ sơ không có khoảng hợp lệ thì dùng `Y=0`.
- Học vấn dùng `DegreeLevel` có cấu trúc: `NONE < ASSOCIATE < BACHELOR < MASTER
  < PHD`. Chỉ bằng cấp vừa hoàn thành vừa được ứng viên xác nhận mới tham gia.
  Với độ thiếu bậc `d = max(0, rank_required - rank_candidate)`, điểm
  `H = max(0, 1 - 0.25d)`. Không có yêu cầu học vấn thì tiêu chí không áp dụng;
  có yêu cầu nhưng thiếu học vấn hợp lệ thì `H=0`.
- Điểm kỹ năng là `K = (ρM_required + M_preferred) /
  (ρN_required + N_preferred)`. Nếu JD không có kỹ năng thì tiêu chí kỹ năng
  không áp dụng. Semantic, kỹ năng, kinh nghiệm và học vấn đều có miền `[0, 1]`.
- Điểm tổng bằng `100 × Σ(w_i × s_i) / Σ(w_i)` trên đúng các tiêu chí áp dụng.
  Không được coi lỗi tạo embedding là semantic không áp dụng; lỗi xử lý phải đi
  qua trạng thái thất bại thay vì làm tăng điểm do chuẩn hóa lại trọng số.
- Khi tạo đơn, hệ thống snapshot hồ sơ có cấu trúc, JD, `Skill.id`, ngày tạo,
  embedding hiện hành, cấu hình trọng số, ρ và phiên bản quy tắc. Kết quả lưu cả
  tiêu chí áp dụng, trọng số gốc/đã chuẩn hóa, thông tin thiếu và metadata
  embedding để có thể giải thích và tái lập.
- Trạng thái xử lý điểm tách biệt với trạng thái tuyển dụng:
  `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `INSUFFICIENT`. Retry là
  idempotent: kết quả one-to-one đã tồn tại được trả lại, không bị ghi đè.

---

## 5. Coding Conventions

Áp dụng **SOLID**, đặc biệt **Single Responsibility**:

- **View/ViewSet** chỉ xử lý HTTP (nhận request, gọi service/selector, trả
  response). KHÔNG chứa business logic → tránh "fat views".
- **Model** chỉ định nghĩa cấu trúc dữ liệu + validation cấp field. KHÔNG
  nhồi business logic phức tạp vào model → tránh "fat models".
- Toàn bộ business logic đặt trong **Service layer** (`services.py`) hoặc
  **Selector** (`selectors.py`).

```python
# ❌ SAI — business logic nằm trong view
class JobViewSet(viewsets.ModelViewSet):
    def create(self, request):
        if request.user.company.status != "APPROVED":
            return Response({"error": "..."}, status=403)
        job = JobPost.objects.create(...)
        generate_job_embedding.delay(job.id)
        return Response(JobSerializer(job).data)

# ✅ ĐÚNG — view mỏng, gọi service
class JobViewSet(viewsets.ModelViewSet):
    def create(self, request):
        job = job_services.publish_job(
            employer=request.user, data=request.data
        )
        return Response(JobPostSerializer(job).data, status=201)
```

**Serializer/DTO** tách biệt rõ input (validation) và output (response
shape). KHÔNG dùng model trực tiếp làm response.

```python
# ❌ SAI
class JobPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = "__all__"   # dùng chung cho cả input lẫn output

# ✅ ĐÚNG
class JobPostCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    # ... chỉ field cần cho input

class JobPostResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = ["id", "title", "status", "match_score", "created_at"]
```

**Naming:**

```python
# ❌ SAI
def proc(d): ...
class jobdata: ...

# ✅ ĐÚNG
def calculate_match_score(candidate_embedding, job_embedding) -> float: ...
class JobApplication: ...
```

- Tên hàm = động từ (`publish_job`, `calculate_match_score`).
- Tên class = danh từ (`JobApplication`, `SkillNormalizer`).
- Tiếng Anh, rõ ràng, không viết tắt tùy tiện.

**Function size & nesting:** mỗi hàm làm đúng một việc, khuyến nghị dưới
~40 dòng, tránh nesting sâu quá 3 cấp — ưu tiên early return:

```python
# ❌ SAI — nesting sâu
def apply_to_job(candidate, job):
    if candidate.profile_complete:
        if job.status == "active":
            if not JobApplication.objects.filter(candidate=candidate, job=job).exists():
                ...

# ✅ ĐÚNG — early return
def apply_to_job(candidate, job):
    if not candidate.profile_complete:
        raise ProfileIncompleteError()
    if job.status != "active":
        raise JobNotActiveError()
    if JobApplication.objects.filter(candidate=candidate, job=job).exists():
        raise AlreadyAppliedError()
    ...
```

**Không hard-code magic string/number** cho status, role, cấu hình — dùng
Enum/Constants tập trung:

```python
# ❌ SAI
if application.status == "shortlisted": ...

# ✅ ĐÚNG
from apps.applications.constants import ApplicationStatus
if application.status == ApplicationStatus.SHORTLISTED: ...
```

**Xử lý lỗi tường minh** — try/except có chủ đích, không nuốt lỗi im lặng,
log lỗi có ngữ cảnh:

```python
# ❌ SAI
try:
    result = gemini_client.parse_resume(file)
except Exception:
    pass

# ✅ ĐÚNG
try:
    result = gemini_client.parse_resume(file)
except GeminiTimeoutError:
    logger.warning("Gemini resume parsing timeout", extra={"candidate_id": candidate.id})
    return ParseResult(success=False, reason="timeout")
```

**Docstring/type hint** cho public function/class quan trọng. **Đóng gói
logic tái sử dụng** (tính `match_score`, gọi Gemini API) thành class/service
riêng, không copy-paste giữa các app. **Ưu tiên composition** hơn kế thừa
sâu; chỉ dùng kế thừa khi đúng quan hệ "is-a".

---

## 6. Quy ước API

- **REST resource naming**: danh từ số nhiều, kebab/snake theo chuẩn DRF —
  `/api//jobs/`, `/api/candidates/profile/`,
  `/api/companies/{id}/jobs/`, `/api/applications/{id}/status/`
  **(Đề xuất, cần xác nhận — Charter không quy định chi tiết URL pattern)**.
- **Response format chuẩn** — thống nhất qua `common/exceptions.py`
  **(Đề xuất, cần xác nhận cấu trúc chính xác)**:

```json
{
  "success": true,
  "data": { "...": "..." },
  "meta": { "page": 1, "page_size": 20, "total": 100 }
}
```

- **Error format chuẩn**:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Không thể chuyển sang trạng thái này",
    "details": {}
  }
}
```


## 7. Quy ước Testing

- **Unit test (pytest)** — bắt buộc cho mọi hàm trong `services.py` và
  `selectors.py`, đặc biệt: tính `match_score`, validate state machine
  `JobApplication.status`, logic chuẩn hóa skill, logic phê duyệt company.
- **Playwright e2e** — bắt buộc cho các luồng chính theo UC của Charter:
  UC-01 (quản lý hồ sơ ứng viên, cả 2 nhánh upload CV / nhập tay), UC-02
  (đăng tin tuyển dụng), UC-03 (tìm kiếm việc làm, cả nhánh có/không từ
  khóa), UC-04 (ứng tuyển, bao gồm luồng ngoại lệ hồ sơ chưa hoàn thiện),
  UC-05 (xử lý ứng tuyển, bao gồm chặn chuyển trạng thái không hợp lệ).
- Mock Gemini API và các dịch vụ bên ngoài trong test (`config/settings/
  test.py`) — không gọi API thật khi chạy CI.
- Dùng `factory_boy` (`tests/factories.py`) để sinh dữ liệu test, không
  insert dữ liệu thủ công trong từng test case.
- Mọi PR bắt buộc pass lint + test (`ci.yml`) trước khi merge.

---

## 8. Setup & chạy dự án local

```bash
# Tạo file local và điền R2 development credentials
cp job_portal_backend/.env.local.example job_portal_backend/.env.local
cp job_portal_frontend/.env.local.example job_portal_frontend/.env.local

docker compose up --build
```

Local dùng QStash Dev, `LocMemCache`, PostgreSQL + pgvector và bucket R2 private
dành riêng cho development. Hướng dẫn đầy đủ cho local, Render và Vercel nằm ở
[`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 9. Glossary

| Thuật ngữ | Giải nghĩa |
| --- | --- |
| **Embedding** | Vector số thực biểu diễn ngữ nghĩa của văn bản (CV, JD, query), do Gemini Embedding API sinh ra, lưu trong PostgreSQL qua pgvector. |
| **pgvector** | Extension PostgreSQL cho phép lưu và truy vấn vector, dùng để tính khoảng cách/độ tương đồng (Cosine Similarity) hiệu quả. |
| **Match Score** | Điểm phù hợp 0-100 của một đơn ứng tuyển, tổng hợp semantic, kỹ năng, kinh nghiệm và học vấn theo trọng số snapshot và chỉ chuẩn hóa trên các tiêu chí áp dụng. |
| **Semantic Search** | Tìm kiếm dựa trên ý nghĩa (qua embedding + similarity), khác với tìm kiếm từ khóa (keyword/SQL ILIKE). |
| **Skill Taxonomy** | Danh mục kỹ năng chuẩn hóa do Admin quản trị, dùng làm "từ điển" để chuẩn hóa skill trích xuất từ CV/JD. |
| **Skill Normalization** | Quá trình ánh xạ skill viết tự do (từ CV/JD) về dạng chuẩn trong Skill Taxonomy. |
| **profile_snapshot / job_snapshot** | Bản sao dữ liệu hồ sơ có cấu trúc và công việc tại thời điểm ứng tuyển, lưu trong `JobApplication` để kết quả không bị ảnh hưởng bởi thay đổi về sau. File CV đính kèm là tùy chọn và không phải đầu vào trực tiếp của Match Score. |
| **Business Rule Ranking** | Bước xếp hạng cuối trong pipeline AI, kết hợp Match Score với các quy tắc nghiệp vụ khác (nếu có) trước khi trả kết quả. |
| **profile_version** | Số phiên bản hồ sơ ứng viên, tăng +1 mỗi lần cập nhật, dùng để theo dõi lịch sử thay đổi. |
