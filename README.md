# 🐍 Cobra Monkey v4.0

Sistema de análisis técnico automatizado basado en patrones A/B/D/E, E-Prime y supersignals.  
Ejecución diaria automática con GitHub Actions y envío de señales por Telegram.

## 🚀 Funcionalidades principales

- Descarga automática de precios diarios (FASE 0)
- Construcción de dataset con patrones A, B, D, E (FASE 1)
- Detección de E-Prime v4.0 y supersignals
- Mensaje diario/semanal formateado para Telegram (FASE 2)
- Resumen simple: `Patrón → Ticker → Precio` enviado cada día
- Motor unificado `run_v40.py` listo para producción
- Workflow GitHub Actions operativo

## 📦 Estructura del proyecto

cobra_monkey_v40/
│
├── scripts/
│ ├── fetch_daily_prices_core.py
│ └── tracking/
│
├── v40/
│ ├── engine/
│ │ ├── run_v40.py
│ │ ├── fetch_daily_prices_v40.py
│ │ ├── build_dataset_v40.py
│ │ └── …
│ ├── reports_v40.py
│ ├── engine_v40.py
│ └── config_v40.py
│
├── outputs/
│ ├── daily_prices/
│ └── logs/
│
└── .github/workflows/cobra_v40.yml


## ⚙️ Ejecución manual

python -m v40.engine.run_v40 --no-telegram


## 🕒 Automatización

El workflow `cobra_v40.yml` ejecuta el sistema L–V a las 22:30 (España).

## 💬 Contacto

Desarrollado con ❤️ como parte del proyecto Cobra Monkey.
