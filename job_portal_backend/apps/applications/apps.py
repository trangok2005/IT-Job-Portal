from django.apps import AppConfig


class Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.applications"
    label = "applications"
    verbose_name = "applications"
