"""Các truy vấn chỉ đọc kết quả phù hợp đã lưu của hồ sơ ứng tuyển."""
from apps.ai_analysis.models import ApplicationMatchResult


def get_application_match_result(application):
    """Trả kết quả đã tính hoặc None khi task vẫn đang xử lý."""
    return ApplicationMatchResult.objects.select_related(
        "application__candidate",
        "application__job",
    ).filter(application=application).first()
