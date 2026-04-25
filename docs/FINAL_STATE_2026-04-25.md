# Cobra Scanner — Final state (2026-04-25)

## Objetivo consolidado
Cobra deja de evolucionar como sistema de trading complejo y se consolida como:

- scanner diario de oportunidades
- shortlist estricta
- patrones simples con evidencia
- posibilidad real de no emitir candidatas si no hay calidad suficiente

---

## Cambios implementados

### Arquitectura
- capa de shortlist diaria: `v40/daily_candidates.py`
- scoring con evidencia histórica: `v40/evidence_scoring.py`
- validación walk-forward simplificada: `v40/walkforward_validation.py`

### Salidas nuevas
- `data/daily_candidates.csv`
- `data/setup_evidence_report.csv`
- `data/walkforward_folds.csv`
- `data/walkforward_selected.csv`

### Reporting
- `reports_v40.py` ya muestra shortlist real
- el mensaje diario informa también cuando no hay candidatas de calidad

---

## Hallazgos clave

### A_REV_US
- sólido en histórico
- walk-forward positivo pero modesto
- sobrevive como setup principal
- contexto útil observado: `DOWN` + RSI profundo

### A_REV_GLOBAL
- deterioro reciente claro
- walk-forward flojo / negativo
- se desactiva por ahora del shortlist final

### D_EU_TACTICAL
- mejor de lo esperado en walk-forward simplificado
- sobrevive, pero bajo filtro estricto
- contexto útil observado: `EU + DOWN`

---

## Configuración final actual del shortlist

### Setups activos
- `A_REV_US`
- `D_EU_TACTICAL`

### Setups desactivados en shortlist
- `A_REV_GLOBAL`

### Umbrales
- `MIN_EVIDENCE_SCORE = 68`
- `MAX_CANDIDATES_TOTAL = 5`

### Reglas de contexto activas
- `A_REV_US`: patrón A, `US_OR_OTHER`, régimen `DOWN`, `RSI <= 28`
- `D_EU_TACTICAL`: patrón D, `EU`, régimen `DOWN`, `RSI <= 45`

---

## Lectura honesta
Esto no significa que los setups sean “verdad”.
Significa que, con la evidencia actual:
- A_REV_US merece seguir vivo
- D_EU_TACTICAL merece seguir vivo con vigilancia
- A_REV_GLOBAL no merece aparecer en producción por ahora

---

## Próximos pasos razonables
1. dejar correr el sistema varios días con shortlist real
2. revisar si la frecuencia baja es aceptable
3. evaluar manualmente las candidatas emitidas
4. recalibrar si el sistema queda demasiado estricto o demasiado suelto

---

## Qué no hacer ahora
- no añadir muchos patrones nuevos
- no meter live trading
- no complicar portfolio/risk antes de estabilizar selección
- no reactivar setups flojos solo por aumentar frecuencia
