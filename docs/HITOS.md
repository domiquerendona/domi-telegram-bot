\# DOCUMENTO HISTÓRICO
#
# Este archivo describe el estado del sistema en una auditoría pasada.
# No debe usarse como fuente normativa del proyecto.

\# Hitos del proyecto Domiquerendona



\## v0.1-admin-saldos — Baseline de finanzas y auditoría



Desde el tag `v0.1-admin-saldos` se construye el historial financiero y de auditoría.



A partir de este punto:

\- El ledger se considera confiable.

\- Los saldos de administradores, aliados y repartidores tienen semántica estable.

\- El cambio de equipo es exclusivo (solo un vínculo APPROVED).

\- Cualquier cambio posterior en finanzas debe:

&nbsp; - ser compatible hacia atrás, o

&nbsp; - incluir migración explícita y documentada.


\## Cierre de ciclo técnico — Auditoría y saneamiento estructural

**Fecha:** marzo 2026

### Contexto

Se ejecutó un ciclo completo de auditoría técnica y saneamiento estructural del proyecto Domiquerendona, con el objetivo de:

\- validar brechas reales detectadas en auditoría,
\- corregir inconsistencias entre código y documentación,
\- reducir deuda técnica crítica sin abrir refactors masivos,
\- asegurar trazabilidad financiera en el flujo de entregas,
\- estabilizar el panel web y las pruebas del sistema.

El trabajo se realizó siguiendo una estrategia por fases para minimizar regresiones.

### Fases implementadas

**Fase 0 — diagnóstico verificable**

Se generó una auditoría objetiva del estado del sistema con evidencia directa en código.

Documentos resultantes:

\- `docs/alineacion_codigo_documentacion_2026-03-12.md`
\- `docs/callback_governance_2026-03-12.md`

Se verificaron:

\- callbacks reales del sistema,
\- accesos SQL fuera de capa,
\- estado real del cobro al courier,
\- componentes del panel web mock vs reales.

**Fase 1 — validación del cobro al courier**

Se confirmó que el cobro al courier ya existía en la ruta real de entrega, aunque estaba documentado de forma incorrecta.

Se añadieron pruebas para garantizar:

\- cobro único por entrega exitosa,
\- idempotencia ante reintentos,
\- ausencia de cobro en cancelación o expiración,
\- comportamiento correcto cuando el pedido es creado por un admin.

Archivo clave:

\- `tests/test_order_delivery_fees.py`

También se corrigió un warning contable relacionado con `admin_id` en el settlement.

**Fase 2 — gobernanza de callbacks**

Se construyó el inventario completo de `callback_data`.

Documento fuente:

\- `docs/callback_governance_2026-03-12.md`

Se definió el estándar:

\- `prefijo_valor`

Ejemplos:

\- `ally_team_TEAM1`
\- `courier_team_TEAM2`

Se mantuvo compatibilidad temporal con el formato antiguo usando `:`.

**Fase 3 — extracción de accesos directos a BD**

Se eliminó SQL inline en los módulos auditados.

Archivos saneados:

\- `Backend/profile_changes.py`
\- `Backend/web/api/admin.py`
\- `Backend/web/api/dashboard.py`

El patrón final quedó:

\- `endpoint/handler -> services.py -> db.py`

**Fase 4 — separación bot / FastAPI**

Se separó el bootstrap web del bootstrap del bot.

Nuevo entrypoint web:

\- `Backend/web_app.py`

Bot:

\- `Backend/main.py`

Esto redujo el acoplamiento sin reestructurar el bot completo.

**Fase 5 — saneamiento mínimo del panel web**

Se reemplazaron los componentes mock principales.

Implementado:

\- auth mínima real,
\- repositorio real mínimo de usuario web,
\- guards de acceso,
\- URL configurable en frontend,
\- endpoints desacoplados de `db.py`.

Archivos clave:

\- `Backend/web/auth/dependencies.py`
\- `Backend/web/auth/guards.py`
\- `Backend/web/users/repository.py`
\- `Frontend/src/environments/environment.ts`

**Fase 6 — ampliación de pruebas**

Se añadió cobertura para flujos críticos que no tenían test.

Suite final incluye:

\- `test_order_delivery_fees.py`
\- `test_callback_compatibility.py`
\- `test_web_permissions.py`
\- `test_web_auth_dependencies.py`
\- `test_web_admin_services.py`
\- `test_dashboard_services.py`
\- `test_web_user_repository.py`
\- `test_main_notification_services.py`

Resultado final:

\- `Ran 35 tests — OK`

### Estado final del sistema

Compilación:

\- `python -m py_compile`
\- `OK`

Tests:

\- `PYTHONPATH=Backend python -m unittest`
\- `OK`

Documentación alineada con el código.

Push final realizado:

\- `commit: da42d94`
\- `branch: staging`

### Resultado

El sistema quedó en un estado estable y verificable, con:

\- arquitectura saneada en las zonas críticas,
\- panel web mínimo real funcional,
\- callbacks gobernados,
\- trazabilidad financiera validada,
\- cobertura de pruebas para los flujos críticos.

Este ciclo no introdujo refactors masivos, priorizando cambios pequeños, verificables y reversibles.




## Cierre C1 - Reinicio de registro por Plataforma

Fecha de cierre: marzo 2026

### QuÃ© resuelve C1

Plataforma puede autorizar o revocar un reinicio de registro para:

- Administradores Locales
- Aliados
- Repartidores

### QuÃ© no cambia

- `INACTIVE` sigue intacto como estado de bloqueo operativo.
- No se creÃ³ un nuevo status.
- No se crean nuevas filas operativas del rol.
- No se alterÃ³ la semÃ¡ntica normal de aprobaciÃ³n, rechazo o inactivaciÃ³n.

### ImplementaciÃ³n final

- El reset quedÃ³ separado del campo `status`.
- La autorizaciÃ³n de reset es exclusiva de Plataforma.
- El gate de reingreso exige `INACTIVE + reset activo`.
- La reinscripciÃ³n reutiliza la misma fila del rol mediante reset in-place.
- El reset se consume al completar la reinscripciÃ³n autorizada.
- Antes del overwrite se guarda auditorÃ­a mÃ­nima en `registration_reset_audit`.

### ValidaciÃ³n tÃ©cnica lograda

C1 quedÃ³ validado en:

- SQLite
- PostgreSQL real

La validaciÃ³n cubriÃ³:

- migraciones y esquema
- helpers base
- services plataforma-only
- gates de entrypoints
- reset in-place
- auditorÃ­a previa al overwrite
- callbacks de Plataforma

### Alcance pendiente opcional

Quedan como mejoras opcionales, no como deuda crÃ­tica:

- historial visual de resets en panel
- nota libre al autorizar reset
- futura exposiciÃ³n en panel web
