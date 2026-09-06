"""Du lieu 10 CV mau cho seed_sample_candidates, tach khoi command."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.candidates.models import CandidateProfile, Education, Experience
from apps.skills.models import Skill, CandidateSkill

User = get_user_model()

CATEGORY_MAP = {
    "Ngôn ngữ lập trình": ["Java", "Python", "JavaScript", "TypeScript", "C#", "Go", "Kotlin", "Swift", "Dart", "PHP"],
    "Frontend": ["React", "Vue.js", "Angular", "HTML/CSS", "Next.js"],
    "Backend": ["Spring Boot", "Node.js", "Express", "Django", "ASP.NET Core", "NestJS", "Laravel"],
    "Database": ["PostgreSQL", "MySQL", "MongoDB", "Redis"],
    "DevOps/Cloud": ["Docker", "Kubernetes", "AWS", "CI/CD", "GCP", "Jenkins", "Terraform"],
    "Mobile": ["Flutter", "React Native", "iOS (Swift)", "Android (Kotlin)"],
    "AI/Data": ["Machine Learning", "TensorFlow", "PyTorch", "Pandas", "SQL", "Airflow", "Spark"],
    "Testing": ["Selenium", "Manual Testing", "API Testing", "JMeter", "Cypress"],
    "Game": ["Unity", "C++", "Unreal Engine"],
    "Khác": ["Git", "Agile/Scrum", "REST API", "Microservices", "Figma", "Jira"],
}

# 10 CV mẫu, phủ các it_role_type xuất hiện nhiều nhất trong bộ JD.
CANDIDATES = [
    {
        "email": "nguyen.van.an@example.com",
        "username": "nguyenvanan",
        "full_name": "Nguyễn Văn An",
        "headline": "Backend Developer (Java / Spring Boot)",
        "desired_position": "Backend Developer",
        "address": "Cầu Giấy, Hà Nội",
        "summary": "3 năm kinh nghiệm xây dựng REST API và microservices bằng Java/Spring Boot, "
                   "quen thuộc với PostgreSQL, Docker và triển khai CI/CD cơ bản.",
        "education": {"school_name": "Đại học Bách Khoa Hà Nội", "major": "Khoa học máy tính",
                       "degree": "Cử nhân", "start_date": "2016-09-01", "end_date": "2020-06-01"},
        "experiences": [
            {"company_name": "FPT Software", "position": "Backend Developer",
             "start_date": "2020-08-01", "end_date": None, "is_current": True,
             "description": "Phát triển và bảo trì các microservice xử lý đơn hàng, tối ưu truy vấn PostgreSQL."},
        ],
        "skills": [("Java", "ADVANCED", 3.5), ("Spring Boot", "ADVANCED", 3),
                   ("PostgreSQL", "INTERMEDIATE", 3), ("Docker", "INTERMEDIATE", 2),
                   ("REST API", "ADVANCED", 3), ("Git", "ADVANCED", 3)],
    },
    {
        "email": "tran.thi.bich@example.com",
        "username": "tranthibich",
        "full_name": "Trần Thị Bích",
        "headline": "Frontend Developer (React / TypeScript)",
        "desired_position": "Frontend Developer",
        "address": "Quận 1, Hồ Chí Minh",
        "summary": "2.5 năm xây dựng giao diện web với React và TypeScript, chú trọng performance "
                   "và trải nghiệm người dùng, từng làm việc trực tiếp với designer theo Figma.",
        "education": {"school_name": "Đại học Khoa học Tự nhiên TP.HCM", "major": "Công nghệ thông tin",
                       "degree": "Cử nhân", "start_date": "2017-09-01", "end_date": "2021-06-01"},
        "experiences": [
            {"company_name": "Tiki", "position": "Frontend Developer",
             "start_date": "2021-07-01", "end_date": None, "is_current": True,
             "description": "Xây dựng các trang sản phẩm với React/Next.js, tối ưu Core Web Vitals."},
        ],
        "skills": [("React", "ADVANCED", 2.5), ("TypeScript", "ADVANCED", 2), ("Next.js", "INTERMEDIATE", 1.5),
                   ("HTML/CSS", "ADVANCED", 2.5), ("Figma", "BASIC", 1), ("Git", "ADVANCED", 2.5)],
    },
    {
        "email": "le.hoang.cuong@example.com",
        "username": "lehoangcuong",
        "full_name": "Lê Hoàng Cường",
        "headline": "Full-stack Developer (Node.js / React)",
        "desired_position": "Full-stack Developer",
        "address": "Đống Đa, Hà Nội",
        "summary": "4 năm kinh nghiệm full-stack với Node.js/Express ở backend và React ở frontend, "
                   "từng dẫn dắt 1 nhóm 3 người trong dự án SaaS nội bộ.",
        "education": {"school_name": "Đại học FPT", "major": "Kỹ thuật phần mềm",
                       "degree": "Cử nhân", "start_date": "2015-09-01", "end_date": "2019-06-01"},
        "experiences": [
            {"company_name": "K&M Holdings", "position": "Fullstack Developer",
             "start_date": "2019-08-01", "end_date": "2023-03-01", "is_current": False,
             "description": "Xây dựng module billing/metering và giao diện quản trị nội bộ."},
            {"company_name": "Base.vn", "position": "Senior Fullstack Developer",
             "start_date": "2023-04-01", "end_date": None, "is_current": True,
             "description": "Phụ trách module tích hợp API bên thứ 3 và refactor kiến trúc backend."},
        ],
        "skills": [("Node.js", "ADVANCED", 4), ("Express", "ADVANCED", 4), ("React", "INTERMEDIATE", 3),
                   ("MongoDB", "INTERMEDIATE", 3), ("Docker", "INTERMEDIATE", 2), ("Microservices", "INTERMEDIATE", 2)],
    },
    {
        "email": "pham.thi.dung@example.com",
        "username": "phamthidung",
        "full_name": "Phạm Thị Dung",
        "headline": "QA Engineer (Manual & Automation)",
        "desired_position": "QA Engineer",
        "address": "Thanh Xuân, Hà Nội",
        "summary": "2 năm kinh nghiệm kiểm thử phần mềm, thành thạo test case/test plan, "
                   "bắt đầu chuyển sang automation testing với Selenium.",
        "education": {"school_name": "Học viện Công nghệ Bưu chính Viễn thông", "major": "Công nghệ thông tin",
                       "degree": "Cử nhân", "start_date": "2018-09-01", "end_date": "2022-06-01"},
        "experiences": [
            {"company_name": "VNG Corporation", "position": "QA Engineer",
             "start_date": "2022-07-01", "end_date": None, "is_current": True,
             "description": "Thiết kế test case, thực hiện regression testing và automation cơ bản với Selenium."},
        ],
        "skills": [("Manual Testing", "ADVANCED", 2), ("Selenium", "INTERMEDIATE", 1), ("API Testing", "INTERMEDIATE", 1.5),
                   ("SQL", "INTERMEDIATE", 2), ("Jira", "ADVANCED", 2)],
    },
    {
        "email": "hoang.minh.duc@example.com",
        "username": "hoangminhduc",
        "full_name": "Hoàng Minh Đức",
        "headline": "Mobile Developer (Flutter)",
        "desired_position": "Mobile Developer",
        "address": "Hải Châu, Đà Nẵng",
        "summary": "2 năm phát triển ứng dụng di động cross-platform bằng Flutter, đã publish 3 app "
                   "lên cả App Store và Google Play.",
        "education": {"school_name": "Đại học Bách Khoa Đà Nẵng", "major": "Công nghệ thông tin",
                       "degree": "Cử nhân", "start_date": "2018-09-01", "end_date": "2022-06-01"},
        "experiences": [
            {"company_name": "Axon Active Vietnam", "position": "Mobile Developer",
             "start_date": "2022-08-01", "end_date": None, "is_current": True,
             "description": "Phát triển app đặt lịch cho khách hàng châu Âu bằng Flutter, tích hợp Firebase."},
        ],
        "skills": [("Flutter", "ADVANCED", 2), ("Dart", "ADVANCED", 2), ("REST API", "INTERMEDIATE", 2),
                   ("Git", "ADVANCED", 2), ("Agile/Scrum", "INTERMEDIATE", 2)],
    },
    {
        "email": "vu.thi.giang@example.com",
        "username": "vuthigiang",
        "full_name": "Vũ Thị Giang",
        "headline": "Software Engineer (.NET)",
        "desired_position": "Software Engineer",
        "address": "Quận 7, Hồ Chí Minh",
        "summary": "3 năm kinh nghiệm phát triển ứng dụng doanh nghiệp bằng C#/ASP.NET Core, "
                   "làm việc trong môi trường outsourcing cho khách hàng Nhật Bản.",
        "education": {"school_name": "Đại học Công nghệ - ĐHQGHN", "major": "Khoa học máy tính",
                       "degree": "Cử nhân", "start_date": "2016-09-01", "end_date": "2020-06-01"},
        "experiences": [
            {"company_name": "NashTech", "position": "Software Engineer",
             "start_date": "2020-09-01", "end_date": None, "is_current": True,
             "description": "Phát triển hệ thống quản lý kho vận cho khách hàng Nhật, dùng ASP.NET Core và SQL Server."},
        ],
        "skills": [("C#", "ADVANCED", 3), ("ASP.NET Core", "ADVANCED", 3), ("MySQL", "INTERMEDIATE", 3),
                   ("Git", "ADVANCED", 3), ("Agile/Scrum", "INTERMEDIATE", 2)],
    },
    {
        "email": "do.quang.huy@example.com",
        "username": "doquanghuy",
        "full_name": "Đỗ Quang Huy",
        "headline": "Game Developer (Unity)",
        "desired_position": "Game Developer",
        "address": "Cầu Giấy, Hà Nội",
        "summary": "2 năm làm game mobile casual bằng Unity/C#, có kinh nghiệm tối ưu hiệu năng "
                   "cho thiết bị cấu hình thấp.",
        "education": {"school_name": "Đại học FPT", "major": "Thiết kế đồ họa & lập trình game",
                       "degree": "Cử nhân", "start_date": "2018-09-01", "end_date": "2022-06-01"},
        "experiences": [
            {"company_name": "Amanotes", "position": "Game Developer",
             "start_date": "2022-07-01", "end_date": None, "is_current": True,
             "description": "Phát triển gameplay và tối ưu performance cho các game âm nhạc casual trên mobile."},
        ],
        "skills": [("Unity", "ADVANCED", 2), ("C#", "ADVANCED", 2), ("Git", "INTERMEDIATE", 2)],
    },
    {
        "email": "bui.thi.kim@example.com",
        "username": "buithikim",
        "full_name": "Bùi Thị Kim",
        "headline": "AI Engineer (Machine Learning)",
        "desired_position": "AI Engineer",
        "address": "Hai Bà Trưng, Hà Nội",
        "summary": "2 năm kinh nghiệm xây dựng và triển khai mô hình machine learning, "
                   "quen thuộc với PyTorch và các pipeline xử lý dữ liệu bằng Pandas.",
        "education": {"school_name": "Đại học Bách Khoa Hà Nội", "major": "Khoa học dữ liệu",
                       "degree": "Thạc sĩ", "start_date": "2019-09-01", "end_date": "2023-06-01"},
        "experiences": [
            {"company_name": "VinAI Research", "position": "AI Engineer",
             "start_date": "2023-07-01", "end_date": None, "is_current": True,
             "description": "Huấn luyện và fine-tune mô hình NLP tiếng Việt, xây dựng pipeline đánh giá mô hình."},
        ],
        "skills": [("Python", "ADVANCED", 3), ("PyTorch", "ADVANCED", 2), ("Machine Learning", "ADVANCED", 2.5),
                   ("Pandas", "ADVANCED", 2.5), ("SQL", "INTERMEDIATE", 2)],
    },
    {
        "email": "ngo.van.long@example.com",
        "username": "ngovanlong",
        "full_name": "Ngô Văn Long",
        "headline": "Business Analyst (Fintech/Banking)",
        "desired_position": "Business Analyst",
        "address": "Ba Đình, Hà Nội",
        "summary": "3 năm kinh nghiệm phân tích nghiệp vụ trong lĩnh vực fintech, viết BRD/SRS, "
                   "làm việc trực tiếp với đội phát triển theo mô hình Agile.",
        "education": {"school_name": "Đại học Kinh tế Quốc dân", "major": "Hệ thống thông tin quản lý",
                       "degree": "Cử nhân", "start_date": "2015-09-01", "end_date": "2019-06-01"},
        "experiences": [
            {"company_name": "MoMo", "position": "Business Analyst",
             "start_date": "2019-08-01", "end_date": None, "is_current": True,
             "description": "Phân tích yêu cầu nghiệp vụ cho các tính năng ví điện tử, viết tài liệu đặc tả cho đội dev."},
        ],
        "skills": [("Agile/Scrum", "ADVANCED", 3), ("SQL", "INTERMEDIATE", 2), ("Jira", "ADVANCED", 3),
                   ("REST API", "BASIC", 1)],
    },
    {
        "email": "dang.thi.mai@example.com",
        "username": "dangthimai",
        "full_name": "Đặng Thị Mai",
        "headline": "DevOps Engineer",
        "desired_position": "DevOps Engineer",
        "address": "Quận Bình Thạnh, Hồ Chí Minh",
        "summary": "3 năm kinh nghiệm vận hành hạ tầng cloud AWS, thiết lập CI/CD pipeline "
                   "và container hóa dịch vụ với Docker/Kubernetes.",
        "education": {"school_name": "Đại học Sư phạm Kỹ thuật TP.HCM", "major": "Công nghệ thông tin",
                       "degree": "Cử nhân", "start_date": "2016-09-01", "end_date": "2020-06-01"},
        "experiences": [
            {"company_name": "Sendo", "position": "DevOps Engineer",
             "start_date": "2020-08-01", "end_date": None, "is_current": True,
             "description": "Quản lý cụm Kubernetes trên AWS, xây dựng pipeline CI/CD bằng Jenkins."},
        ],
        "skills": [("AWS", "ADVANCED", 3), ("Docker", "ADVANCED", 3), ("Kubernetes", "INTERMEDIATE", 2),
                   ("CI/CD", "ADVANCED", 3), ("Jenkins", "INTERMEDIATE", 2), ("Terraform", "BASIC", 1)],
    },
]
