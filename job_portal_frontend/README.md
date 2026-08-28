# Cấu trúc Frontend — IT Job Portal

> Lấy cảm hứng từ cấu trúc route thật của itviec.com (public job listing, sign-in
> social + email, redirect sau login...), nhưng đã điều chỉnh theo đúng scope và các
> quyết định đã chốt của dự án: KHÔNG có blog/company review/salary report, KHÔNG có
> "Quên mật khẩu", đăng nhập/đăng ký dùng chung 1 trang cho mọi role, `/jobs` công khai
> hoàn toàn (đã sửa lỗi từng đặt nhầm trong route group bị guard).

## Nguyên tắc routing bắt buộc

1. Route công khai và route cần đăng nhập **không bao giờ** tách thành 2 trang riêng
   cho cùng 1 nội dung. Chỉ có 1 trang duy nhất, hành vi thay đổi theo trạng thái đăng
   nhập/role — không nhân đôi code, không nhân đôi route.
2. Route group có `layout.tsx` guard theo role **chỉ** áp cho khu vực thật sự cần đăng
   nhập (dashboard, hồ sơ, quản lý...). Trang duyệt/xem nội dung công khai (`/`, `/jobs`,
   `/jobs/[jobId]`) đứng ngoài mọi route group bị guard.
3. Khi 1 hành động cụ thể (không phải cả trang) cần đăng nhập — ví dụ nút "Ứng tuyển" —
   xử lý bằng **action-level check** ngay trong component, không đẩy thành route-level
   guard: chưa đăng nhập → điều hướng `/login?redirect_to=<url hiện tại>`, đăng nhập
   xong quay lại đúng chỗ và tự tiếp tục hành động đó (không bắt bấm lại).

## Cây thư mục

```
job_portal_frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                        # Landing — hero + thanh search + job nổi bật (PUBLIC)
│   │   ├── layout.tsx                       # Root layout (Navbar + Footer dùng chung mọi trang)
│   │   │
│   │   ├── jobs/                            # PUBLIC — tách khỏi mọi route group bị guard
│   │   │   ├── page.tsx                       # UC-03: tìm kiếm việc làm (SQL filter: vị trí,
│   │   │   │                                  # skill + family, địa điểm, level, lương)
│   │   │   └── [jobId]/
│   │   │       └── page.tsx                   # Chi tiết JD; nút "Ứng tuyển" action-gate,
│   │   │                                      # không route-gate (xem nguyên tắc #3)
│   │   │
│   │   ├── (auth)/                          # PUBLIC — chỉ hiện khi CHƯA đăng nhập
│   │   │   ├── layout.tsx                     # guard ngược: nếu đã login thì redirect ra ngoài
│   │   │   ├── login/
│   │   │   │   └── page.tsx                    # Dùng chung mọi role; Google OAuth + Email/Password;
│   │   │   │                                   # KHÔNG có "Quên mật khẩu"; redirect theo role sau login
│   │   │   └── register/
│   │   │       └── page.tsx                    # Toggle chọn role Candidate/Employer đầu form;
│   │   │                                       # dùng chung component AuthForm với login
│   │   │
│   │   ├── (candidate)/                     # PROTECTED — dùng chung PublicSiteShell + role guard
│   │   │   ├── layout.tsx
│   │   │   ├── candidate/
│   │   │   ├── profile/
│   │   │   │   └── page.tsx                    # UC-01: Upload CV (AI trích xuất) / nhập thủ công
│   │   │   └── applications/
│   │   │       └── page.tsx                    # Theo dõi trạng thái đơn ứng tuyển (UC liên quan UC-04)
│   │   │
│   │   ├── (employer)/                      # PROTECTED — dùng chung PublicSiteShell + role guard
│   │   │   ├── layout.tsx                     # Company chưa APPROVED chỉ bị chặn tạo tin mới
│   │   │   ├── employer/
│   │   │   │   └── page.tsx                    # Dashboard: số tin active, ứng viên mới
│   │   │   ├── company/
│   │   │   │   └── page.tsx                    # Hồ sơ công ty + hiển thị trạng thái duyệt
│   │   │   └── jobs/
│   │   │       ├── page.tsx                    # Danh sách tin đã đăng (status, số ứng viên)
│   │   │       ├── new/
│   │   │       │   └── page.tsx                  # Tạo tin tuyển dụng
│   │   │       └── [jobId]/
│   │   │           ├── edit/
│   │   │           │   └── page.tsx               # Sửa tin
│   │   │           └── applications/
│   │   │               └── page.tsx               # UC-05: danh sách ứng viên, sort match_score,
│   │   │                                          # section "Ứng viên gợi ý" gộp trong trang này
│   │   │
│   │   └── (admin)/                         # PROTECTED — dùng chung PublicSiteShell + role guard
│   │       ├── layout.tsx
│   │       ├── admin/
│   │       │   └── page.tsx                    # Dashboard thống kê tổng
│   │       ├── companies/
│   │       │   └── page.tsx                    # Duyệt hồ sơ công ty (pending/approved/rejected)
│   │       ├── users/
│   │       │   └── page.tsx                    # Quản lý tài khoản người dùng
│   │       └── skills/
│   │           └── page.tsx                    # Quản trị Skill Taxonomy: CRUD skill/alias/family,
│   │                                           # duyệt skill "pending" từ AI trích xuất, cấu hình
│   │                                           # trọng số Business Rule Ranking
│   │
│   ├── features/                            # Giữ nguyên theo charter gốc — mỗi thư mục ↔ 1 app Django
│   │   ├── auth/  companies/  candidates/  skills/  jobs/  applications/  ai-analysis/
│   │   │   └── api.ts / types.ts / hooks.ts / components/    (không đổi so với bản trước)
│   │
│   ├── components/
│   │   ├── ui/                                # shadcn/ui primitives
│   │   ├── layout/                            # Navbar, Footer — dùng ở root layout.tsx, không
│   │   │                                       # lặp lại trong từng route group
│   │   └── shared/                              # JobCard, StatusBadge, dùng ở cả /jobs (public)
│   │                                            # lẫn (employer)/jobs (protected)
│   │
│   ├── lib/            # api-client.ts, query-client.ts, utils.ts — không đổi
│   ├── middleware.ts   # CHỈ áp guard role cho (candidate)/(employer)/(admin);
│   │                    # (auth) guard ngược (đã login thì đá ra); "/" và "/jobs/*" không đụng tới
│   └── config/env.ts
│
├── public/
└── ... (giữ nguyên phần còn lại theo bản charter gốc)
```

