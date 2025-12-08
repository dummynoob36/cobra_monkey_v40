"""
v40.engine — Motor principal del sistema Cobra v4.0
---------------------------------------------------

Este submódulo contiene todos los componentes del motor diario:

- run_v40.py
    Punto de entrada principal. Ejecuta:
        • FASE 0: actualización de daily prices
        • FASE 1: construcción/actualización del dataset v40
        • FASE 2: generación de mensajes diario/semanal
        • FASE 3: envío a Telegram (opcional)

- fetch_daily_prices_v40.py
    Wrapper de la FASE 0. Invoca el core Daily Prices v3.x desde
    scripts/fetch_daily_prices_core.py y reporta métricas.

- build_dataset_v40.py
    Construye el dataset v40 consolidando todos los daily prices.

Esta estructura permite ejecutar el sistema mediante:

    python -m v40.engine.run_v40

tanto en local como en GitHub Actions.
"""

