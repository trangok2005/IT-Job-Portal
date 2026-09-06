"""
seed_sample_candidates.py

10 CV mẫu, đúng schema trong models.py (User -> CandidateProfile ->
Education/Experience -> Skill/CandidateSkill), phân bố theo các nhóm role
phổ biến (Backend, Frontend, Full-stack, QA, Mobile, Software, Game,
AI, Business Analyst, DevOps/Data) và 2 thành phố chiếm đa số (Hà Nội, TP.HCM).

Cài đặt: copy file này vào
    <app_có_CandidateProfile>/management/commands/seed_sample_candidates.py
(cần có __init__.py trong cả 2 thư mục management/ và management/commands/)

Chạy:
    python manage.py seed_sample_candidates

Dùng get_or_create() ở mọi bước nên chạy lại nhiều lần vẫn an toàn
(idempotent), không tạo trùng.

Lưu ý: KHÔNG tự set embedding ở đây — sau khi seed xong, chạy tiếp lệnh
rebuild_embeddings (bạn đã có sẵn) để đẩy các CandidateProfile mới vào
QStash sinh embedding.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.candidates.models import CandidateProfile, DegreeLevel, Education, Experience
from apps.core.matching import recognized_degree_level
from apps.core.seed_data.candidates import CANDIDATES, CATEGORY_MAP
from apps.skills.models import Skill, CandidateSkill

User = get_user_model()


class Command(BaseCommand):
    help = "Seed 10 CV mẫu (User + CandidateProfile + Education + Experience + Skill) để test import/matching."

    def handle(self, *args, **options):
        skill_cache = {}
        for skill_names in CATEGORY_MAP.values():
            for name in skill_names:
                skill = Skill.objects.filter(
                    name__iexact=name,
                    status__in=[Skill.Status.APPROVED, Skill.Status.PENDING],
                ).first()
                if skill is not None:
                    skill_cache[name] = skill

        created_count = 0
        with transaction.atomic():
            for data in CANDIDATES:
                user, user_created = User.objects.get_or_create(
                    email=data["email"],
                    defaults={
                        "username": data["username"],
                        "role": User.Role.CANDIDATE,
                    },
                )
                if user_created:
                    user.set_password("ChangeMe123!")
                    user.save()

                profile, _ = CandidateProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "full_name": data["full_name"],
                        "headline": data["headline"],
                        "summary": data["summary"],
                        "desired_position": data["desired_position"],
                        "address": data["address"],
                        "is_public": True,
                    },
                )

                edu = data["education"]
                degree_rank = recognized_degree_level(edu["degree"])
                degree_level = {
                    1: DegreeLevel.ASSOCIATE,
                    2: DegreeLevel.BACHELOR,
                    3: DegreeLevel.MASTER,
                    4: DegreeLevel.PHD,
                }.get(degree_rank)
                Education.objects.get_or_create(
                    candidate=profile, school_name=edu["school_name"], major=edu["major"],
                    defaults={"degree": edu["degree"], "degree_level": degree_level,
                              "is_completed": degree_level is not None,
                              "is_verified": degree_level is not None,
                              "start_date": edu["start_date"], "end_date": edu["end_date"]},
                )

                for exp in data["experiences"]:
                    Experience.objects.get_or_create(
                        candidate=profile, company_name=exp["company_name"], position=exp["position"],
                        defaults={"start_date": exp["start_date"], "end_date": exp["end_date"],
                                  "is_current": exp["is_current"], "description": exp["description"]},
                    )

                for skill_name, *_ in data["skills"]:
                    skill = skill_cache.get(skill_name)
                    if skill is None:
                        continue
                    CandidateSkill.objects.get_or_create(
                        candidate=profile, skill=skill,
                    )

                created_count += 1
                self.stdout.write(f"  OK: {data['full_name']} ({data['desired_position']})")

        self.stdout.write(self.style.SUCCESS(f"Đã seed xong {created_count} candidate CV mẫu."))
        self.stdout.write("Chạy tiếp: python manage.py rebuild_embeddings  để đưa các profile mới vào hàng đợi tính embedding.")
