"""Sinh ra jobs_200_curated.json - 200 JobPosts chuẩn hóa.

Phân loại theo mức độ phổ biến của vai trò:
  - common (120 / 60%): Backend, Frontend, Full-stack, Mobile, QA/Testing, Software/.NET
  - average (60 / 30%): DevOps, Cloud, Data, Database, BA, PM/Scrum, UX/UI, System/SRE, Networking
  - rare (20 / 10%): AI/ML Research, Quant, Game, Security/Offensive, Blockchain, Robotics,
                     Embedded/Firmware, Big Data (Spark/Kafka), Quantum/Edge

Chạy: python gen_jobs_200.py  → tạo jobs_200_curated.json
"""
import json
import random
from pathlib import Path

random.seed(42)

HERE = Path(__file__).resolve().parent
SKILLS_BY_CATEGORY = {
    "Backend": ["Python", "Java", "Go", "Node.js", "PHP", "Ruby", "C#", "Django", "Spring Boot", "FastAPI", "MySQL", "PostgreSQL", "Redis", "Docker", "Kubernetes", "GraphQL", "Nginx"],
    "Frontend": ["React", "Next.js", "Vue.js", "Angular", "TypeScript", "JavaScript", "Tailwind CSS", "Redux", "Svelte", "HTML", "CSS", "Figma", "Vite"],
    "Fullstack": ["React", "Node.js", "TypeScript", "Next.js", "Django", "PostgreSQL", "Docker", "GraphQL", "Spring Boot"],
    "Mobile": ["Flutter", "React Native", "Swift", "Kotlin", "Android SDK", "iOS Development", "Java", "Dart", "Jetpack Compose"],
    "QA": ["Manual Testing", "Test Automation", "Selenium", "Cypress", "Playwright", "JUnit", "pytest", "JMeter", "Postman", "API Testing", "Jira"],
    "Software/.NET": ["C#", "ASP.NET Core", ".NET MAUI", "Microsoft SQL Server", "Microsoft Azure", "TypeScript", "Angular"],
    "DevOps": ["Docker", "Kubernetes", "Jenkins", "Terraform", "Ansible", "GitHub Actions", "Prometheus", "Grafana", "Linux System Administration", "ArgoCD", "Helm"],
    "Cloud": ["Amazon Web Services", "Google Cloud Platform", "Microsoft Azure", "Terraform", "Serverless Architecture", "AWS Lambda", "Amazon EC2"],
    "Data": ["Python", "SQL", "Pandas", "NumPy", "Power BI", "Tableau", "ETL", "Data Analysis", "Data Engineering"],
    "Database": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Oracle Database", "Microsoft SQL Server", "Elasticsearch", "Cassandra"],
    "BA": ["Agile", "Scrum", "Jira", "Confluence", "Giao tiếp", "SQL", "Figma", "Wireframing"],
    "PM": ["Agile", "Scrum", "Kanban", "Quản lý dự án", "Jira", "Giao tiếp", "Lãnh đạo", "Confluence"],
    "UX/UI": ["Figma", "UI Design", "UX Design", "Adobe XD", "Prototyping", "Wireframing", "Sketch", "HTML", "CSS"],
    "System/SRE": ["Linux System Administration", "Prometheus", "Grafana", "Kubernetes", "Python", "Elasticsearch", "Nginx", "Docker"],
    "Networking": ["Linux System Administration", "Nginx", "Network Security", "Application Security", "Bash/Shell Scripting"],
    "AI/ML": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision", "Large Language Models", "Pandas", "Scikit-learn"],
    "Quant": ["Python", "R", "Pandas", "NumPy", "SQL", "Machine Learning", "Data Analysis"],
    "Game": ["C#", "C++", "Design Patterns", "Git", "Python", "Large Language Models"],
    "Security": ["Application Security", "OWASP", "Penetration Testing", "Network Security", "Cybersecurity", "Python", "Linux System Administration"],
    "Blockchain": ["Rust", "Go", "C++", "Cybersecurity", "JavaScript", "Python"],
    "Robotics": ["Python", "C++", "Machine Learning", "Computer Vision", "Linux System Administration"],
    "Embedded": ["C", "C++", "Linux System Administration", "Python"],
    "Big Data": ["Apache Spark", "Apache Kafka", "Python", "Scala", "ETL", "SQL", "Data Engineering"],
}

