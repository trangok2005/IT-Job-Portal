from django.test import SimpleTestCase

from apps.core.background_tasks.registry import TASK_REGISTRY


class BackgroundTaskRegistryTests(SimpleTestCase):
    def test_registry_keeps_all_stable_task_names(self):
        self.assertEqual(
            set(TASK_REGISTRY),
            {
                "cleanup_expired_jd_imports",
                "cleanup_expired_resume_imports",
                "compute_application_match_score",
                "retry_incomplete_application_matches",
                "expire_jobs",
                "generate_candidate_embedding",
                "generate_job_embedding",
                "parse_jd_import",
                "parse_resume_import",
                "send_application_status_email",
            },
        )
        self.assertTrue(all(callable(task) for task in TASK_REGISTRY.values()))
