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
        result = resolve_extracted_skill("REACTJS", Skill.Source.CV_PARSING)

        self.assertEqual(result, self.react)

    def test_fuzzy_spacing_variant_resolves_alias(self):
        result = resolve_extracted_skill("React Js", Skill.Source.JD_PARSING)

        self.assertEqual(result, self.react)
        self.assertFalse(Skill.objects.filter(name="React Js").exists())

    def test_different_skill_name_does_not_false_match(self):
        javascript = Skill.objects.create(name="JavaScript", slug="javascript")

        result = resolve_extracted_skill("Java", Skill.Source.CV_PARSING)

        self.assertNotEqual(result, javascript)
        self.assertEqual(result.name, "Java")
        self.assertEqual(result.status, Skill.Status.PENDING)

    def test_short_skill_requires_exact_match(self):
        Skill.objects.create(name="C++", slug="c-plus-plus")

        result = resolve_extracted_skill("C", Skill.Source.JD_PARSING)

        self.assertEqual(result.name, "C")
        self.assertEqual(result.status, Skill.Status.PENDING)
        self.assertEqual(result.source, Skill.Source.JD_PARSING)
