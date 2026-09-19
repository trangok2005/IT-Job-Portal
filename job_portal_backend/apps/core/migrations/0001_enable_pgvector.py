from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """Phải chạy trước migration dùng VectorField; DB role cần CREATE EXTENSION."""

    initial = True
    dependencies = []
    operations = [
        VectorExtension(),
    ]
