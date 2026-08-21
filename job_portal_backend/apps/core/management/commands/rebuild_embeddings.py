"""Queue regeneration after an embedding model or text-pipeline change."""
from django.core.management.base import BaseCommand
from django.db.models import F, Q
from django_q.tasks import async_task

from apps.candidates.models import CandidateProfile
from integrations.gemini.embeddings import (
    current_candidate_embedding_signature,
    current_job_embedding_signature,
)
from apps.jobs.models import JobPost


class Command(BaseCommand):
    help = "Queue stale Candidate and published Job embeddings for regeneration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Queue every Candidate and non-draft Job after a dev text-builder change.",
        )

    def handle(self, *args, **options):
        candidate_signature = current_candidate_embedding_signature()
        job_signature = current_job_embedding_signature()
        stale_profiles = CandidateProfile.objects.all()
        stale_jobs = JobPost.objects.exclude(status=JobPost.Status.DRAFT)
        if not options["force"]:
            stale_profiles = stale_profiles.filter(
                Q(embedding__isnull=True)
                | ~Q(embedding_version=F("profile_version"))
                | ~Q(embedding_signature=candidate_signature)
            )
            stale_jobs = stale_jobs.filter(
                Q(embedding__isnull=True)
                | ~Q(embedding_version=F("content_version"))
                | ~Q(embedding_signature=job_signature)
            )

        profile_count = 0
        for profile in stale_profiles.iterator():
            async_task(
                "apps.candidates.tasks.generate_candidate_embedding",
                str(profile.pk),
                profile.profile_version,
            )
            profile_count += 1

        job_count = 0
        for job in stale_jobs.iterator():
            async_task(
                "apps.jobs.tasks.generate_job_embedding",
                str(job.pk),
                job.content_version,
                job.status != JobPost.Status.ACTIVE,
            )
            job_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Queued {profile_count} candidate and {job_count} job embeddings."
            )
        )
