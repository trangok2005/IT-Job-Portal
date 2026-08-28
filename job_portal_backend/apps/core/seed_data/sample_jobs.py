"""Dữ liệu seed cho JobPost, tách khỏi management commands.

Các helper parse/logic nằm ở command; module này chỉ chứa hằng số dữ liệu.
"""
from apps.jobs.models import JobPost

# Keep the original 20 rows, then fill every role family to 10 jobs.
INITIAL_GROUP_ROWS = {
    "Backend": [3, 4],
    "Frontend": [17, 33],
    "Full-stack": [0, 1],
    "QA": [21, 30],
    "Mobile": [11, 37],
    "Software/.NET": [44, 242],
    "Game": [51, 99],
    "AI": [59, 94],
    "Business": [23, 127],
    "DevOps/Data": [14, 18],
}

ROLE_GROUPS = {
    "Backend": {
        "Backend Developer", "Backend Engineer", "Backend Intern",
        "Java Developer", "Java Engineer", "Java Software Engineer",
        "PHP Developer", "Senior Java Developer",
    },
    "Frontend": {"Frontend Developer", "Web Developer", "UX/UI Designer"},
    "Full-stack": {
        "Full-stack Developer", "Fullstack Developer",
        "Java/Golang/Angular Developer", "Magento Developer",
    },
    "QA": {
        "QA Engineer", "Automation Tester", "Software Tester",
        "Senior QA Engineer", "Quality Control Engineer",
        "Software Quality Assurance Engineer", "Automation Test Lead",
        "Leader Tester Engineer", "Quality Assurance Manager",
    },
    "Mobile": {
        "Mobile Developer", "Flutter Developer", "iOS Developer",
        "Leader React Native",
    },
    "Software/.NET": {
        "Software Engineer", "Software Developer", ".NET Developer",
        "Senior .NET Developer", "Senior Software Engineer",
        "C#.NET Leader", "C/C++ Developer", "C++ Developer",
        "Senior C++ Developer", "C++/C# Developer",
    },
    "Game": {
        "Game Developer", "Unity Developer", "Playable Ads Developer",
        "Game Designer",
    },
    "AI": {
        "AI Engineer", "Machine Learning Engineer", "Data Scientist",
        "AI Analyst", "Quantitative Developer",
    },
    "Business": {
        "Business Analyst", "Product Manager", "IT Project Manager",
        "Project Manager", "Technical Project Manager",
    },
    "DevOps/Data": {
        "DevOps Engineer", "DevSecOps Engineer", "Data Engineer",
        "Data Engineer Intern", "Data Analyst", "Data Integration Engineer",
        "Cloud Engineer", "Site Reliability Engineer", "Database Engineer",
        "Database Developer", "Database Administrator",
    },
}

SKILL_ALIASES = {
    "ReactJS": "React",
    "React.js": "React",
    "NextJS": "Next.js",
    "NodeJS": "Node.js",
    "ExpressJS": "Express",
    "Golang": "Go",
    "Postgres": "PostgreSQL",
    "Spring": "Spring Boot",
    "Spring Framework": "Spring Boot",
    "REST": "REST API",
    "RESTful": "REST API",
    "RESTful API": "REST API",
    "RESTful APIs": "REST API",
    ".NET": "ASP.NET Core",
    ".NET Core": "ASP.NET Core",
    "ASP.NET": "ASP.NET Core",
    "ASP.NET MVC": "ASP.NET Core",
    "HTML": "HTML/CSS",
    "CSS": "HTML/CSS",
}

SALARY_BY_LEVEL = {
    JobPost.ExperienceLevel.ENTRY: (5_000_000, 15_000_000),
    JobPost.ExperienceLevel.JUNIOR: (12_000_000, 22_000_000),
    JobPost.ExperienceLevel.MID_SENIOR: (20_000_000, 50_000_000),
    JobPost.ExperienceLevel.LEAD: (40_000_000, 70_000_000),
}

GROUP_QUOTAS = {
    "Backend": 9,
    "Frontend": 6,
    "Full-stack": 5,
    "QA": 5,
    "Mobile": 5,
    "Software/.NET": 7,
    "Game": 4,
    "AI": 2,
    "Business": 3,
    "DevOps/Data": 4,
}

EXTRA_GROUP_ROLES = {
    "Software/.NET": {
        "Software Internship", "Software Development Intern", "Intern Developer",
        "Junior Developer", "Software Development Intern",
    },
    "DevOps/Data": {"Intern Security Engineer", "Security Engineer"},
}
