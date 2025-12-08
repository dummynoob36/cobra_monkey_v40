"""
Configuración global de Cobra Monkey v4.0
-----------------------------------------

Este módulo centraliza todas las rutas importantes del proyecto v4.0,
asegurando que el motor pueda ejecutarse de forma idéntica en:

- Ejecución local manual
- Ejecución como módulo: python -m v40.engine.run_v40
- GitHub Actions

No contiene lógica del sistema ni cálculos; solo paths y constantes.
"""

from __future__ import annotations
from pathlib import Path


# ============================================================
# Rutas principales del proyecto
# ============================================================

# Raíz del repositorio cobra_monkey_v40
REPO_ROOT = Path(__file__).resolve().parents[1]

# Carpeta de datos generados por el sistema
DATA_DIR = REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Dataset principal v40
DATASET_V40_PATH = DATA_DIR / "dataset_v40.csv"

# Carpeta outputs/
OUTPUTS_DIR = REPO_ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# outputs/daily_prices/
DAILY_PRICES_DIR = OUTPUTS_DIR / "daily_prices"
DAILY_PRICES_DIR.mkdir(parents=True, exist_ok=True)

# outputs/logs/
LOGS_DIR = OUTPUTS_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Parámetros globales
# ============================================================

# Número de años de histórico requerido en daily prices
DEFAULT_HISTORY_YEARS = 2

# Días que abarca un "resumen semanal" (L-V)
WEEKLY_WINDOW_DAYS = 5

