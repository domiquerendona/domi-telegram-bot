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
| 2026-03-17 | claude | Backend/main.py, Backend/order_delivery.py, CLAUDE.md | Limpieza datetime.utcnow() deprecado: lazy import → top-level en main.py; docstring order_delivery.py actualizado | COMPLETADO |
| 2026-03-13 | claude | Backend/db.py, Backend/services.py, Backend/web_app.py, Backend/requirements.txt, Backend/web/api/auth.py, Backend/web/api/admin.py, Backend/web/api/users.py, Backend/web/auth/dependencies.py, Backend/web/users/repository.py, Backend/web/schemas/user.py, Frontend/src/app/core/services/auth.service.ts, Frontend/src/app/core/guards/role.guard.ts, Frontend/src/app/core/guards/auth.guard.ts, Frontend/src/app/features/login/login.ts, Frontend/src/app/app.routes.ts, Frontend/src/app/layout/components/sidebar/sidebar.ts, Frontend/src/app/features/superadmin/administradores/administradores.ts, CLAUDE.md | Multi-usuario real panel web: tabla web_users + bcrypt, ADMIN_LOCAL scoping, AuthService + RoleGuard Angular, gestión usuarios panel | COMPLETADO |
| 2026-03-12 | claude | Backend/web/users/roles.py, Backend/web/auth/guards.py, Backend/web/auth/dependencies.py, Backend/web/api/admin.py | RBAC fino panel web: Permission enum, ROLE_PERMISSIONS, has_permission(), require_permission() factory — endpoints /reject y /settings/pricing exclusivos PLATFORM_ADMIN | COMPLETADO |
| 2026-03-09 | codex | Backend/main.py, Backend/services.py, Backend/db.py, WORKLOG.md | Bienvenida courier: mensaje + recarga automática $5.000 al aprobar (Admin Local y Plataforma) | COMPLETADO |
| 2026-03-05 | claude | Backend/main.py, CLAUDE.md | Fix: pedido_nueva_dir ahora pasa por geocoding completo (PEDIDO_UBICACION) | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md, Backend/db.py, Backend/services.py, Backend/order_delivery.py | Tracking tiempos de entrega + estadísticas por repartidor | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md | Docs: lecciones Edit tool y escape sequences en bash | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md, Backend/db.py, Backend/services.py | Merge verify/live-location-expiry-15m + cherry-pick costeo Google Maps | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md | Reglas colaboración multi-agente (sección 15) | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md, WORKLOG.md | Sistema coordinación multi-agente: WORKLOG, prefijos, protocolo pre-push (15A-15G) | COMPLETADO |
| 2026-03-02 | claude | AGENTS.md, CLAUDE.md | Routing de documentación (sección 16) y regla de cambios estructurales (sección 17) | COMPLETADO |

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
# 1. Mover fila de "Sesiones activas" a "Historial" y commitear el WORKLOG
git commit -m "[claude] worklog: cierre — <descripción breve>"

# 2. PROTOCOLO PRE-PUSH (obligatorio antes de cada push)
git fetch origin staging
git log --oneline HEAD..origin/staging    # ¿hay commits nuevos del otro agente?
git diff --name-only HEAD origin/staging  # ¿tocan los mismos archivos que yo modifiqué?

# Sin solapamiento de archivos -> push normal
git push origin staging

# Con solapamiento en mismos archivos -> PAUSAR
# Reportar a Luis Felipe: qué archivos, cuál es tu cambio, cuál es el del otro agente
# Esperar instruccion antes de pushear
```

> **Regla de oro:** PROHIBIDO `git push --force`. Si el push es rechazado por fast-forward,
> hacer fetch + revisar + reportar a Luis Felipe.

### Filtrar commits por agente
```bash
git log --oneline --grep="\[claude\]"
git log --oneline --grep="\[codex\]"
```
