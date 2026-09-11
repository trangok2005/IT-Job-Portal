"""Module duy nhất trong dự án được gọi mô hình embedding của Gemini."""
import math
from numbers import Real

from django.conf import settings

from integrations.gemini.client import get_gemini_client


EMBEDDING_MODEL = settings.GEMINI_EMBEDDING_MODEL
EMBEDDING_DIMENSIONS = 768
EMBEDDING_CONTENT_VERSION = "matching-text-v1"


class TaskType:
    DOCUMENT = "RETRIEVAL_DOCUMENT"
    QUERY = "RETRIEVAL_QUERY"

    @classmethod
    def choices(cls):
        return (cls.DOCUMENT, cls.QUERY)


class EmbeddingError(Exception):
    """Loại lỗi nghiệp vụ cho API, timeout, quota và vector không hợp lệ."""


def current_embedding_signature(task_type: str) -> str:
    return (
        f"{EMBEDDING_MODEL}:{EMBEDDING_DIMENSIONS}:"
        f"{task_type}:{EMBEDDING_CONTENT_VERSION}"
    )


def current_candidate_embedding_signature() -> str:
    return current_embedding_signature(TaskType.DOCUMENT)


def current_job_embedding_signature() -> str:
    return current_embedding_signature(TaskType.DOCUMENT)


def generate_embedding(text: str, *, task_type: str = TaskType.DOCUMENT) -> list[float]:
    """Tạo một vector đã kiểm tra từ văn bản đã chuẩn hóa."""
    if task_type not in TaskType.choices():
        raise EmbeddingError(f"task_type không hợp lệ: {task_type}")
    if not text or not text.strip():
        raise EmbeddingError("Không thể tạo embedding từ text rỗng.")
    from google.genai import types

    try:
        client = get_gemini_client()
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        if not response.embeddings:
            raise ValueError("Gemini không trả về embedding.")
        vector = list(response.embeddings[0].values)
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError(f"Gemini embedding API lỗi: {exc}") from exc

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            f"Embedding trả về {len(vector)} chiều, "
            f"kỳ vọng {EMBEDDING_DIMENSIONS} chiều."
        )
    if any(not isinstance(value, Real) or not math.isfinite(value) for value in vector):
        raise EmbeddingError("Embedding chứa giá trị không hợp lệ")
    if not any(value != 0 for value in vector):
        raise EmbeddingError("Embedding không được là zero vector")
    return vector


def embed_document(text: str) -> list[float]:
    """tạo embedding cho nội dung cv/jd sẵn"""
    return generate_embedding(text, task_type=TaskType.DOCUMENT)


def embed_query(text: str) -> list[float]:
    """tạo embedding cho câu truy vấn tìm kiếm tức thời"""
    return generate_embedding(text, task_type=TaskType.QUERY)
