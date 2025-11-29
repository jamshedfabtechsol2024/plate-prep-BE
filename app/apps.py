from django.apps import AppConfig
from app.utils import start_scheduler

class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        import app.signals
        start_scheduler()
