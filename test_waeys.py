import asyncio
import json
import qrcode

from WAeys.Defaults.index import default_connection_config
from WAeys.Utils.auth_utils import (
    init_auth_creds,
    make_memory_key_store,
)
from WAeys.Utils.browser_utils import Browsers
from WAeys.Socket.socket import make_socket


def print_error_details(data, path="event"):
    """Print fields that may contain WhatsApp connection errors."""

    interesting_keys = {
        "error",
        "errors",
        "code",
        "statuscode",
        "status_code",
        "reason",
        "message",
        "lastdisconnect",
        "disconnectreason",
        "output",
        "payload",
    }

    if isinstance(data, dict):
        for key, value in data.items():
            normalized_key = str(key).lower().replace("_", "")

            if normalized_key in interesting_keys:
                print(f"  {path}.{key} = {value!r}")

            if isinstance(value, (dict, list, tuple)):
                print_error_details(value, f"{path}.{key}")

            elif isinstance(value, BaseException):
                print(f"  {path}.{key} exception type = {type(value).__name__}")
                print(f"  {path}.{key} exception message = {value}")

    elif isinstance(data, (list, tuple)):
        for index, value in enumerate(data):
            print_error_details(value, f"{path}[{index}]")


async def main():
    config = default_connection_config()

    config["auth"] = {
        "creds": init_auth_creds(),
        "keys": make_memory_key_store(),
    }

    config["browser"] = Browsers.windows("Chrome")
    config["logger"].level = "info"
    config["keepAliveIntervalMs"] = 5000

    sock = make_socket(config)
    ev = sock["ev"]

    async def on_connection_update(update):
        print("\n" + "=" * 55)
        print("WHATSAPP CONNECTION UPDATE")
        print("=" * 55)

        try:
            print(json.dumps(update, indent=2, default=str))
        except Exception:
            print(repr(update))

        print("\nPossible error details:")
        print_error_details(update)

        if not isinstance(update, dict):
            print("Unexpected event type:", type(update).__name__)
            return

        qr_data = update.get("qr")

        if qr_data:
            try:
                image = qrcode.make(qr_data)
                image.save("whatsapp_qr.png")

                print("\nQR saved as whatsapp_qr.png")
                print(
                    "Scan it using WhatsApp > Linked devices "
                    "> Link a device."
                )
            except Exception as exc:
                print("\nQR IMAGE GENERATION ERROR")
                print("Error type:", type(exc).__name__)
                print("Error message:", str(exc))

        connection = update.get("connection")

        if connection == "open":
            print("\nSUCCESS: WhatsApp connected!")

        elif connection == "close":
            print("\nERROR: WhatsApp connection closed.")
            print("Full close event:", repr(update))

    def handle_connection_update(update):
        asyncio.create_task(on_connection_update(update))

    ev.on("connection.update", handle_connection_update)

    try:
        print("Starting WAeys connection...")
        print("Waiting for QR and connection events.")
        print("Press Ctrl+C to stop the test.\n")

        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("\nStopping WAeys...")

    finally:
        end_method = sock.get("end")

        if end_method:
            try:
                result = end_method()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                print("Shutdown warning:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest stopped.")