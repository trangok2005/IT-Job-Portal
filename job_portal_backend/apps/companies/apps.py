from django.apps import AppConfig


class Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.companies"
    label = "companies"
    verbose_name = "companies"
