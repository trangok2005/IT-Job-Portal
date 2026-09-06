"""Module duy nhất trong dự án được gọi mô hình embedding của Gemini."""
import math
from numbers import Real

from django.conf import settings


EMBEDDING_MODEL = settings.GEMINI_EMBEDDING_MODEL
EMBEDDING_DIMENSIONS = 768
EMBEDDING_CONTENT_VERSION = "matching-text-v1"


class TaskType:
    """Gemini task_type phân biệt vai trò văn bản, không phân biệt trường hợp sử dụng.

    UC-01/UC-02 index nội dung tĩnh (document); UC-03 nhúng câu truy vấn
    tức thời (query). Vector hai loại này không trộn lẫn được.
    """

    DOCUMENT = "RETRIEVAL_DOCUMENT"
    QUERY = "RETRIEVAL_QUERY"

    @classmethod
    def choices(cls):
        return (cls.DOCUMENT, cls.QUERY)


_client = None


class EmbeddingError(Exception):
    """Loại lỗi nghiệp vụ ổn định cho API, timeout, quota và vector không hợp lệ."""


def _get_client():
    """Khởi tạo SDK client khi cần để nhánh phi ngữ nghĩa không cần API key."""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise EmbeddingError("GEMINI_API_KEY chưa được cấu hình.")
        from google import genai
        from google.genai import types

        _client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=settings.EMBEDDING_TIMEOUT_MS),
        )
    return _client


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
        client = _get_client()
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
        raise EmbeddingError("Embedding chứa giá trị không hợp lệ.")
    if not any(value != 0 for value in vector):
        raise EmbeddingError("Embedding không được là zero vector.")
    return vector


def embed_document(text: str) -> list[float]:
    """UC-01/UC-02: tạo embedding cho nội dung được index sẵn."""
    return generate_embedding(text, task_type=TaskType.DOCUMENT)


def embed_query(text: str) -> list[float]:
    """UC-03: tạo embedding cho câu truy vấn tìm kiếm tức thời."""
    return generate_embedding(text, task_type=TaskType.QUERY)
