
import logging

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


logger = logging.getLogger(__name__)


class ConnectionStatus(dict):
    """Connection information; truthy when WhatsApp is connected."""

    def __bool__(self):
        return bool(self.get("connected", False))


class EvolutionAPIService:
    """Client for the Evolution API WhatsApp instance."""

    def __init__(self, instance_name=None):
        self.base_url = (
            getattr(settings, "EVOLUTION_API_URL", "") or ""
        ).strip().rstrip("/")

        self.api_key = (
            getattr(settings, "EVOLUTION_API_KEY", "") or ""
        ).strip()

        self.instance_name = (
            instance_name
            or getattr(settings, "EVOLUTION_API_INSTANCE", "")
            or getattr(settings, "EVOLUTION_INSTANCE_NAME", "")
            or ""
        ).strip()

        # Backward compatibility with older code using .instance.
        self.instance = self.instance_name

        if not self.base_url:
            raise ImproperlyConfigured(
                "EVOLUTION_API_URL is not configured."
            )

        if not self.api_key:
            raise ImproperlyConfigured(
                "EVOLUTION_API_KEY is not configured."
            )

        if not self.instance_name:
            raise ImproperlyConfigured(
                "Set EVOLUTION_API_INSTANCE or "
                "EVOLUTION_INSTANCE_NAME."
            )

        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _error_result(state, message):
        return {
            "connected": False,
            "state": state,
            "qrcode": None,
            "base64": None,
            "pairingCode": None,
            "error": message,
        }

    # ----------------------------------------------------------
    # QR RESPONSE NORMALIZATION
    # ----------------------------------------------------------

    @staticmethod
    def _format_qr_response(data):
        """Normalize common Evolution API QR response formats."""

        if not isinstance(data, dict):
            return EvolutionAPIService._error_result(
                "invalid_response",
                "Evolution API returned an unexpected response.",
            )

        # Some API versions wrap the response in "data".
        nested = data.get("data")
        if isinstance(nested, dict):
            data = {**data, **nested}

        qr = data.get("qrcode")
        if isinstance(qr, dict):
            raw_qr = (
                qr.get("base64")
                or qr.get("code")
                or data.get("base64")
                or ""
            )
            pairing_code = (
                qr.get("pairingCode")
                or data.get("pairingCode")
            )
        else:
            raw_qr = (
                data.get("base64")
                or (qr if isinstance(qr, str) else "")
            )
            pairing_code = data.get("pairingCode")

        # Some responses return a QR string instead of an image.
        if isinstance(raw_qr, str) and raw_qr.startswith(
            ("data:image/", "data: image/")
        ):
            image = raw_qr.replace("data: image/", "data:image/", 1)
        elif isinstance(raw_qr, str) and raw_qr:
            image = f"data:image/png;base64,{raw_qr}"
        else:
            image = None

        return {
            "connected": False,
            "state": "qr" if image else (
                "pairing_code" if pairing_code else "waiting_for_qr"
            ),
            "qrcode": image,
            "base64": image,
            "code": data.get("code"),
            "pairingCode": pairing_code,
            "error": (
                None
                if image or pairing_code
                else "Evolution API returned no QR image or pairing code."
            ),
        }

    # ----------------------------------------------------------
    # CONNECTION STATUS
    # ----------------------------------------------------------

    @classmethod
    def check_connection(cls, instance_name=None):
        try:
            service = cls(instance_name=instance_name)
        except ImproperlyConfigured as exc:
            logger.error("Evolution API configuration error: %s", exc)
            return ConnectionStatus({
                "connected": False,
                "state": "configuration_error",
                "error": str(exc),
            })

        endpoint = service._url(
            f"instance/connectionState/{service.instance_name}"
        )

        try:
            response = requests.get(
                endpoint,
                headers=service.headers,
                timeout=15,
            )

            if not response.ok:
                logger.warning(
                    "Connection check returned HTTP %s",
                    response.status_code,
                )
                return ConnectionStatus({
                    "connected": False,
                    "state": "disconnected",
                    "error": f"Evolution API returned HTTP "
                             f"{response.status_code}.",
                })

            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Unexpected connection response.")

            nested = data.get("data")
            if isinstance(nested, dict):
                data = {**data, **nested}

            instance = data.get("instance")
            state = (
                instance.get("state", "")
                if isinstance(instance, dict)
                else ""
            ) or data.get("state", "")

            state = str(state).lower()

            return ConnectionStatus({
                "connected": state in ("open", "connected"),
                "state": state or "unknown",
                "data": data,
            })

        except (requests.RequestException, ValueError) as exc:
            logger.warning("Connection check failed: %s", exc)
            return ConnectionStatus({
                "connected": False,
                "state": "unreachable",
                "error": str(exc),
            })

    # ----------------------------------------------------------
    # GET OR CREATE QR CODE
    # ----------------------------------------------------------

    @classmethod
    def get_or_create_qr(cls, instance_name=None):
        try:
            service = cls(instance_name=instance_name)
        except ImproperlyConfigured as exc:
            return cls._error_result("configuration_error", str(exc))

        status = cls.check_connection(
            instance_name=service.instance_name
        )

        if status.get("connected"):
            return {
                "connected": True,
                "state": "open",
                "qrcode": None,
                "base64": None,
                "pairingCode": None,
                "error": None,
            }

        endpoint = service._url(
            f"instance/connect/{service.instance_name}"
        )

        try:
            response = requests.get(
                endpoint,
                headers=service.headers,
                timeout=30,
            )

            # Only try to create an instance when the API reports
            # that the instance is missing.
            if response.status_code == 404:
                return cls._create_instance(service)

            if not response.ok:
                logger.error(
                    "QR request failed: HTTP %s; response=%s",
                    response.status_code,
                    response.text[:500],
                )
                return cls._error_result(
                    "api_error",
                    f"Evolution API returned HTTP "
                    f"{response.status_code}. Check the API logs "
                    "and instance configuration.",
                )

            try:
                data = response.json()
            except ValueError:
                return cls._error_result(
                    "invalid_response",
                    "Evolution API did not return valid JSON.",
                )

            result = cls._format_qr_response(data)

            if result.get("error"):
                logger.warning(
                    "Evolution API QR response contained no QR image "
                    "or pairing code."
                )

            return result

        except requests.RequestException as exc:
            logger.exception("Failed to retrieve WhatsApp QR code.")
            return cls._error_result("unreachable", str(exc))

    @classmethod
    def _create_instance(cls, service):
        endpoint = service._url("instance/create")

        payload = {
            "instanceName": service.instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=service.headers,
                timeout=30,
            )

            # An existing instance or invalid configuration should
            # be diagnosed rather than silently recreated.
            if response.status_code not in (200, 201):
                logger.error(
                "Evolution API instance creation failed. "
                "URL=%s HTTP=%s BODY=%s",
                endpoint,
                response.status_code,
                response.text[:1000],
            )

                return cls._error_result(
                    "creation_failed",
                    f"Instance creation failed (HTTP {response.status_code}). "
                    f"API response: {response.text[:500]}",
        )

            try:
                data = response.json()
            except ValueError:
                return cls._error_result(
                    "invalid_response",
                    "Instance creation returned invalid JSON.",
                )

            result = cls._format_qr_response(data)

            # Some API versions create the instance successfully
            # but return no QR. Try the connect endpoint once.
            if not result.get("qrcode") and not result.get("pairingCode"):
                try:
                    qr_response = requests.get(
                        service._url(
                            f"instance/connect/{service.instance_name}"
                        ),
                        headers=service.headers,
                        timeout=30,
                    )
                    if qr_response.ok:
                        result = cls._format_qr_response(
                            qr_response.json()
                        )
                except (requests.RequestException, ValueError):
                    logger.warning(
                        "QR retrieval after instance creation failed."
                    )

            if not result.get("qrcode") and not result.get("pairingCode"):
                result["state"] = "waiting_for_qr"
                result["error"] = (
                    "Instance was created, but no QR code was returned. "
                    "Check the Evolution API instance state."
                )

            return result

        except requests.RequestException as exc:
            logger.exception("Instance creation request failed.")
            return cls._error_result("unreachable", str(exc))

    # ----------------------------------------------------------
    # SEND WHATSAPP TEXT
    # ----------------------------------------------------------

    def send_text_message(self, number, text):
        clean_number = "".join(
            character
            for character in str(number)
            if character.isdigit()
        )

        if not clean_number:
            return {
                "success": False,
                "error": "Invalid WhatsApp phone number.",
            }

        if not text or not text.strip():
            return {
                "success": False,
                "error": "Message text cannot be empty.",
            }

        endpoint = self._url(
            f"message/sendText/{self.instance_name}"
        )

        payload = {
            "number": clean_number,
            "text": text.strip(),
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=self.headers,
                timeout=30,
            )

            try:
                data = response.json()
            except ValueError:
                data = {"raw_response": response.text[:500]}

            if not response.ok:
                logger.error(
                    "Message send failed: HTTP %s",
                    response.status_code,
                )
                return {
                    "success": False,
                    "error": f"Evolution API returned HTTP "
                             f"{response.status_code}.",
                    "data": data,
                }

            return {"success": True, "data": data}

        except requests.RequestException as exc:
            logger.exception("WhatsApp message request failed.")
            return {"success": False, "error": str(exc)}

    # ----------------------------------------------------------
    # PHONE-NUMBER PAIRING CODE
    # ----------------------------------------------------------

    def get_pairing_code(self, phone_number):
        phone = "".join(
            character
            for character in str(phone_number)
            if character.isdigit()
        )

        if not 8 <= len(phone) <= 15:
            return {
                "success": False,
                "error": "Enter a valid phone number with country code.",
            }

        try:
            response = requests.get(
                self._url(
                    f"instance/connect/{self.instance_name}"
                ),
                params={"number": phone},
                headers=self.headers,
                timeout=30,
            )

            if not response.ok:
                logger.warning(
                    "Pairing-code request returned HTTP %s",
                    response.status_code,
                )
                return {
                    "success": False,
                    "error": "Evolution API could not generate a pairing code.",
                }

            data = response.json()
            if isinstance(data.get("data"), dict):
                data = {**data, **data["data"]}

            pairing_code = data.get("pairingCode")

            if pairing_code:
                return {
                    "success": True,
                    "pairingCode": pairing_code,
                    "phone_number": phone,
                }

            return {
                "success": False,
                "error": "No pairing code was returned by Evolution API.",
            }

        except (requests.RequestException, ValueError) as exc:
            logger.warning("Pairing-code request failed: %s", exc)
            return {
                "success": False,
                "error": "Could not retrieve the pairing code.",
            }

    # ----------------------------------------------------------
    # LOGOUT
    # ----------------------------------------------------------

    def logout(self):
        endpoint = self._url(
            f"instance/logout/{self.instance_name}"
        )

        try:
            response = requests.delete(
                endpoint,
                headers=self.headers,
                timeout=20,
            )

            try:
                data = response.json()
            except ValueError:
                data = {"raw_response": response.text[:500]}

            if response.ok:
                return {"success": True, "data": data}

            return {
                "success": False,
                "error": f"Evolution API returned HTTP "
                         f"{response.status_code}.",
                "data": data,
            }

        except requests.RequestException as exc:
            logger.exception("WhatsApp logout request failed.")
            return {"success": False, "error": str(exc)}
