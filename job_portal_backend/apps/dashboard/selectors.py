"""Aggregated read queries for role-specific dashboards."""
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
    """Return candidate counts and at most three eligible recommendations."""
    profile = CandidateProfile.objects.annotate(
        primary_resume_count=Count(
            "resumes",
            filter=Q(resumes__is_primary=True) & ~Q(resumes__file=""),
            distinct=True,
        )
    ).get(user=user)
    counts = profile.applications.filter(is_active=True).aggregate(
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
    """Return company state and aggregate job/application counts for its owner."""
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
    jobs = company.job_posts.filter(is_active=True)
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
        is_active=True,
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
    """Return system-wide moderation and activity counters in aggregate queries."""
    now = timezone.now()
    user_counts = User.objects.aggregate(
        users_total=Count("id"),
        users_active=Count("id", filter=Q(is_active=True)),
    )
    return {
        **user_counts,
        "pending_companies": Company.objects.filter(
            status=Company.Status.PENDING, is_active=True
        ).count(),
        "active_jobs": JobPost.objects.filter(
            status=JobPost.Status.ACTIVE,
            company__status=Company.Status.APPROVED,
            is_active=True,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).count(),
        "applications": JobApplication.objects.filter(is_active=True).count(),
        "pending_skills": Skill.objects.filter(
            status=Skill.Status.PENDING, is_active=True
        ).count(),
    }
