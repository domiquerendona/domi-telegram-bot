# Migracion PostgreSQL-first — 2026-04-09

## Objetivo

Definir la salida ordenada del soporte dual `SQLite + PostgreSQL` para que el sistema opere y se valide de forma prioritaria sobre PostgreSQL, sin romper flujos criticos ni dejar pruebas sin reemplazo.

## Estado actual

- El estado vigente del codigo sigue siendo dual-engine.
- `Backend/db.py` detecta el motor por `DATABASE_URL` y mantiene bifurcaciones `postgres/sqlite`.
- `AGENTS.md` todavia declara soporte oficial multi-motor.
- En la operacion real, DEV (`staging`) y PROD ya corren sobre PostgreSQL.
- La mayoria de pruebas con BD hoy usan SQLite temporal (`DB_PATH` + `DATABASE_URL` ausente).

## Decision recomendada

Adoptar una estrategia `PostgreSQL-first` por fases:

- PostgreSQL pasa a ser el motor canonico para arquitectura, validacion real y pruebas criticas.
- SQLite deja de ser referencia de diseno y queda solo como compatibilidad transitoria mientras migran las pruebas.
- El retiro total de SQLite se hace en un ciclo dedicado, con evidencia funcional previa en `staging`.

## Por que conviene

- Reduce complejidad en `db.py` y en las migraciones.
- Evita bugs silenciosos por diferencias entre `sqlite3.Row` y `RealDictRow`.
- Alinea el desarrollo con el entorno real del bot.
- Disminuye deuda de placeholders, fechas, `PRAGMA`, `information_schema` y ramas por motor.

## Riesgos si se hace de golpe

- Se rompe buena parte de la suite actual porque muchas pruebas dependen de SQLite temporal.
- Se pueden perder validaciones rapidas si no se deja un reemplazo claro para pruebas con BD.
- Un cambio brusco mezclando arquitectura, motor y pruebas haria mas dificil aislar regresiones.

## Fases propuestas

### Fase 0 — Inventario y alineacion documental

Objetivo:
- Congelar el alcance y dejar una ruta oficial antes de tocar el motor.

Entregables:
- Este documento.
- Referencia visible desde `CLAUDE.md`.
- Registro de coordinacion en `WORKLOG.md`.

Estado:
- Iniciada en esta sesion.

### Fase 1 — PostgreSQL como validacion canonica

Objetivo:
- Mover la validacion real de flujos criticos a PostgreSQL de forma explicita.

Acciones:
- Definir un set minimo de smoke tests funcionales en `staging` para:
  - registro
  - aprobacion
  - recargas
  - pedido aliado
  - pedido especial admin
  - ruta
  - oferta / aceptacion / entrega
- Ejecutar y documentar esas validaciones solo contra PostgreSQL.
- Dejar claro en documentacion que "funciona en SQLite" ya no equivale a "listo para desplegar".

### Fase 2 — Migracion de pruebas con BD

Objetivo:
- Dejar de depender de SQLite para las pruebas que realmente validan persistencia.

Acciones:
- Separar pruebas sin BD real (AST, helpers puros, renderers) de pruebas con BD.
- Migrar las pruebas con BD a fixtures PostgreSQL dedicados.
- Eliminar el patron repetido de:
  - `os.environ["DB_PATH"] = ...`
  - `os.environ.pop("DATABASE_URL", None)`
- Mantener SQLite solo mientras existan pruebas no migradas.

Resultado esperado:
- Las pruebas de integracion y persistencia corren sobre PostgreSQL.
- SQLite queda reducido a compatibilidad temporal o se elimina por completo si ya no se usa.

### Fase 3 — Convergencia de codigo

Objetivo:
- Dejar de introducir deuda nueva dependiente del dual-engine.

Acciones:
- Revisar `Backend/db.py` y clasificar bifurcaciones:
  - necesarias solo por transicion
  - ya eliminables
  - reemplazables por SQL/PostgreSQL unico
- Prohibir nuevas ramas SQLite salvo para sostener pruebas aun no migradas.
- Corregir deuda visible asociada al dual-engine:
  - `.get()` sobre filas de BD
  - fallbacks distintos por tipo de row
  - fechas y placeholders duplicados por motor

### Fase 4 — Retiro de SQLite

Objetivo:
- Simplificar definitivamente la capa de datos.

Acciones:
- Eliminar `DB_ENGINE`, `P` y ramas `if DB_ENGINE == "postgres" else ...` que ya no apliquen.
- Retirar `sqlite3`, `DB_PATH`, `PRAGMA`, `AUTOINCREMENT` y cuerpos SQLite de `init_db()`.
- Reescribir `AGENTS.md`, `CLAUDE.md`, `Backend/DEPLOY.md` y cualquier guia operativa para reflejar un solo motor.
- Actualizar o eliminar pruebas/herramientas que dependan de SQLite.

## Criterios de salida para retirar SQLite

No retirar SQLite hasta que se cumplan todos:

1. Los flujos criticos estan validados en `staging` sobre PostgreSQL.
2. Existe una ruta clara para correr pruebas con BD sobre PostgreSQL.
3. Las pruebas que hoy usan SQLite fueron migradas o declaradas obsoletas.
4. `AGENTS.md` puede actualizarse sin contradecir el estado real del codigo.
5. El arranque, migraciones y persistencia sobreviven redeploy en Railway DEV.

## Orden recomendado de implementacion tecnica

1. Corregir deuda transversal provocada por compatibilidad de rows (`.get()` en filas de BD).
2. Disenar fixture/base de pruebas PostgreSQL para integracion.
3. Migrar primero las suites mas criticas:
   - `tests/test_recharge_idempotency.py`
   - `tests/test_order_lifecycle.py`
   - `tests/test_order_delivery_fees.py`
   - `tests/test_profile_change_services.py`
4. Recien despues iniciar retiro de ramas SQLite en `db.py`.

## Fuera de alcance por ahora

- Reescribir toda la suite en esta misma sesion.
- Cambiar ya `AGENTS.md` a un solo motor sin haber migrado pruebas y validacion.
- Eliminar `sqlite3` de `Backend/db.py` en este ciclo.

## Siguiente paso concreto

La siguiente iteracion deberia atacar un objetivo unico:

- crear el primer fixture de pruebas PostgreSQL para integracion, o
- auditar y corregir el uso de `.get()` sobre filas de BD como deuda heredada del dual-engine.
