AGENTS.md — Reglas obligatorias del proyecto Domiquerendona

Este archivo define las reglas técnicas, operativas y de flujo de trabajo que TODOS los agentes (Claude, Codex u otros) deben obedecer estrictamente.

⚠️ No seguir estas reglas se considera un error grave.
⚠️ Estas reglas tienen prioridad absoluta sobre cualquier sugerencia del agente.

1. Restricciones críticas (NO negociables)

PROHIBIDO usar parse_mode o Markdown en cualquier mensaje del bot.

PROHIBIDO duplicar:

handlers

estados de ConversationHandler

funciones

callbacks

imports

Si algo se reemplaza, el código anterior DEBE eliminarse en el mismo commit.

PROHIBIDO borrar bloques grandes sin mostrar primero el bloque exacto existente.

PROHIBIDO ampliar el alcance sin autorización explícita del usuario.

Cambios mínimos obligatorios: un solo objetivo por instrucción.

2. Arquitectura y código

main.py contiene únicamente:

Orquestación

Flujo

Handlers

Toda la lógica de negocio debe vivir en:

services.py

u otros módulos dedicados

Reglas:

No crear funciones similares o redundantes.

Una función = una sola responsabilidad clara.

Respetar nombres, estructuras y funciones existentes.

No introducir nuevos patrones si ya existe uno funcional.

3. Base de datos (reglas estrictas)

Usar exclusivamente get_connection() para acceso a BD.

PROHIBIDO sqlite3.connect() directo.

Estados estándar únicos para todos los roles:

PENDING

APPROVED

REJECTED

INACTIVE

Desde la interfaz:

Nunca eliminar información.

No DELETE desde UI.

Solo cambio de status.

Registro:

Permitir nuevo registro solo si el registro previo está en INACTIVE.

Bloquear acciones si está en PENDING o APPROVED.

Separación estricta de identificadores:

telegram_id → solo mensajería

users.id → ID interno principal

admins.id, couriers.id, allies.id → IDs de rol

Nunca mezclar estos conceptos.

3B. Soporte oficial multi-motor (SQLite + PostgreSQL)
Objetivo

El sistema debe funcionar correctamente en:

SQLite (LOCAL / desarrollo)

PostgreSQL (PROD / Railway)

Reglas obligatorias

La selección de motor se determina exclusivamente por:

DATABASE_URL presente → PostgreSQL

DATABASE_URL ausente → SQLite

PROHIBIDO usar sintaxis exclusiva de un motor sin bifurcación controlada.

Todas las queries SQL deben usar la variable global:

P = "%s" if DB_ENGINE == "postgres" else "?"

Todas las queries deben usar:

f"... WHERE campo = {P}"

init_db() debe bifurcar explícitamente:

_init_db_postgres() para PostgreSQL

cuerpo SQLite separado

PROHIBIDO mezclar:

AUTOINCREMENT en PostgreSQL

SERIAL/BIGSERIAL en SQLite

PRAGMA en PostgreSQL

information_schema en SQLite

3C. Política oficial de migraciones
Principios

Las migraciones deben ser:

No destructivas

Idempotentes

Compatibles con datos existentes

PROHIBIDO:

DROP TABLE

TRUNCATE

migraciones que borren información en producción

Reglas

Toda nueva columna debe:

verificarse antes de agregarse

soportar ambos motores

En PostgreSQL:

usar information_schema.columns

En SQLite:

usar PRAGMA table_info

Toda migración debe ejecutarse dentro de init_db() o función controlada.

3D. Validaciones obligatorias en PRODUCCIÓN (PROD)
Seguridad de entorno

Si:

ENV == "PROD"

Entonces:

DATABASE_URL es obligatoria.

Si no existe, el sistema debe:

lanzar error fatal

impedir arranque

registrar log explícito

Prohibición crítica

PROHIBIDO permitir que PROD caiga silenciosamente a SQLite efímero.

Logging mínimo obligatorio en arranque

En PROD el sistema debe registrar:

Motor detectado (postgres/sqlite)

Ambiente (LOCAL/PROD)

Confirmación de conexión exitosa

Sin exponer credenciales.

3E. Regla anti-parches en compatibilidad multi-motor

