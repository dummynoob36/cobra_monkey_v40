"""
Tracking Engine v4.0
--------------------

Este módulo actúa como capa de integración entre el motor de Cobra v4.0
y los sistemas de notificación externos (Telegram u otros).

Actualmente expone:
    send_telegram_message(message: str)

De esta forma el engine no depende directamente del módulo Telegram
y se facilita el mantenimiento y la sustitución futura de este sistema
si fuera necesario.
"""

from __future__ import annotations

from scripts.telegram.telegram_sender import send_telegram_text


def send_telegram_message(message: str) -> None:
    """
    Envoltura fina sobre telegram_sender.send_telegram_text().

    - Garantiza aislamiento del engine frente a errores.
    - Permite añadir logs adicionales si en un futuro se desea
      implementar un tracking más completo (base de datos, métricas, etc.)
    """
    print("[Tracking v4.0] Enviando mensaje a Telegram…")
    send_telegram_text(message)