CORE_SKILLS_BY_ROLE = {
    "Java Developer": ["Java", "Spring Boot"],
    "Frontend Developer": ["JavaScript", "TypeScript", "React"],
    "Full-stack Developer": ["React", "Node.js", "TypeScript"],
    "Mobile Developer": ["Flutter", "Dart"],
    "QA / Tester": ["Manual Testing", "Test Automation"],
    "Software Engineer (.NET/C#)": ["C#", "ASP.NET Core"],
    "Node.js Developer": ["Node.js", "JavaScript"],
    "PHP Developer": ["PHP", "MySQL"],
    "Android Developer": ["Kotlin", "Android SDK"],
    "iOS Developer": ["Swift", "iOS Development"],
    "DevOps Engineer": ["Docker", "Kubernetes"],
    "Cloud Engineer": ["Amazon Web Services", "Terraform"],
    "Data Engineer": ["Python", "SQL", "Data Engineering"],
    "Data Analyst": ["SQL", "Data Analysis"],
    "Database Engineer / DBA": ["PostgreSQL", "MySQL"],
    "Business Analyst": ["Agile", "Jira"],
    "IT Project Manager": ["Quản lý dự án", "Agile"],
    "UX/UI Designer": ["Figma", "UI Design", "UX Design"],
    "Site Reliability Engineer": ["Linux System Administration", "Prometheus"],
    "System Administrator": ["Linux System Administration", "Network Security"],
    "AI / Machine Learning Engineer": ["Python", "Machine Learning"],
    "NLP / LLM Engineer": ["Python", "Natural Language Processing", "Large Language Models"],
    "Data Scientist (Deep Learning)": ["Python", "Deep Learning"],
    "Game Developer": ["C#", "C++"],
    "Security Penetration Tester": ["Penetration Testing", "Application Security"],
    "Blockchain Engineer": ["Rust", "Go"],
    "Embedded / Firmware Engineer": ["C", "C++"],
    "Big Data Engineer (Spark)": ["Apache Spark", "Apache Kafka"],
}

BACKEND_STACKS = (
    ["Python", "Django"],
    ["Python", "FastAPI"],
    ["Go"],
    ["Node.js"],
    ["PHP"],
)

BACKEND_PRIMARY_SKILLS = {
    "Python", "Java", "Go", "Node.js", "PHP", "Ruby", "C#",
    "Django", "Spring Boot", "FastAPI",
}

OPTIONAL_SKILLS_BY_ROLE = {
    "Frontend Developer": ["Next.js", "Tailwind CSS", "Redux", "HTML", "CSS", "Figma", "Vite"],
    "Full-stack Developer": ["Next.js", "PostgreSQL", "Docker", "GraphQL"],
    "Mobile Developer": ["React Native", "Android SDK", "iOS Development"],
    "Node.js Developer": ["TypeScript", "PostgreSQL", "Redis", "Docker", "GraphQL", "Nginx"],
    "PHP Developer": ["PostgreSQL", "Redis", "Docker", "GraphQL", "Nginx"],
    "Android Developer": ["Java", "Jetpack Compose", "Flutter", "Dart"],
    "iOS Developer": ["Swift", "iOS Development", "React Native", "Flutter"],
    "Data Engineer": ["Python", "SQL", "Pandas", "ETL", "Data Engineering"],
    "Data Analyst": ["Python", "Pandas", "Power BI", "Tableau"],
    "Game Developer": ["Design Patterns", "Git"],
    "Big Data Engineer (Spark)": ["Python", "Scala", "ETL", "SQL", "Data Engineering"],
}

