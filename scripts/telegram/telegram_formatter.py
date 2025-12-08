"""
Formateador de mensajes para Cobra v4.0
---------------------------------------

Este módulo se encarga exclusivamente de construir mensajes de texto
válidos para Telegram, sin dependencias externas y evitando Markdown
complejo que pueda provocar errores al enviar mensajes.
"""

from __future__ import annotations
from typing import List


def build_message(
    phase: str,
    date: str,
    status: str,
    summary_lines: List[str],
    data_lines: List[str],
) -> str:
    """
    Construye un mensaje formateado para Telegram.

    Parámetros
    ----------
    phase : str
        Título o fase del proceso (ej. "FASE v4.0 · Diario (E-Prime)")
    date : str
        Fecha en formato YYYY-MM-DD
    status : str
        Estado general del análisis ("OK", "WARNING", "ERROR", etc.)
    summary_lines : List[str]
        Líneas de resumen (nº señales, indicadores principales…)
    data_lines : List[str]
        Líneas de detalle (tickers, listas, agrupaciones por patrón…)

    Retorno
    -------
    str : mensaje listo para enviar via Telegram.
    """

    lines: List[str] = []

    # Cabecera
    lines.append(f"{phase}")
    lines.append(f"📅 Fecha análisis: {date}")
    lines.append(f"📌 Estado: {status}")
    lines.append("━━━━━━━━━━━━━━━━━━")

    # Resumen
    for line in summary_lines:
        lines.append(line)

    # Detalle
    if data_lines:
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.extend(data_lines)

    return "\n".join(lines)

