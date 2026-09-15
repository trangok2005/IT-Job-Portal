from apps.ai_analysis.models import ApplicationMatchResult


def get_application_match_result(application):
    return ApplicationMatchResult.objects.select_related(
        "application__candidate",
        "application__job",
    ).filter(application=application).first()
