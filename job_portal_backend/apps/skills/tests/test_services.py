from unittest.mock import patch

from django.test import TestCase

from apps.skills.models import Skill, SkillAlias
from apps.skills.services import resolve_extracted_skill


class ExtractedSkillResolutionTests(TestCase):
    def setUp(self):
        self.react = Skill.objects.create(name="React", slug="react")
        SkillAlias.objects.create(
            skill=self.react,
            alias_text="ReactJS",
            normalized_text="reactjs",
        )

    def test_exact_alias_resolves_canonical_skill(self):
        result = resolve_extracted_skill("REACTJS")

        self.assertEqual(result, self.react)

    def test_fuzzy_spacing_variant_resolves_alias(self):
        result = resolve_extracted_skill("React Js")

        self.assertEqual(result, self.react)
        self.assertFalse(Skill.objects.filter(name="React Js").exists())

    def test_different_skill_name_does_not_false_match(self):
        javascript = Skill.objects.create(name="JavaScript", slug="javascript")

        result = resolve_extracted_skill("Java")

        self.assertNotEqual(result, javascript)
        self.assertEqual(result.name, "Java")
        self.assertEqual(result.status, Skill.Status.PENDING)

    def test_short_skill_requires_exact_match(self):
        Skill.objects.create(name="C++", slug="c-plus-plus")

        result = resolve_extracted_skill("C")

        self.assertEqual(result.name, "C")
        self.assertEqual(result.status, Skill.Status.PENDING)

    def test_fuzzy_score_at_90_resolves(self):
        skill = Skill.objects.create(name="abcdefghij", slug="abcdefghij")

        result = resolve_extracted_skill("abcdefghiX")

        self.assertEqual(result, skill)

    def test_fuzzy_score_below_90_creates_pending(self):
        skill = Skill.objects.create(name="abcdefghi", slug="abcdefghi")

        result = resolve_extracted_skill("abcdefghX")

        self.assertNotEqual(result, skill)
        self.assertEqual(result.status, Skill.Status.PENDING)

    @patch("apps.skills.services.fuzz.ratio", return_value=100)
    def test_three_char_input_skips_fuzzy_matching(self, scorer):
        Skill.objects.create(name="three-char-target", slug="three-char-target")

        result = resolve_extracted_skill("abc")

        self.assertEqual(result.name, "abc")
        self.assertFalse(scorer.called)

    @patch("apps.skills.services.fuzz.ratio")
    def test_four_char_input_allows_fuzzy_matching(self, scorer):
        target = Skill.objects.create(name="four-char-target", slug="four-char-target")
        scorer.side_effect = lambda _query, choice: 90 if choice == "four-char-target" else 0

        result = resolve_extracted_skill("abcd")

        self.assertEqual(result, target)

    @patch("apps.skills.services.fuzz.ratio")
    def test_score_gap_below_three_is_ambiguous(self, scorer):
        Skill.objects.create(name="first-target", slug="first-target")
        Skill.objects.create(name="second-target", slug="second-target")
        scores = {"first-target": 95, "second-target": 92.01}
        scorer.side_effect = lambda _query, choice: scores.get(choice, 0)

        result = resolve_extracted_skill("ambiguous input")

        self.assertEqual(result.name, "ambiguous input")
        self.assertEqual(result.status, Skill.Status.PENDING)

    @patch("apps.skills.services.fuzz.ratio")
    def test_score_gap_of_exactly_three_resolves_best(self, scorer):
        best = Skill.objects.create(name="best-target", slug="best-target")
        Skill.objects.create(name="runner-up", slug="runner-up")
        scores = {"best-target": 95, "runner-up": 92}
        scorer.side_effect = lambda _query, choice: scores.get(choice, 0)

        result = resolve_extracted_skill("clear input")

        self.assertEqual(result, best)

    @patch("apps.skills.services.fuzz.ratio")
    def test_duplicate_aliases_for_same_skill_do_not_hide_ambiguity(self, scorer):
        first = Skill.objects.create(name="first", slug="first")
        second = Skill.objects.create(name="second", slug="second")
        SkillAlias.objects.create(
            skill=first, alias_text="first alias one", normalized_text="first alias one"
        )
        SkillAlias.objects.create(
            skill=first, alias_text="first alias two", normalized_text="first alias two"
        )
        scores = {
            "first alias one": 98,
            "first alias two": 97,
            "second": 96,
        }
        scorer.side_effect = lambda _query, choice: scores.get(choice, 0)

        result = resolve_extracted_skill("duplicate aliases")

        self.assertNotEqual(result, first)
        self.assertNotEqual(result, second)
        self.assertEqual(result.status, Skill.Status.PENDING)

    def test_active_pending_skill_is_fuzzy_eligible(self):
        pending = Skill.objects.create(
            name="pendingabc", slug="pendingabc", status=Skill.Status.PENDING
        )

        result = resolve_extracted_skill("pendingabX")

        self.assertEqual(result, pending)

    def test_exact_active_pending_skill_is_reused(self):
        pending = Skill.objects.create(
            name="Pending Exact", slug="pending-exact", status=Skill.Status.PENDING
        )

        result = resolve_extracted_skill("pending exact")

        self.assertEqual(result, pending)
        self.assertEqual(
            Skill.objects.filter(name__iexact="pending exact").count(), 1
        )

    def test_inactive_and_rejected_skills_are_not_fuzzy_eligible(self):
        inactive = Skill.objects.create(
            name="inactiveab", slug="inactiveab", is_active=False
        )
        rejected = Skill.objects.create(
            name="rejectedab",
            slug="rejectedab",
            status=Skill.Status.REJECTED,
        )

        inactive_result = resolve_extracted_skill("inactiveaX")
        rejected_result = resolve_extracted_skill("rejectedaX")

        self.assertNotEqual(inactive_result, inactive)
        self.assertNotEqual(rejected_result, rejected)
        self.assertEqual(inactive_result.status, Skill.Status.PENDING)
        self.assertEqual(rejected_result.status, Skill.Status.PENDING)

    def test_c_family_names_remain_distinct(self):
        c = Skill.objects.create(name="C", slug="c")
        cpp = Skill.objects.create(name="C++", slug="c-plus-plus")
        csharp = Skill.objects.create(name="C#", slug="c-sharp")

        self.assertEqual(resolve_extracted_skill("C"), c)
        self.assertEqual(resolve_extracted_skill("C++"), cpp)
        self.assertEqual(resolve_extracted_skill("C#"), csharp)
