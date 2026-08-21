"""Read-only queries cho kết quả AI analysis."""
from apps.ai_analysis.models import AIAnalysis


def get_application_analysis(application):
    """Trả kết quả đã tính hoặc None trong lúc task vẫn đang xử lý."""
    return AIAnalysis.objects.select_related(
        "application__candidate",
        "application__job",
        "weight_config",
    ).filter(application=application).first()
