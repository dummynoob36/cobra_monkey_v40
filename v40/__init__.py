"""
Cobra Monkey v4.0 — Paquete principal del sistema
-------------------------------------------------

Este paquete contiene todos los módulos que forman el motor de Cobra v4.0:

- config_v40.py        → rutas, constantes, configuración global
- engine/              → ejecución diaria (run_v40), FASE 0, FASE 1
- engine_v40.py        → filtros y lógica del sistema
- reports_v40.py       → generación de mensajes diario/semanal
- data/                → dataset_v40.csv (generado automáticamente)

El paquete v40 debe ser importable mediante:

    import v40
    from v40.engine.run_v40 import run_v40

Se asegura así compatibilidad en:
- ejecución local
- ejecución como módulo: python -m v40.engine.run_v40
- GitHub Actions
"""

