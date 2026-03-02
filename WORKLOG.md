# WORKLOG — Registro de Sesiones de Agentes IA

> Archivo mantenido por **Claude Code** y **Codex**.
> Actualizar al INICIO y al FIN de cada sesión de trabajo.
> Reglas completas: AGENTS.md Sección 15.

---

## Sesiones activas

| Agente | Inicio | Archivos | Tarea |
|--------|--------|----------|-------|
| (ninguna) | — | — | — |

---

## Historial reciente

| Fecha | Agente | Archivos tocados | Tarea | Estado |
|-------|--------|------------------|-------|--------|
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md, Backend/db.py, Backend/services.py, Backend/order_delivery.py | Tracking tiempos de entrega + estadísticas por repartidor | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md | Docs: lecciones Edit tool y escape sequences en bash | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md, Backend/db.py, Backend/services.py | Merge verify/live-location-expiry-15m + cherry-pick costeo Google Maps | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md | Reglas colaboración multi-agente (sección 15) | COMPLETADO |

---

## Guía rápida

### Iniciar sesión
```bash
git pull origin staging
git log --oneline -15 origin/staging    # revisar trabajo reciente del otro agente
cat WORKLOG.md                           # verificar sesiones activas
# Agregar fila en "Sesiones activas" y hacer commit+push:
git commit -m "[claude] worklog: inicio — <descripción breve>"
git push origin staging
```

### Cerrar sesión
```bash
# Mover fila de "Sesiones activas" a "Historial reciente" con estado COMPLETADO o PENDIENTE
git commit -m "[claude] worklog: cierre — <descripción breve>"
git push origin staging
```

### Filtrar commits por agente
```bash
git log --oneline --grep="\[claude\]"
git log --oneline --grep="\[codex\]"
```
