# Scoring and Walk-Forward

## Qué se añadió

### 1. Evidence scoring
Nuevo módulo:
- `v40/evidence_scoring.py`

Objetivo:
- no depender solo del patrón técnico del día
- añadir evidencia histórica por:
  - setup
  - contexto (`setup + market + regime`)

Cada señal puede recibir:
- `evidence_score`
- `evidence_label`
- `evidence_note`
- `context_signals`
- `setup_signals`
- `recent_context_signals`
- `recent_setup_signals`

Idea central:
- una señal técnicamente bonita pero con evidencia histórica débil debe quedar penalizada
- una señal técnicamente correcta y con contexto históricamente favorable debe subir

### 2. Walk-forward inicial
Nuevo módulo:
- `v40/walkforward_validation.py`

Script:
- `scripts/run_walkforward_validation.py`

Objetivo:
- evitar engañarnos con validación puramente in-sample
- medir cómo se comporta la selección cuando la evidencia se estima en el pasado y se aplica al futuro

Salida esperada:
- `data/walkforward_folds.csv`
- `data/walkforward_selected.csv`

---

## Cómo encaja en Cobra
Flujo actualizado:

1. `build_dataset_v40.py`
2. `daily_candidates.py`
   - filtros base
   - score técnico
   - evidence score
   - shortlist estricta
3. `reports_v40.py`
4. `run_v40.py`

---

## Filosofía de producto
Cobra no debe premiar frecuencia.

Debe premiar:
- calidad
- evidencia
- contexto
- estabilidad

Es correcto que algunos días la shortlist sea vacía.

---

## Estabilidad temporal
Ahora el evidence scoring también compara:
- rendimiento histórico total
- rendimiento reciente (ventana móvil)

Si el contexto o setup se deteriora claramente en la muestra reciente, la señal queda penalizada.
Si mejora, recibe un pequeño refuerzo.

## Reporte comparativo por setup
Script nuevo:
- `scripts/run_setup_evidence_report.py`

Salida:
- `data/setup_evidence_report.csv`

Sirve para revisar:
- señales totales vs recientes
- avg5 global vs reciente
- hit5 global vs reciente
- drift reciente

## Próximos pasos recomendados
1. calibrar umbrales de `evidence_score`
2. usar el reporte comparativo para podar setups
3. añadir benchmark por bucket (US / EU)
4. validar si `D_EU_TACTICAL` realmente merece seguir vivo
5. endurecer filtros de contexto si aún hay demasiado ruido
