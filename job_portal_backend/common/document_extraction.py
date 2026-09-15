import io
import zipfile
import xml.etree.ElementTree as ET


def extract_docx_text(file_data: bytes) -> str:
    """Trích xuất đoạn và bảng mà không chạy nội dung nhúng."""
    with zipfile.ZipFile(io.BytesIO(file_data)) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in document.findall(".//w:p", namespace):
        text = "".join(
            node.text or "" for node in paragraph.findall(".//w:t", namespace)
        ).strip()
        if text:
            paragraphs.append(text)
    if not paragraphs:
        raise ValueError("File DOCX không có nội dung văn bản.")
    return "\n".join(paragraphs)
