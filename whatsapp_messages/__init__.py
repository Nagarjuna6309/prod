#  Recommended: Evaluated only when instantiated
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class EvolutionAPIService:

    def __init__(self):
        self.base_url = getattr(settings, "EVOLUTION_API_URL", None)
        self.api_key = getattr(settings, "EVOLUTION_API_KEY", None)

        if not self.base_url or not self.api_key:
            raise ImproperlyConfigured(
                "Both EVOLUTION_API_URL and EVOLUTION_API_KEY must be set in settings.py."
            )

        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }