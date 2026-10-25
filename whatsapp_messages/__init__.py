
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class EvolutionAPIService:
    def __init__(self, instance_name=None):
        self.base_url = getattr(
            settings, "EVOLUTION_API_URL", None
        )
        self.api_key = getattr(
            settings, "EVOLUTION_API_KEY", None
        )
        self.instance_name = (
            instance_name
            or getattr(settings, "EVOLUTION_INSTANCE_NAME", None)
        )

        if not self.base_url or not self.api_key:
            raise ImproperlyConfigured(
                "EVOLUTION_API_URL and EVOLUTION_API_KEY "
                "must be configured in settings.py."
            )

        if not self.instance_name:
            raise ImproperlyConfigured(
                "EVOLUTION_INSTANCE_NAME must be configured "
                "in settings.py."
            )

        self.base_url = self.base_url.rstrip("/")

        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }
