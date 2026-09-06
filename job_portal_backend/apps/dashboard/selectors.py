"""Các truy vấn tổng hợp chỉ đọc cho dashboard theo role."""
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import JobApplication
from apps.candidates.models import CandidateProfile
from apps.companies.models import Company
from apps.dashboard.services import calculate_profile_completion
from apps.jobs.models import JobPost
from apps.jobs.selectors import get_recommended_jobs
from apps.skills.models import Skill


def get_candidate_dashboard(user):
    """Trả số liệu của candidate và tối đa ba đề xuất đủ điều kiện."""
    profile = CandidateProfile.objects.annotate(
        primary_resume_count=Count(
            "resumes",
            filter=Q(resumes__is_primary=True) & ~Q(resumes__file=""),
            distinct=True,
        )
    ).get(user=user)
    counts = profile.applications.aggregate(
        application_count=Count("id"),
        **{
            f"status_{status.lower()}": Count("id", filter=Q(status=status))
            for status in JobApplication.Status.values
        },
    )
    return {
        "profile_completion": calculate_profile_completion(
            profile, bool(profile.primary_resume_count)
        ),
        "application_count": counts["application_count"],
        "application_status_counts": {
            status: counts[f"status_{status.lower()}"]
            for status in JobApplication.Status.values
        },
        "recommended_jobs": list(get_recommended_jobs(profile)[:3]),
        "profile": profile,
    }


def get_employer_dashboard(user):
    """Trả trạng thái công ty và số tin, hồ sơ tổng hợp cho chủ sở hữu."""
    company = Company.objects.filter(owner=user).first()
    if company is None:
        return {
            "company_status": None,
            "jobs_total": 0,
            "jobs_active": 0,
            "jobs_draft": 0,
            "new_applications": 0,
            "total_applications": 0,
        }
    now = timezone.now()
    jobs = company.job_posts.all()
    job_counts = jobs.aggregate(
        jobs_total=Count("id"),
        jobs_active=Count(
            "id",
            filter=Q(status=JobPost.Status.ACTIVE)
            & (Q(expires_at__isnull=True) | Q(expires_at__gt=now)),
        ),
        jobs_draft=Count("id", filter=Q(status=JobPost.Status.DRAFT)),
    )
    application_counts = JobApplication.objects.filter(
        job__company=company,
    ).aggregate(
        new_applications=Count("id", filter=Q(status=JobApplication.Status.APPLIED)),
        total_applications=Count("id"),
    )
    return {
        "company_status": company.status,
        **job_counts,
        **application_counts,
    }


def get_admin_dashboard():
    """Trả số liệu kiểm duyệt và hoạt động toàn hệ thống bằng truy vấn tổng hợp."""
    now = timezone.now()
    user_counts = User.objects.aggregate(
        users_total=Count("id"),
        users_active=Count("id", filter=Q(is_active=True)),
    )
    return {
        **user_counts,
        "pending_companies": Company.objects.filter(
            status=Company.Status.PENDING
        ).count(),
        "active_jobs": JobPost.objects.filter(
            status=JobPost.Status.ACTIVE,
            company__status=Company.Status.APPROVED,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).count(),
        "applications": JobApplication.objects.count(),
        "pending_skills": Skill.objects.filter(
            status=Skill.Status.PENDING, is_active=True
        ).count(),
    }
