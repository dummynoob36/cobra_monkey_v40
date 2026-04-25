# Cobra Scanner Fast Track

## Objetivo
Convertir Cobra Monkey v4.0 en un **scanner diario de oportunidades** simple, rápido y útil.

El sistema debe:
- recorrer un universo de tickers
- detectar solo unos pocos setups con evidencia
- rankear señales por calidad
- entregar una lista diaria corta de candidatos
- evitar convertirse en una plataforma de trading compleja

---

## Decisión estratégica
No usar QuantDinger como núcleo.

Sí reutilizar Cobra porque ya tiene:
- ingestión diaria de precios
- universe files
- feature engineering
- detección de patrones
- validación forward
- quality tier
- signal scoring
- workflow GitHub operativo
- reporting diario

La dirección correcta es **podar y enfocar**, no reconstruir desde cero.

---

## Qué debe ser Cobra a partir de ahora
Cobra debe actuar como un sistema con 4 capas:

1. **Data layer**
   - universe
   - daily OHLCV
   - limpieza y consistencia

2. **Research layer**
   - features
   - patrones simples
   - validación histórica
   - comparación por mercado/regímenes

3. **Signal layer**
   - elegibilidad diaria
   - quality tier
   - signal score
   - ranking final

4. **Delivery layer**
   - mensaje diario
   - artifacts CSV
   - opcional dashboard ligero

No debe ser todavía:
- live trading engine
- broker platform
- portfolio optimizer complejo
- sistema multiagente

---

## Activos reutilizables de Cobra

### Mantener
- `v40/engine/fetch_daily_prices_v40.py`
- `v40/engine/build_dataset_v40.py`
- `v40/pattern_validation.py`
- `v40/pattern_quality.py`
- `v40/signal_scoring.py`
- `v40/setup_definitions.py`
- `v40/reports_v40.py`
- `.github/workflows/cobra_v40.yml`
- `data/universe_live.txt`
- `outputs/daily_prices/`

### Mantener pero rebajar protagonismo
- `v40/operability.py`
- `scripts/run_risk_backtest.py`
- `scripts/run_exit_policy_sweep.py`
- `scripts/run_full_operability_sweep.py`
- `data/portfolio_v40.csv`

### Sacar del foco del producto
- narrativa de cartera viva
- gestión operativa diaria como núcleo
- complejidad de entradas/salidas si no mejora selección

---

## Setups iniciales permitidos
Mantener solo estos setups mientras no aparezca evidencia mejor:
- `A_REV_US`
- `A_REV_GLOBAL`
- `D_EU_TACTICAL`

Reglas actuales ya observadas como útiles:
- `A_REV_US`: patrón A + `RSI < 28`
- `A_REV_GLOBAL`: patrón A + `RSI < 30`
- `D_EU_TACTICAL`: patrón D en EU fuera de `RANGE`

Regla de producto:
**si un patrón no tiene evidencia suficiente, no se enseña.**

---

## Producto mínimo objetivo
Cada ejecución diaria debe producir:

1. `dataset_v40.csv` actualizado
2. shortlist diaria de señales elegibles
3. ranking ordenado por calidad
4. mensaje corto con top candidatos
5. artifact persistente para revisar histórico

Formato ideal de cada candidato:
- ticker
- setup
- score
- quality_tier
- close
- entry orientativa
- stop orientativo
- target orientativo
- nota breve de contexto

---

## Roadmap rápido

### Fase 1 — Consolidación del scanner
Objetivo: que Cobra entregue una lista diaria limpia.

Tareas:
1. congelar el universo actual útil
2. consolidar los 3 setups válidos
3. revisar score y quality para que penalicen ruido
4. limitar salida diaria a top N
5. generar un CSV de shortlist diario

Entregables:
- `data/daily_candidates.csv`
- mensaje Telegram con top 5 o top 10
- workflow estable

### Fase 2 — Validación seria de setups
Objetivo: decidir qué sobrevive de verdad.

Tareas:
1. backtest por setup
2. métricas por mercado
3. métricas por régimen
4. estabilidad temporal
5. control de sample size mínimo

Métricas mínimas:
- número de señales
- hit rate 5d / 10d / 20d
- avg return 5d / 10d / 20d
- drawdown aproximado
- profit factor si aplica
- estabilidad por periodos

### Fase 3 — Refinamiento de selección
Objetivo: menos ruido, más utilidad diaria.

Tareas:
1. score basado en evidencia histórica + contexto actual
2. rank por bucket (US / EU)
3. cap por setup
4. mínimo score para entrar al shortlist
5. control de duplicidad por ticker

### Fase 4 — UX ligera
Objetivo: hacer el resultado cómodo de usar.

Tareas:
1. mensaje diario más claro
2. artifact CSV/markdown/html simple
3. drill-down opcional por ticker

---

## Cambios inmediatos recomendados

### 1. Crear shortlist explícita
Añadir una salida diaria tipo:
- `data/daily_candidates.csv`

Con columnas mínimas:
- `signal_date`
- `ticker`
- `setup_code`
- `pattern_family`
- `quality_tier`
- `signal_score`
- `close`
- `entry_price`
- `stop_price`
- `target_price`
- `setup_note`
- `quality_note`

### 2. Reducir la salida diaria
En Telegram o reporte principal mostrar solo:
- top 5 global
- o top 3 US + top 3 EU

### 3. Separar research de delivery
- `build_dataset_v40.py` produce señales y features
- un selector posterior construye shortlist elegible
- el reporte solo consume shortlist, no todo el dataset

### 4. Mantener portfolio como opcional
No borrarlo todavía.
Solo dejar de tratarlo como la pieza central.

---

## Criterios de diseño
- simple > brillante
- pocas señales buenas > muchas señales mediocres
- evidencia > intuición
- daily batch > complejidad intradía
- shortlist útil > dashboard espectacular

---

## Primera tanda de tareas técnicas

### Prioridad A
1. crear módulo `v40/daily_candidates.py`
2. generar shortlist desde `dataset_v40.csv`
3. persistir `data/daily_candidates.csv`
4. adaptar `reports_v40.py` para leer shortlist
5. actualizar workflow para commitear shortlist

### Prioridad B
1. añadir filtros mínimos por score
2. limitar candidatos por setup
3. limitar candidatos por ticker
4. separar reporte operativo de reporte research

### Prioridad C
1. crear validación walk-forward simple
2. sacar tabla comparativa por setup
3. versionar reglas activas de selección

---

## Definición de éxito
El sistema va bien si, cada día, puede responder con claridad:
- qué tickers son candidatos hoy
- por qué aparecen
- qué setup los activa
- cuál es su calidad relativa
- cuáles merecen atención primero

Si hace más cosas pero responde peor a eso, estamos complicándolo demasiado.
