import logging

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


logger = logging.getLogger(__name__)


class ConnectionStatus(dict):
    """
    Dictionary containing WhatsApp connection information.

    The object evaluates to True when WhatsApp is connected.
    """

    def __bool__(self):
        return bool(self.get("connected", False))


class EvolutionAPIService:
    """
    Service for communicating with Evolution API.
    """

    def __init__(self, instance: str = None):

        self.base_url = (
            getattr(
                settings,
                "EVOLUTION_API_URL",
                None,
            )
            or "http://localhost:8080"
        ).rstrip("/")

        self.api_key = (
            getattr(
                settings,
                "EVOLUTION_API_KEY",
                None,
            )
            or ""
        ).strip()

        self.instance = (
            instance
            or getattr(
                settings,
                "EVOLUTION_INSTANCE_NAME",
                None,
            )
            or "default"
        )

        if not self.api_key:
            raise ImproperlyConfigured(
                "Missing EVOLUTION_API_KEY in settings.py."
            )

        if not self.instance:
            raise ImproperlyConfigured(
                "Missing EVOLUTION_INSTANCE_NAME in settings.py."
            )

        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    # ==========================================================
    # CONNECTION STATUS
    # ==========================================================

    @classmethod
    def check_connection(
        cls,
        instance_name: str = None,
    ) -> ConnectionStatus:
        """
        Check whether the WhatsApp instance is connected.
        """

        try:
            service = cls(
                instance=instance_name
            )

        except ImproperlyConfigured as exc:
            logger.error(
                "Evolution API configuration error: %s",
                exc,
            )

            return ConnectionStatus(
                {
                    "connected": False,
                    "state": "configuration_error",
                    "error": str(exc),
                }
            )

        endpoint = (
            f"{service.base_url}/instance/"
            f"connectionState/{service.instance}"
        )

        try:
            response = requests.get(
                endpoint,
                headers=service.headers,
                timeout=5,
            )

            if response.status_code == 200:

                try:
                    data = response.json()
                except ValueError:
                    data = {}

                state = (
                    data.get(
                        "instance",
                        {},
                    ).get("state")
                    or data.get("state")
                    or ""
                ).lower()

                is_connected = state in [
                    "open",
                    "connected",
                ]

                return ConnectionStatus(
                    {
                        "connected": is_connected,
                        "state": state or "unknown",
                        "data": data,
                    }
                )

            logger.warning(
                "Evolution API connection check returned HTTP %s",
                response.status_code,
            )

            return ConnectionStatus(
                {
                    "connected": False,
                    "state": "disconnected",
                    "error": (
                        f"HTTP {response.status_code}"
                    ),
                }
            )

        except requests.exceptions.RequestException as exc:

            logger.warning(
                "Evolution API connection check failed: %s",
                exc,
            )

            return ConnectionStatus(
                {
                    "connected": False,
                    "state": "unreachable",
                    "error": str(exc),
                }
            )

    # ==========================================================
    # QR CODE
    # ==========================================================

    @classmethod
    def get_or_create_qr(
        cls,
        instance_name: str = None,
    ) -> dict:
        """
        Get the QR code for the configured Evolution API instance.

        If the instance does not exist, attempt to create it.

        Returns:

            {
                "connected": bool,
                "state": str,
                "qrcode": str | None,
                "base64": str | None,
                "pairingCode": str | None,
                "error": str | None,
            }
        """

        try:
            service = cls(
                instance=instance_name
            )

        except ImproperlyConfigured as exc:

            return {
                "connected": False,
                "state": "configuration_error",
                "qrcode": None,
                "base64": None,
                "pairingCode": None,
                "error": str(exc),
            }

        # ------------------------------------------------------
        # Check current connection first
        # ------------------------------------------------------

        connection = cls.check_connection(
            instance_name=service.instance
        )

        if connection.get("connected"):

            return {
                "connected": True,
                "state": "open",
                "qrcode": None,
                "base64": None,
                "pairingCode": None,
            }

        # ------------------------------------------------------
        # Request QR from existing instance
        # ------------------------------------------------------

        connect_endpoint = (
            f"{service.base_url}/instance/"
            f"connect/{service.instance}"
        )

        try:

            response = requests.get(
                connect_endpoint,
                headers=service.headers,
                timeout=10,
            )

            if response.status_code == 200:

                try:
                    data = response.json()
                except ValueError:

                    return {
                        "connected": False,
                        "state": "invalid_response",
                        "qrcode": None,
                        "base64": None,
                        "pairingCode": None,
                        "error": (
                            "Evolution API returned "
                            "an invalid JSON response."
                        ),
                    }

                return cls._format_qr_response(
                    data
                )

            # --------------------------------------------------
            # Instance doesn't exist
            # --------------------------------------------------

            if response.status_code in [400, 404]:

                return cls._create_instance(
                    service
                )

            return {
                "connected": False,
                "state": "error",
                "qrcode": None,
                "base64": None,
                "pairingCode": None,
                "error": (
                    "Evolution API returned "
                    f"HTTP {response.status_code}: "
                    f"{response.text}"
                ),
            }

        except requests.exceptions.RequestException as exc:

            logger.exception(
                "Error fetching QR code."
            )

            return {
                "connected": False,
                "state": "unreachable",
                "qrcode": None,
                "base64": None,
                "pairingCode": None,
                "error": str(exc),
            }

    @staticmethod
    def _format_qr_response(data: dict) -> dict:
        """
        Normalize QR response from different Evolution API
        response formats.
        """

        qr_object = data.get("qrcode")

        if isinstance(qr_object, dict):

            raw_base64 = (
                qr_object.get("base64")
                or data.get("base64")
                or ""
            )

            pairing_code = (
                qr_object.get("pairingCode")
                or data.get("pairingCode")
            )

        else:

            raw_base64 = (
                data.get("base64")
                or data.get("qrcode")
                or ""
            )

            pairing_code = data.get(
                "pairingCode"
            )

        formatted_base64 = (
            raw_base64
            if raw_base64.startswith(
                "data:image"
            )
            else (
                f"data:image/png;base64,{raw_base64}"
                if raw_base64
                else ""
            )
        )

        return {
            "connected": False,
            "state": "qr",
            "qrcode": formatted_base64 or None,
            "base64": formatted_base64 or None,
            "code": data.get("code"),
            "pairingCode": pairing_code,
        }

    @classmethod
    def _create_instance(
        cls,
        service,
    ) -> dict:
        """
        Create an Evolution API instance.
        """

        create_endpoint = (
            f"{service.base_url}/instance/create"
        )

        payload = {
            "instanceName": service.instance,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }

        try:

            response = requests.post(
                create_endpoint,
                json=payload,
                headers=service.headers,
                timeout=15,
            )

            if response.status_code not in [
                200,
                201,
            ]:

                return {
                    "connected": False,
                    "state": "creation_failed",
                    "qrcode": None,
                    "base64": None,
                    "pairingCode": None,
                    "error": (
                        "Failed to create Evolution API "
                        f"instance. HTTP "
                        f"{response.status_code}: "
                        f"{response.text}"
                    ),
                }

            try:
                data = response.json()
            except ValueError:

                return {
                    "connected": False,
                    "state": "invalid_response",
                    "qrcode": None,
                    "base64": None,
                    "pairingCode": None,
                    "error": (
                        "Evolution API returned "
                        "an invalid JSON response."
                    ),
                }

            result = cls._format_qr_response(
                data
            )

            result["state"] = "created"

            return result

        except requests.exceptions.RequestException as exc:

            logger.exception(
                "Error creating Evolution API instance."
            )

            return {
                "connected": False,
                "state": "unreachable",
                "qrcode": None,
                "base64": None,
                "pairingCode": None,
                "error": str(exc),
            }

    # ==========================================================
    # SEND TEXT MESSAGE
    # ==========================================================

    def send_text_message(
        self,
        number: str,
        text: str,
    ) -> dict:
        """
        Send a plain-text WhatsApp message.
        """

        clean_number = "".join(
            filter(
                str.isdigit,
                str(number),
            )
        )

        if not clean_number:

            return {
                "success": False,
                "error": (
                    "Invalid WhatsApp phone number."
                ),
            }

        if not text or not text.strip():

            return {
                "success": False,
                "error": (
                    "Message text cannot be empty."
                ),
            }

        endpoint = (
            f"{self.base_url}/message/"
            f"sendText/{self.instance}"
        )

        payload = {
            "number": clean_number,
            "text": text.strip(),
            "options": {
                "delay": 1200,
                "presence": "composing",
            },
        }

        try:

            response = requests.post(
                endpoint,
                json=payload,
                headers=self.headers,
                timeout=20,
            )

            try:
                data = response.json()
            except ValueError:
                data = {
                    "raw_response": response.text
                }

            if response.status_code not in [
                200,
                201,
            ]:

                logger.error(
                    "Evolution API message failed: "
                    "HTTP %s - %s",
                    response.status_code,
                    response.text,
                )

                return {
                    "success": False,
                    "error": (
                        f"Evolution API returned "
                        f"HTTP {response.status_code}: "
                        f"{response.text}"
                    ),
                    "data": data,
                }

            return {
                "success": True,
                "data": data,
            }

        except requests.exceptions.RequestException as exc:

            logger.exception(
                "Failed to send WhatsApp message."
            )

            return {
                "success": False,
                "error": str(exc),
            }

    # ==========================================================
    # LOGOUT / DISCONNECT
    # ==========================================================

    def logout(self) -> dict:
        """
        Logout the current Evolution API instance.
        """

        endpoint = (
            f"{self.base_url}/instance/"
            f"logout/{self.instance}"
        )

        try:

            response = requests.delete(
                endpoint,
                headers=self.headers,
                timeout=10,
            )

            try:
                data = response.json()
            except ValueError:
                data = {
                    "raw_response": response.text
                }

            if response.status_code in [
                200,
                201,
            ]:

                return {
                    "success": True,
                    "data": data,
                }

            return {
                "success": False,
                "error": (
                    f"Evolution API returned "
                    f"HTTP {response.status_code}"
                ),
                "data": data,
            }

        except requests.exceptions.RequestException as exc:

            logger.exception(
                "Failed to logout WhatsApp instance."
            )

            return {
                "success": False,
                "error": str(exc),
            }



