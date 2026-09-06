#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    # Console Windows mặc định cp1252 - không in được tiếng Việt có dấu
    # trong thông báo của các lệnh quản trị (seed, shell...).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Missing mocks must fail fast instead of consuming a real Gemini quota.
        os.environ["GEMINI_API_KEY"] = ""
        if not any(arg.startswith("--settings") for arg in sys.argv[2:]):
            os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
