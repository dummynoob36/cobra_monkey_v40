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

### Backtest operativo con restricciones reales

Para evaluar carga operativa, exposición y drawdown con solo los 3 setups válidos:

```bash
PYTHONPATH=. python scripts/run_risk_backtest.py
```

Con límites de simultaneidad y cooldown por ticker:

```bash
PYTHONPATH=. python scripts/run_risk_backtest.py --max-concurrent 8 --cooldown-days 10
```

Baseline operativo recomendado actualmente:
- `max_concurrent_positions = 8`
- `cooldown_days = 10`
- cupos por setup:
  - `A_REV_US = 2`
  - `A_REV_GLOBAL = 4`
  - `D_EU_TACTICAL = 2`
- sistema enfocado solo en:
  - `A_REV_US`
  - `A_REV_GLOBAL`
  - `D_EU_TACTICAL`

El reporte incluye:
- días medios en posición
- días medios hasta target
- días medios hasta stop
- % de cierres por expiry
- exposición simultánea media y máxima

Sweep rápido de configuraciones operativas:

```bash
PYTHONPATH=. python scripts/run_exit_policy_sweep.py
```

Sweep completo de baseline + cupos + carga operativa:

```bash
PYTHONPATH=. python scripts/run_full_operability_sweep.py
```

## 🕒 Automatización

El workflow `cobra_v40.yml` ejecuta el sistema L–V a las 22:45 UTC.

Motivo:
- mercados EU cerrados
- mercado US cerrado
- mayor probabilidad de tener barras diarias estables del proveedor

Además del dataset, el workflow persiste también el estado de cartera en:
- `data/portfolio_v40.csv`

Modo de uso recomendado en paper testing:
- Telegram recibe siempre el resumen operativo diario
- entradas solo si realmente se activa alguna posición
- salidas solo si realmente se cierra alguna posición
- estado de cartera solo si hay posiciones abiertas

## 💬 Contacto

Desarrollado con ❤️ como parte del proyecto Cobra Monkey.