def get_pairing_code(self, phone_number: str) -> dict:
 
    import logging
    import requests

    logger = logging.getLogger(__name__)

    phone = "".join(
        character for character in str(phone_number)
        if character.isdigit()
    )

    if len(phone) < 8 or len(phone) > 15:
        return {
            "success": False,
            "error": "Enter a valid phone number with country code.",
        }

    try:
        # Ask Evolution API to generate a pairing code.
        url = (
            f"{self.base_url.rstrip('/')}/instance/connect/"
            f"{self.instance}"
        )

        response = requests.get(
            url,
            params={"number": phone},
            headers=getattr(self, "headers", {}),
            timeout=30,
        )

        if not response.ok:
            logger.error(
                "Pairing-code request failed: HTTP %s",
                response.status_code,
            )
            return {
                "success": False,
                "error": (
                    "Evolution API could not generate a pairing code. "
                    "Check the instance and API configuration."
                ),
            }

        data = response.json()
        pairing_code = data.get("pairingCode")

        if not pairing_code and isinstance(data.get("data"), dict):
            pairing_code = data["data"].get("pairingCode")

        if pairing_code:
            return {
                "success": True,
                "pairingCode": pairing_code,
                "phone_number": phone,
                "message": (
                    "Open WhatsApp > Linked devices > "
                    "Link with phone number and enter this code."
                ),
            }

        return {
            "success": False,
            "error": (
                "No pairing code was returned. Check that your "
                "Evolution API version and WhatsApp connection "
                "mode support phone-number pairing."
            ),
            "details": data,
        }

    except requests.RequestException:
        logger.exception("Evolution API pairing request failed")
        return {
            "success": False,
            "error": "Could not connect to Evolution API.",
        }
    except (ValueError, TypeError):
        logger.exception("Invalid Evolution API response")
        return {
            "success": False,
            "error": "Evolution API returned an invalid response.",
        }