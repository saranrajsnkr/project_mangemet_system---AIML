from django.apps import AppConfig
import sys

class InternshipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'internship'

    def ready(self):
        """
        Load signals, but skip them when running 'collectstatic'
        to prevent Google Sheets initialization errors during Docker build.
        """
        if 'collectstatic' in sys.argv:
            return
        import internship.signals
