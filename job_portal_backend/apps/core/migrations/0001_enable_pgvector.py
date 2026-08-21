from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """Bật extension 'vector' trên PostgreSQL trước khi bất kỳ app nào
    (candidates, jobs) dùng VectorField/HnswIndex. App 'core' phải đứng
    đầu INSTALLED_APPS (hoặc ít nhất trước candidates/jobs) để migration
    này chạy trước.

    Yêu cầu: role DB đang dùng để migrate phải có quyền CREATE EXTENSION,
    hoặc DBA cần chạy tay:  CREATE EXTENSION IF NOT EXISTS vector;
    """

    initial = True
    dependencies = []
    operations = [
        VectorExtension(),
    ]
