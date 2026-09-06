import json

from django.conf import settings
from django.test import SimpleTestCase


class CuratedJobSeedDataTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = (
            settings.BASE_DIR
            / "apps"
            / "core"
            / "seed_data"
            / "jobs_200_curated.json"
        )
        cls.jobs = json.loads(path.read_text(encoding="utf-8"))["jobs"]

    def test_every_skill_declares_is_required(self):
        self.assertEqual(len(self.jobs), 200)
        for job in self.jobs:
            self.assertTrue(job["skills"], job["title"])
            self.assertTrue(
                any(item["is_required"] for item in job["skills"]),
                job["title"],
            )
            for item in job["skills"]:
                self.assertEqual(set(item), {"name", "is_required"})
                self.assertIsInstance(item["is_required"], bool)

    def test_java_jobs_do_not_contain_competing_backend_stacks(self):
        competing = {"Python", "Django", "FastAPI", "PHP", "Go", "Node.js"}
        java_jobs = [job for job in self.jobs if "Java Developer" in job["title"]]

        self.assertTrue(java_jobs)
        for job in java_jobs:
            names = {item["name"] for item in job["skills"]}
            self.assertIn("Java", names)
            self.assertIn("Spring Boot", names)
            self.assertFalse(names & competing, job["title"])

    def test_python_backend_jobs_require_python_and_matching_framework(self):
        python_jobs = [job for job in self.jobs if "Python/" in job["title"]]

        self.assertTrue(python_jobs)
        for job in python_jobs:
            required = {
                item["name"]
                for item in job["skills"]
                if item["is_required"]
            }
            self.assertIn("Python", required)
            self.assertTrue(required & {"Django", "FastAPI"})
            self.assertFalse(required & {"Java", "Spring Boot"})
