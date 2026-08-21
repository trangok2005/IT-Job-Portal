from django.apps import AppConfig


class Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.skills"
    label = "skills"
    verbose_name = "skills"