COMPANIES_COMMON = [
    "FPT Software", "TMA Solutions", "KMS Technology", "Rikkeisoft", "VNG Corporation",
    "Viettel Group", "MISA", "VNPT", "CMC Corporation", "DXC Technology", "AGEST Vietnam",
    "VTI Vietnam", "NashTech Vietnam", "Base Enterprise", "VCCorp", "MobiFone",
]
COMPANIES_AVERAGE = [
    "FPT Software", "TMA Solutions", "KMS Technology", "VNPAY", "Viettel Group",
    "Rikkeisoft", "MISA", "VNPT", "CMC Corporation", "AGEST Vietnam", "VTI Vietnam",
    "NashTech Vietnam", "DXC Technology", "VNG Corporation", "Base Enterprise",
]
COMPANIES_RARE = [
    "Samsung R&D Vietnam", "Bosch Vietnam", "Intel Vietnam", "Viettel Group",
    "VinAI Research", "FPT Software", "VNPAY", "VNG Corporation",
]


def pick_location(rng):
    return rng.choice(["Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Hồ Chí Minh", "Hà Nội"])


def enum_field(name, choices, rng):
    return rng.choice(list(choices))


def make_salary(level, rng):
    bands = {
        "ENTRY": (5_000_000, 15_000_000),
        "JUNIOR": (12_000_000, 25_000_000),
        "MID_SENIOR": (20_000_000, 45_000_000),
        "LEAD": (40_000_000, 80_000_000),
    }
    lo, hi = bands[level]
    mid = (lo + hi) // 2
    salary_min = rng.randint(lo, mid - 1_000_000)
    salary_max = rng.randint(max(salary_min + 1_000_000, mid), hi)
    return salary_min, salary_max


