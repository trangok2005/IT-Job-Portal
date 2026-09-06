from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from apps.candidates.models import DegreeLevel
from apps.core.matching import (
    MatchingWeights,
    aggregate_match_score,
    education_score,
    experience_score,
    skill_match_score,
    total_experience_years,
)
from apps.skills.serializers import MatchingWeightConfigSerializer
from apps.ai_analysis.tasks import _cosine_similarity


class MatchingRuleTests(SimpleTestCase):
    def setUp(self):
        self.weights = MatchingWeights(
            semantic=Decimal("0.35"),
            skill=Decimal("0.40"),
            experience=Decimal("0.20"),
            education=Decimal("0.05"),
            required_skill_multiplier=Decimal("2"),
        )

    def test_full_weighted_example(self):
        score, normalized = aggregate_match_score(
            {"semantic": 0.8, "skill": 0.75, "experience": 1, "education": 0.5},
            self.weights,
        )
        self.assertEqual(score, Decimal("80.50"))
        self.assertEqual(sum(normalized.values()), Decimal("1"))

    def test_non_applicable_education_is_renormalized(self):
        score, normalized = aggregate_match_score(
            {"semantic": 0.8, "skill": 0.75, "experience": 1, "education": None},
            self.weights,
        )
        self.assertEqual(score, Decimal("82.11"))
        self.assertEqual(normalized["education"], Decimal("0"))
        self.assertEqual(sum(normalized.values()), Decimal("1"))

    def test_missing_required_education_stays_applicable(self):
        score, _ = aggregate_match_score(
            {"semantic": 0.8, "skill": 0.75, "experience": 1, "education": 0},
            self.weights,
        )
        self.assertEqual(score, Decimal("78.00"))

    def test_zero_applicable_weight_returns_insufficient(self):
        score, normalized = aggregate_match_score(
            {"semantic": None, "skill": 0.5, "experience": None, "education": None},
            MatchingWeights(
                semantic=Decimal("1"),
                skill=Decimal("0"),
                experience=Decimal("0"),
                education=Decimal("0"),
            ),
        )
        self.assertIsNone(score)
        self.assertEqual(sum(normalized.values()), Decimal("0"))

    def test_non_finite_component_or_weight_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_match_score(
                {"semantic": float("nan")},
                self.weights,
            )
        with self.assertRaises(ValueError):
            aggregate_match_score(
                {"semantic": 1},
                MatchingWeights(
                    semantic=Decimal("Infinity"),
                    skill=Decimal("0"),
                    experience=Decimal("0"),
                    education=Decimal("0"),
                ),
            )

    def test_required_and_preferred_skill_formula_and_deduplication(self):
        job_skills = [
            {"id": "r1", "name": "R1", "is_required": True},
            {"id": "r2", "name": "R2", "is_required": True},
            {"id": "p1", "name": "P1", "is_required": False},
            {"id": "p2", "name": "P2", "is_required": False},
            {"id": "r1", "name": "R1 alias", "is_required": False},
        ]
        score, details = skill_match_score({"r1", "p1", "p2"}, job_skills, 2)
        self.assertAlmostEqual(score, 4 / 6)
        self.assertEqual(details["required_count"], 2)
        self.assertEqual(details["preferred_count"], 2)

    def test_no_job_skills_is_not_applicable(self):
        score, _ = skill_match_score(set(), [], 2)
        self.assertIsNone(score)

    def test_experience_intervals_are_merged_as_half_open_ranges(self):
        intervals = [
            (date(2020, 1, 1), date(2020, 1, 11), False),
            (date(2020, 1, 5), date(2020, 1, 8), False),
            (date(2020, 1, 10), date(2020, 1, 20), False),
            (date(2020, 2, 1), date(2020, 2, 6), False),
        ]
        self.assertAlmostEqual(total_experience_years(intervals) * 365.25, 24)
        self.assertEqual(experience_score(0, "ENTRY"), 1)
        self.assertEqual(experience_score(0, "JUNIOR"), 0)

    def test_education_soft_scoring_and_applicability(self):
        self.assertIsNone(education_score(None, None))
        self.assertIsNone(education_score(DegreeLevel.NONE, DegreeLevel.NONE))
        self.assertEqual(education_score(None, DegreeLevel.BACHELOR), 0)
        self.assertEqual(education_score(DegreeLevel.ASSOCIATE, DegreeLevel.BACHELOR), 0.75)
        self.assertEqual(education_score(DegreeLevel.PHD, DegreeLevel.BACHELOR), 1)

    def test_weight_config_rejects_invalid_and_non_finite_values(self):
        base = {
            "name": "Invalid",
            "weight_semantic_similarity": "0.35",
            "weight_skill_overlap": "0.40",
            "weight_experience_match": "0.20",
            "weight_education_match": "0.05",
            "required_skill_multiplier": "2",
        }
        self.assertTrue(MatchingWeightConfigSerializer(data=base).is_valid())

        for field, value in (
            ("weight_semantic_similarity", "-0.1"),
            ("weight_semantic_similarity", "NaN"),
            ("weight_skill_overlap", "Infinity"),
            ("required_skill_multiplier", "0.99"),
        ):
            invalid = {**base, field: value}
            self.assertFalse(
                MatchingWeightConfigSerializer(data=invalid).is_valid(),
                (field, value),
            )

        wrong_total = {**base, "weight_semantic_similarity": "0.34"}
        self.assertFalse(MatchingWeightConfigSerializer(data=wrong_total).is_valid())

    def test_cosine_rejects_invalid_vectors_instead_of_returning_zero(self):
        valid = [0.1] * 768
        with self.assertRaises(ValueError):
            _cosine_similarity(valid[:-1], valid)
        with self.assertRaises(ValueError):
            _cosine_similarity([0.0] * 768, valid)
        with self.assertRaises(ValueError):
            _cosine_similarity([float("nan"), *valid[1:]], valid)