PROHIBIDO parchear función por función cuando el problema sea estructural.

Si un error afecta múltiples funciones (ej. placeholders), se debe:

aplicar solución global

no soluciones locales repetidas

4. Flujos y estados

Los estados son globales y coherentes entre roles.

No crear estados nuevos sin validación explícita.

No romper flujos existentes que ya funcionan.

Cualquier ajuste debe ser compatible con el flujo actual del bot.

5. Regla anti-duplicación (OBLIGATORIA)

Antes de escribir código, el agente debe:

Buscar explícitamente con git grep handlers, callbacks, estados, funciones e imports.

Si un bloque se reemplaza:

eliminar el bloque anterior en el mismo commit.

PROHIBIDO dejar:

versiones muertas

funciones no usadas

handlers registrados dos veces

callbacks duplicados con distinto patrón

6. Flujo de trabajo con IA (OBLIGATORIO)
Antes de cambiar código

El agente debe:

Mostrar el bloque exacto que va a modificar.

Explicar brevemente qué se va a cambiar y por qué.

Confirmar:

rama activa

archivo exacto a tocar

Durante el trabajo

No asumir errores solo por ver diffs.

No repetir pasos ya completados.

No reescribir archivos completos sin autorización.

Después de los cambios

Ejecutar obligatoriamente:

python -m py_compile main.py services.py db.py

Reportar claramente:

qué cambió

qué se eliminó

por qué

7. Git y ramas

Nunca trabajar directamente sobre main.

Confirmar siempre la rama activa antes de modificar código.

Si un bloque se reemplaza, el código anterior debe desaparecer.

Mantener el repositorio:

limpio

sin duplicaciones ocultas

sin código zombie

7B. Regla obligatoria para cambios estructurales de BD

PROHIBIDO hacer merge a main cuando el cambio:

afecte estructura de base de datos

modifique init_db()

altere migraciones

cambie motor (SQLite/Postgres)

modifique placeholders globales

afecte lógica de persistencia

Todo cambio estructural de BD debe:

Implementarse en rama verify/*

Desplegarse en entorno de prueba

Validarse con:

arranque limpio

operaciones reales

persistencia tras redeploy

Solo después puede mergearse a main.

PROHIBIDO saltarse la rama verify/* en cambios de base de datos.

7C. Checklist obligatorio antes de merge a main

Aplicable cuando el cambio afecte:

Base de datos

Migraciones

init_db()

Placeholders SQL

Lógica de persistencia

Sistema de recargas

Cotizador

Flujos críticos

1. Verificación técnica mínima

Compilación sin errores

No duplicaciones

git grep limpio

2. Verificación de base de datos

Arranque sin crash

Tablas creadas

Inserciones reales funcionan

Persistencia tras redeploy

DATABASE_URL presente en PROD

3. Verificación funcional mínima

/start

/menu

Registro real

Cambio de estado

Acción que toque BD

4. Evidencia obligatoria

Debe existir evidencia documentada antes de merge.

8. Reglas específicas para agentes tipo Codex

Codex NO improvisa.

Debe:

Preguntar ante ambigüedad

Trabajar solo en el objetivo indicado

Mostrar evidencia si ejecuta comandos

9. Reglas del sistema de recargas (CRÍTICAS)

(Se mantiene íntegra la sección previamente definida en el proyecto.)

X. Cotizador y uso de APIs (CRÍTICO: control de costos)

(Se mantiene íntegra la sección previamente definida en el proyecto.)

10. Veracidad técnica y evidencia (OBLIGATORIA)

Separar siempre entre:

IMPLEMENTADO

PROPUESTA / FUTURO

Indicar archivo + función al afirmar existencia.

11. Regla de decisiones y veredictos (OBLIGATORIA)

Exponer opciones → preguntar → esperar confirmación → ejecutar.

PROHIBIDO cerrar decisiones de cambio por iniciativa propia.

12. Estilo de colaboración

Priorizar estabilidad sobre velocidad.

Preguntar antes de decidir.

No improvisar soluciones.

Asumir que el usuario:

es técnico

es detallista

quiere control total del sistema

Este documento representa el estándar definitivo y vigente del proyecto Domiquerendona.