## Bảng route — Access Control

| Route | Truy cập | Ghi chú |
|---|---|---|
| `/` | Public | Landing — hero + search bar + job nổi bật |
| `/jobs` | Public | UC-03, không cần đăng nhập |
| `/jobs/[jobId]` | Public | Xem JD tự do; nút "Ứng tuyển" action-gate |
| `/login` | Public (chỉ hiện khi chưa đăng nhập) | Dùng chung mọi role, redirect theo role sau login |
| `/register` | Public (chỉ hiện khi chưa đăng nhập) | Toggle chọn role ngay trong form |
| `/candidate/*` | Protected — CANDIDATE | Guard ở `(candidate)/layout.tsx` |
| `/employer/*` | Protected — EMPLOYER | Guard ở `(employer)/layout.tsx`, kèm chặn phụ theo `Company.status` |
| `/admin/*` | Protected — ADMIN | Guard ở `(admin)/layout.tsx` |

## Ví dụ pattern action-level gate (redirect_to)

```ts
// trong component nút "Ứng tuyển" tại app/jobs/[jobId]/page.tsx
const handleApplyClick = () => {
  if (!user) {
    router.push(`/login?redirect_to=${pathname}`);
    return;
  }
  if (user.role !== "candidate") {
    toast.error("Chỉ Ứng viên mới ứng tuyển được");
    return;
  }
  setApplyModalOpen(true); // mở form ngay tại chỗ, không điều hướng
};
```

## Khác biệt có chủ đích so với ITviec (đã lược bỏ vì ngoài scope)

- Không tách `/sign_in` và `/employer/sign_in` riêng như ITviec — dùng chung `/login`.
- Không có mega-menu Jobs by Skill/Expertise/Title/Company/City (các trang SEO landing
  riêng lẻ) — lọc gộp hết trong `/jobs`.
- Không có Blog, Company Reviews, IT Salary Report, Story Hub.
- Không có "Quên mật khẩu".

Nếu sau này thêm route mới, luôn tự hỏi trước: *"route này có nội dung xem được công
khai không, hay chỉ có hành động cần đăng nhập?"* — trả lời sai câu này chính là nguyên
nhân gây ra lỗi `jobs/` từng bị nhét nhầm vào `(candidate)/` lúc đầu.