JOB_BLUEPRINTS = {
# ---------------- PHỔ BIẾN (120) ----------------
    "Backend Developer": {"cat": "Backend", "pop": "common", "mult": 18, "level_weights": ["JUNIOR", "MID_SENIOR", "JUNIOR", "MID_SENIOR", "ENTRY", "MID_SENIOR"]},
    "Java Developer": {"cat": "Backend", "pop": "common", "mult": 14, "level_weights": ["JUNIOR", "MID_SENIOR", "MID_SENIOR", "JUNIOR"]},
    "Frontend Developer": {"cat": "Frontend", "pop": "common", "mult": 16, "level_weights": ["JUNIOR", "MID_SENIOR", "JUNIOR", "MID_SENIOR", "ENTRY"]},
    "Full-stack Developer": {"cat": "Fullstack", "pop": "common", "mult": 14, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR", "LEAD"]},
    "Mobile Developer": {"cat": "Mobile", "pop": "common", "mult": 12, "level_weights": ["JUNIOR", "MID_SENIOR", "JUNIOR", "MID_SENIOR"]},
    "QA / Tester": {"cat": "QA", "pop": "common", "mult": 14, "level_weights": ["ENTRY", "JUNIOR", "MID_SENIOR", "JUNIOR"]},
    "Software Engineer (.NET/C#)": {"cat": "Software/.NET", "pop": "common", "mult": 14, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR", "LEAD"]},
    "Node.js Developer": {"cat": "Backend", "pop": "common", "mult": 6, "level_weights": ["JUNIOR", "JUNIOR", "MID_SENIOR"]},
    "PHP Developer": {"cat": "Backend", "pop": "common", "mult": 6, "level_weights": ["JUNIOR", "JUNIOR", "MID_SENIOR"]},
    "Android Developer": {"cat": "Mobile", "pop": "common", "mult": 3, "level_weights": ["JUNIOR", "MID_SENIOR", "JUNIOR"]},
    "iOS Developer": {"cat": "Mobile", "pop": "common", "mult": 3, "level_weights": ["JUNIOR", "MID_SENIOR", "JUNIOR"]},
# ---------------- TRUNG BÌNH (60) ----------------
    "DevOps Engineer": {"cat": "DevOps", "pop": "average", "mult": 10, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR", "LEAD"]},
    "Cloud Engineer": {"cat": "Cloud", "pop": "average", "mult": 6, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR"]},
    "Data Engineer": {"cat": "Data", "pop": "average", "mult": 6, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR"]},
    "Data Analyst": {"cat": "Data", "pop": "average", "mult": 6, "level_weights": ["JUNIOR", "MID_SENIOR", "ENTRY"]},
    "Database Engineer / DBA": {"cat": "Database", "pop": "average", "mult": 5, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR"]},
    "Business Analyst": {"cat": "BA", "pop": "average", "mult": 7, "level_weights": ["MID_SENIOR", "JUNIOR", "MID_SENIOR"]},
    "IT Project Manager": {"cat": "PM", "pop": "average", "mult": 6, "level_weights": ["MID_SENIOR", "LEAD", "MID_SENIOR"]},
    "UX/UI Designer": {"cat": "UX/UI", "pop": "average", "mult": 6, "level_weights": ["JUNIOR", "MID_SENIOR", "JUNIOR"]},
    "Site Reliability Engineer": {"cat": "System/SRE", "pop": "average", "mult": 4, "level_weights": ["MID_SENIOR", "LEAD"]},
    "System Administrator": {"cat": "System/SRE", "pop": "average", "mult": 4, "level_weights": ["JUNIOR", "MID_SENIOR"]},
# ---------------- HIẾM (20) ----------------
    "AI / Machine Learning Engineer": {"cat": "AI/ML", "pop": "rare", "mult": 5, "level_weights": ["MID_SENIOR", "LEAD", "MID_SENIOR"]},
    "NLP / LLM Engineer": {"cat": "AI/ML", "pop": "rare", "mult": 3, "level_weights": ["MID_SENIOR", "LEAD"]},
    "Data Scientist (Deep Learning)": {"cat": "AI/ML", "pop": "rare", "mult": 2, "level_weights": ["MID_SENIOR"]},
    "Game Developer": {"cat": "Game", "pop": "rare", "mult": 2, "level_weights": ["MID_SENIOR", "JUNIOR"]},
    "Security Penetration Tester": {"cat": "Security", "pop": "rare", "mult": 2, "level_weights": ["MID_SENIOR"]},
    "Blockchain Engineer": {"cat": "Blockchain", "pop": "rare", "mult": 2, "level_weights": ["MID_SENIOR"]},
    "Embedded / Firmware Engineer": {"cat": "Embedded", "pop": "rare", "mult": 2, "level_weights": ["MID_SENIOR", "JUNIOR"]},
    "Big Data Engineer (Spark)": {"cat": "Big Data", "pop": "rare", "mult": 2, "level_weights": ["MID_SENIOR"]},
}


def experience_title(level):
    return {
        "ENTRY": "", "JUNIOR": "Junior ", "MID_SENIOR": "", "LEAD": "Lead / "
    }[level]


def display_role_title(base_title, core_skills):
    if base_title != "Backend Developer":
        return base_title
    stack = "/".join(core_skills)
    return f"{stack} Backend Developer"


def optional_skill_pool(base_title, category, core_skills):
    if base_title in OPTIONAL_SKILLS_BY_ROLE:
        pool = OPTIONAL_SKILLS_BY_ROLE[base_title]
    elif category == "Backend":
        pool = [
            skill
            for skill in SKILLS_BY_CATEGORY[category]
            if skill not in BACKEND_PRIMARY_SKILLS
        ]
    else:
        pool = SKILLS_BY_CATEGORY[category]
    return [skill for skill in dict.fromkeys(pool) if skill not in core_skills]


ROLE_DESCRIPTIONS = {
    "Backend Developer": "Thiết kế, phát triển và vận hành các dịch vụ API, hệ thống xử lý nghiệp vụ phía server. Tối ưu hiệu năng, bảo mật và khả năng mở rộng của hệ thống.",
    "Java Developer": "Phát triển ứng dụng doanh nghiệp sử dụng hệ sinh thái Java/Spring Boot, viết microservices, tối ưu truy vấn cơ sở dữ liệu.",
    "Frontend Developer": "Xây dựng giao diện web hiện đại, responsive và tối ưu tốc độ tải trang. Phối hợp chặt chẽ với đội backend và design.",
    "Full-stack Developer": "Phát triển toàn bộ ứng dụng từ UI tới API và database, tự chủ tính năng từ đầu tới cuối.",
    "Mobile Developer": "Phát triển ứng dụng di động đa nền tảng hoặc native, đảm bảo trải nghiệm mượt mà và hiệu năng tốt.",
    "QA / Tester": "Đảm bảo chất lượng phần mềm thông qua kiểm thử thủ công và tự động hóa, viết test case, theo dõi bug.",
    "Software Engineer (.NET/C#)": "Phát triển ứng dụng trong hệ sinh thái Microsoft .NET, tích hợp dịch vụ Azure, xây dựng API và dịch vụ nền tảng.",
    "Node.js Developer": "Phát triển dịch vụ API và ứng dụng web với Node.js, tối ưu hiệu năng và khả năng mở rộng.",
    "PHP Developer": "Phát triển và bảo trì ứng dụng web PHP, thiết kế API và tối ưu truy vấn cơ sở dữ liệu.",
    "Android Developer": "Phát triển ứng dụng Android native với Kotlin, đảm bảo chất lượng và đúng chuẩn Google Play.",
    "iOS Developer": "Phát triển ứng dụng iOS native với Swift, đảm bảo chất lượng và đúng chuẩn App Store.",
    "DevOps Engineer": "Xây dựng hạ tầng CI/CD, tự động hóa triển khai, giám sát hệ thống, áp dụng quy trình Infrastructure as Code.",
    "Cloud Engineer": "Thiết kế và vận hành hệ thống trên AWS/GCP/Azure, tối ưu chi phí và độ sẵn sàng cao.",
    "Data Engineer": "Xây dựng pipeline xử lý dữ liệu, chuẩn hóa và vận hành data warehouse phục vụ phân tích.",
    "Data Analyst": "Phân tích dữ liệu kinh doanh, dựng báo cáo và dashboard, đưa ra insight cho quyết định.",
    "Database Engineer / DBA": "Quản trị cơ sở dữ liệu, tối ưu hiệu năng truy vấn, thiết kế schema và đảm bảo backup/khôi phục.",
    "Business Analyst": "Thu thập, phân tích yêu cầu nghiệp vụ, viết tài liệu BRD/PRD, làm cầu nối giữa stakeholder và đội phát triển.",
    "IT Project Manager": "Lập kế hoạch, điều phối và giám sát tiến độ dự án phần mềm, quản lý rủi ro và nguồn lực.",
    "UX/UI Designer": "Thiết kế giao diện và trải nghiệm người dùng, làm prototype và quy chuẩn thiết kế.",
    "Site Reliability Engineer": "Đảm bảo độ tin cậy, khả năng mở rộng và giám sát hệ thống sản xuất, cân bằng giữa tốc độ và ổn định.",
    "System Administrator": "Quản trị hạ tầng server, mạng và hệ điều hành, xử lý sự cố và bảo trì hệ thống.",
    "AI / Machine Learning Engineer": "Xây dựng và triển khai mô hình học máy vào sản phẩm thực tế, xử lý dữ liệu đào tạo và đánh giá hiệu quả.",
    "NLP / LLM Engineer": "Phát triển ứng dụng xử lý ngôn ngữ tự nhiên và tích hợp mô hình ngôn ngữ lớn, prompt engineering và RAG.",
    "Data Scientist (Deep Learning)": "Nghiên cứu và xây dựng mô hình deep learning cho các bài toán phức tạp, chuyển nghiên cứu thành sản phẩm.",
    "Game Developer": "Phát triển game trên Unity/Unreal, xử lý đồ họa, vật lý và tối ưu hiệu năng.",
    "Security Penetration Tester": "Kiểm thử bảo mật xâm nhập, đánh giá lỗ hổng ứng dụng và hạ tầng, đề xuất giải pháp khắc phục.",
    "Blockchain Engineer": "Phát triển smart contract và ứng dụng phi tập trung, thiết kế giải pháp blockchain cho doanh nghiệp.",
    "Embedded / Firmware Engineer": "Phát triển firmware cho thiết bị nhúng, tối ưu tài nguyên và đảm bảo độ ổn định phần cứng.",
    "Big Data Engineer (Spark)": "Xây dựng hệ thống xử lý dữ liệu lớn với Spark/Kafka, tối ưu hiệu năng tính toán phân tán.",
}

REQUIREMENTS_TEMPLATE = (
    "- Kinh nghiệm {exp_text}\n"
    "- Kỹ năng bắt buộc: {required_skills}\n"
    "- Kỹ năng ưu tiên: {optional_skills}\n"
    "- Hiểu biết về quy trình phát triển phần mềm, sử dụng tốt Git\n"
    "- {lang_text}\n"
    "- Tư duy logic tốt, có trách nhiệm và cầu tiến"
)

BENEFITS_TEMPLATE = (
    "- Mức lương cạnh tranh theo năng lực, thưởng dự án hấp dẫn\n"
    "- Chế độ bảo hiểm đầy đủ, nghỉ phép theo quy định\n"
    "- Môi trường làm việc chuyên nghiệp, có mentor và lộ trình thăng tiến\n"
    "- Hoạt động team building, gym và chăm sóc sức khỏe\n"
    "- Cơ hội làm việc với công nghệ mới và dự án toàn cầu"
)

EXP_TEXT = {
    "ENTRY": "tối thiểu 0 đến 1 năm hoặc sinh viên năm cuối; ",
    "JUNIOR": "từ 1 đến 2 năm làm vị trí tương đương; ",
    "MID_SENIOR": "từ 3 năm trở lên ở vị trí tương đương; ",
    "LEAD": "từ 5 năm trở lên, đã từng dẫn dắt nhóm hoặc quản lý dự án; ",
}
LANG_TEXT = {
    "ENTRY": "Tiếng Anh đọc hiểu tài liệu kỹ thuật.",
    "JUNIOR": "Tiếng Anh giao tiếp cơ bản, đọc hiểu tài liệu tốt.",
    "MID_SENIOR": "Tiếng Anh giao tiếp khá, làm việc với khách hàng nước ngoài.",
    "LEAD": "Tiếng Anh giao tiếp và viết tốt, làm việc trực tiếp với khách nước ngoài.",
}

JOB_TYPES = ["FULL_TIME", "FULL_TIME", "FULL_TIME", "FULL_TIME", "CONTRACT", "PART_TIME"]
WORKPLACES = ["ONSITE", "ONSITE", "HYBRID", "HYBRID", "REMOTE", "ONSITE"]


def assign_titles_and_slots():
    """Phân bổ số dựa trên multiplier của từng blueprint, tổng đúng 200."""
    jobs = []
    for title, cfg in JOB_BLUEPRINTS.items():
        for i in range(cfg["mult"]):
            jobs.append((title, cfg, i))
    # đảm bảo tổng = 200
    assert len(jobs) == 200, len(jobs)
    return jobs


def build():
    rng = random.Random(42)
    jobs = assign_titles_and_slots()
    records = []
    used_emails = set()
    for n, (base_title, cfg, i) in enumerate(jobs, start=1):
        level = rng.choice(cfg["level_weights"])
        location = pick_location(rng)
        job_type = rng.choice(JOB_TYPES)
        workplace = rng.choice(WORKPLACES)
        salary_min, salary_max = make_salary(level, rng)
        negotiable = rng.random() < 0.35
        if cfg["pop"] == "common":
            company = rng.choice(COMPANIES_COMMON)
        elif cfg["pop"] == "average":
            company = rng.choice(COMPANIES_AVERAGE)
        else:
            company = rng.choice(COMPANIES_RARE)

        core_skills = (
            BACKEND_STACKS[i % len(BACKEND_STACKS)]
            if base_title == "Backend Developer"
            else CORE_SKILLS_BY_ROLE.get(base_title, [])
        )
        prefix = experience_title(level)
        title = f"{prefix}{display_role_title(base_title, core_skills)}"
        other_skills = optional_skill_pool(base_title, cfg["cat"], core_skills)
        rng.shuffle(other_skills)
        skill_count = min(len(core_skills) + len(other_skills), 3 + rng.randint(0, 3))
        optional_skills = other_skills[: skill_count - len(core_skills)]
        skill_specs = [
            *({"name": name, "is_required": True} for name in core_skills),
            *({"name": name, "is_required": False} for name in optional_skills),
        ]

        # phân bố status: chủ yếu ACTIVE, phủ đủ DRAFT/CLOSED/EXPIRED
        if n == 3:
            status = "DRAFT"
        elif n == 7:
            status = "CLOSED"
        elif n == 11:
            status = "EXPIRED"
        elif n == 13:
            status = "DRAFT"
        elif n == 17:
            status = "CLOSED"
        elif n == 19:
            status = "EXPIRED"
        else:
            status = "ACTIVE"

        # PART_TIME chỉ áp dụng cho QA/Tester, Data Analyst và UX/UI (vai trò phù hợp)
        if job_type == "PART_TIME" and base_title not in ("QA / Tester", "Data Analyst", "UX/UI Designer", "Frontend Developer"):
            job_type = "FULL_TIME"

        email = f"hr.{cfg['pop']}.{n:03d}@jobportal.local"

        record = {
            "title": title,
            "company_name": company,
            "category": cfg["cat"],
            "popularity": cfg["pop"],
            "description": ROLE_DESCRIPTIONS[base_title],
            "requirements": REQUIREMENTS_TEMPLATE.format(
                exp_text=EXP_TEXT[level],
                required_skills=", ".join(core_skills),
                optional_skills=", ".join(optional_skills) or "Không bắt buộc",
                lang_text=LANG_TEXT[level],
            ),
            "benefits": BENEFITS_TEMPLATE,
            "location": location,
            "workplace_type": workplace,
            "job_type": job_type,
            "experience_level": level,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_negotiable": negotiable,
            "status": status,
            "skills": skill_specs,
            "owner_email": email,
            "owner_username": f"hr_{cfg['pop']}_{n:03d}",
        }
        used_emails.add(email)
        records.append(record)

    data = {
        "meta": {
            "description": "200 JobPosts chuẩn hóa, phân loại theo mức độ phổ biến của vai trò: 120 phổ biến (60%), 60 trung bình (30%), 20 hiếm (10%).",
            "total": len(records),
            "skill_schema": {"name": "string", "is_required": "boolean"},
            "popularity": {
                "common": sum(1 for r in records if r["popularity"] == "common"),
                "average": sum(1 for r in records if r["popularity"] == "average"),
                "rare": sum(1 for r in records if r["popularity"] == "rare"),
            },
        },
        "jobs": records,
    }
    out = HERE / "jobs_200_curated.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", out, "with", len(records), "jobs")
    print("popularity:", data["meta"]["popularity"])
# Báo cáo độ bao phủ enum
    from collections import Counter
    for field in ["workplace_type", "job_type", "experience_level", "location", "status"]:
        counts = dict(Counter(r[field] for r in records))
        print(field, json.dumps(counts, ensure_ascii=True))


if __name__ == "__main__":
    build()
