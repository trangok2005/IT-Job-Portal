"""Đưa tác vụ tái tạo vào queue sau khi đổi embedding model hoặc text pipeline."""
from django.core.management.base import BaseCommand
from django.db.models import F, Q

from apps.candidates.models import CandidateProfile
from integrations.qstash.publisher import publish_task
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
        parser.add_argument(
            "--stagger-seconds",
            type=int,
            default=0,
            help="Delay consecutive QStash messages to avoid bursting provider quotas.",
        )

    def handle(self, *args, **options):
        stagger_seconds = options["stagger_seconds"]
        if stagger_seconds < 0:
            raise ValueError("--stagger-seconds must be zero or greater.")
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
            publish_task(
                "generate_candidate_embedding",
                {
                    "profile_id": str(profile.pk),
                    "profile_version": profile.profile_version,
                },
                delay=profile_count * stagger_seconds or None,
            )
            profile_count += 1

        job_count = 0
        for job in stale_jobs.iterator():
            queue_position = profile_count + job_count
            publish_task(
                "generate_job_embedding",
                {
                    "job_id": str(job.pk),
                    "content_version": job.content_version,
                    "allow_closed": job.status != JobPost.Status.ACTIVE,
                },
                delay=queue_position * stagger_seconds or None,
            )
            job_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Queued {profile_count} candidate and {job_count} job embeddings."
            )
        )
