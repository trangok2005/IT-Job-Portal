from django.urls import path

from apps.candidates.views import (
    CandidateEducationCreateView,
    CandidateEducationDetailView,
    CandidateExperienceCreateView,
    CandidateExperienceDetailView,
    CandidateMeView,
    CandidateResumeDetailView,
    CandidateResumeImportDetailView,
    CandidateResumeImportView,
    CandidateResumeView,
    CandidateSkillCreateView,
    CandidateSkillDetailView,
    SetPrimaryResumeView,
)

urlpatterns = [
    path("me/", CandidateMeView.as_view(), name="candidate-me"),
    path("me/educations/", CandidateEducationCreateView.as_view(), name="candidate-education-create"),
    path("me/educations/<uuid:pk>/", CandidateEducationDetailView.as_view(), name="candidate-education-detail"),
    path("me/experiences/", CandidateExperienceCreateView.as_view(), name="candidate-experience-create"),
    path("me/experiences/<uuid:pk>/", CandidateExperienceDetailView.as_view(), name="candidate-experience-detail"),
    path("me/skills/", CandidateSkillCreateView.as_view(), name="candidate-skill-create"),
    path("me/skills/<uuid:pk>/", CandidateSkillDetailView.as_view(), name="candidate-skill-detail"),
    path("me/resumes/", CandidateResumeView.as_view(), name="candidate-resume-list-create"),
    path("me/resumes/<uuid:pk>/", CandidateResumeDetailView.as_view(), name="candidate-resume-detail"),
    path("me/resumes/<uuid:pk>/set-primary/", SetPrimaryResumeView.as_view(), name="candidate-resume-set-primary"),
    path("me/resume-imports/", CandidateResumeImportView.as_view(), name="candidate-resume-import-create"),
    path("me/resume-imports/<uuid:pk>/", CandidateResumeImportDetailView.as_view(), name="candidate-resume-import-detail"),
]