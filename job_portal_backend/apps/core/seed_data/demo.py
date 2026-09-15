
ADMIN = {
    "username": "admin",
    "email": "admin@gmail.com",
    "password": "admin123",
}

EMPLOYER = {
    "username": "employer",
    "email": "employer@gmail.com",
    "password": "employer123",
}

CANDIDATE = {
    "username": "candidate",
    "email": "candidate@gmail.com",
    "password": "candidate123",
}

COMPANY = {
    "name": "TechCorp Vietnam",
    "defaults": {
        "tax_code": "0123456789",
        "description": "Công ty công nghệ chuyên phát triển sản phẩm phần mềm.",
        "website": "https://techcorp.example.com",
        "address": "Hà Nội, Việt Nam",
        "company_size": "50-100",
        "industry": "IT - Software",
    },
}

JOB = {
    "title": "Backend Developer (Python/Django)",
    "description": "Phát triển hệ thống job portal với Django REST Framework, PostgreSQL + pgvector.",
    "requirements": "3 năm kinh nghiệm Python/Django, PostgreSQL, Docker.",
    "benefits": "Lương thưởng hấp dẫn, bảo hiểm đầy đủ, môi trường trẻ trung.",
    "location": "Hà Nội",
    "salary_min": 15_000_000,
    "salary_max": 25_000_000,
    "skills": [
        {"name": "Python", "is_required": True},
        {"name": "Django", "is_required": True},
        {"name": "Django REST Framework", "is_required": True},
        {"name": "PostgreSQL", "is_required": False},
        {"name": "Docker", "is_required": False},
    ],
}

CANDIDATE_PROFILE = {
    "full_name": "Nguyễn Văn Ứng Viên",
    "phone": "0901234567",
    "headline": "Backend Developer 2 năm kinh nghiệm",
    "summary": "Yêu thích Python/Django.",
    "desired_position": "Backend Developer",
}
