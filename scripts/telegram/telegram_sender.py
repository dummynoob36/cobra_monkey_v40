"""
Envío de mensajes a Telegram para Cobra v4.0
--------------------------------------------

Este módulo implementa una función simple y robusta para enviar mensajes
a Telegram sin dependencias externas fuera de `requests`.

Funciona tanto en local como en GitHub Actions.

Variables de entorno necesarias:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""

from __future__ import annotations
import os
import requests


def send_telegram_text(message: str) -> None:
    """
    Envía un mensaje de texto a Telegram usando la API oficial.

    Si faltan credenciales, simplemente muestra el mensaje en consola
    sin lanzar errores, para permitir que v4.0 funcione en modo testing.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Seguridad y modo local/testing
    if not token or not chat_id:
        print("[Telegram][WARN] Variables TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no definidas.")
        print("[Telegram][WARN] Mensaje NO enviado. Contenido:")
        print("--------------------------------------------------")
        print(message)
        print("--------------------------------------------------")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        if not response.ok:
            print(f"[Telegram][ERROR] HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[Telegram][ERROR] Excepción al enviar mensaje: {e}")

