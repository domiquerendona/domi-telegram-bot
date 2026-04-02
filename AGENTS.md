AGENTS.md — Reglas obligatorias del proyecto Domiquerendona

Este archivo define las reglas técnicas, operativas y de flujo de trabajo que TODOS los agentes (Claude, Codex u otros) deben obedecer estrictamente.

⚠️ No seguir estas reglas se considera un error grave.
⚠️ Estas reglas tienen prioridad absoluta sobre cualquier sugerencia del agente.

Jerarquía documental oficial

Nivel 1 — Reglas obligatorias del proyecto
- Fuente de verdad: `AGENTS.md`
- Temas: arquitectura obligatoria, flujo de trabajo del repositorio, callbacks y convenciones, reglas de base de datos, ramas, coordinación entre agentes y reglas anti-regresión documental.

Nivel 2 — Guía técnica y arquitectura explicada
- Fuente: `CLAUDE.md`
- Propósito: explicar arquitectura, estructura del repo, módulos, flujos y despliegue.
- Si hay conflicto con `AGENTS.md`, manda `AGENTS.md`.

Nivel 3 — Gobernanza específica de componentes
- `docs/callback_governance_2026-03-12.md` → fuente de verdad de callbacks
- `Backend/DEPLOY.md` → fuente de verdad de despliegue
- `docs/business/contexto-negocio-domiquerendona.md` → fuente de verdad de negocio
- `WORKLOG.md` → fuente de verdad de coordinación de agentes

Nivel 4 — Documentos históricos / snapshot
- `docs/alineacion_codigo_documentacion_2026-03-12.md`
- `docs/HITOS.md`
- Estos documentos describen auditorías o hitos pasados y no son normativa vigente.

1. Restricciones críticas (NO negociables)

PROHIBIDO usar parse_mode o Markdown en cualquier mensaje del bot.

PROHIBIDO usar `datetime.utcnow()` en cualquier archivo Python del proyecto (deprecated desde Python 3.12).
Usar siempre `datetime.now(timezone.utc).replace(tzinfo=None)` para obtener UTC naive (compatible con la BD).
Asegurarse de que `timezone` esté importado: `from datetime import datetime, timezone`.

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

main.py contiene ÚNICAMENTE:

- Registro y wiring de handlers (CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler)
- Funciones handler que solo: validan formato de entrada → llaman a services → retornan next state
- Helpers de UI e input (teclados, hints, validadores de formato simples)
- Gestión de estado de flujo (_set_flow_step, _clear_flow_data_from_state)
- Constantes de UI (_OPTIONS_HINT y similares)

PROHIBIDO en main.py:

- Funciones que llamen directamente a cualquier función de db.py
- Validaciones de rol o permisos (es_admin_plataforma, _get_reference_reviewer, etc.)
- Lectores de configuración que consulten BD (get_setting, _get_important_alert_config, etc.)
- Lógica condicional basada en datos de BD
- Construcción de listas de comandos según estado de usuario

Toda la lógica de negocio debe vivir en services.py u otros módulos dedicados.

Regla de trigger — una función DEBE moverse a services.py si:

1. Llama a cualquier función importada de db.py
2. Valida roles, permisos o estados de usuario
3. Lee o interpreta configuración desde BD
4. Tiene lógica condicional basada en datos persistidos

Reglas generales:

No crear funciones similares o redundantes.
Una función = una sola responsabilidad clara.
Respetar nombres, estructuras y funciones existentes.
No introducir nuevos patrones si ya existe uno funcional.

2B. Patrón oficial de helpers de input en main.py

Cuando 3 o más handlers repiten la misma lógica de validación de campo, se DEBE usar o extender los helpers existentes. No crear nuevas variantes ad-hoc.

Helpers establecidos (main.py):

_handle_phone_input(update, context, storage_key, current_state, next_state, flow, next_prompt)
    Valida mínimo 7 dígitos. Almacena en context.user_data[storage_key].

_handle_text_field_input(update, context, error_msg, storage_key, current_state, next_state, flow, next_prompt)
    Valida que el texto no esté vacío. Almacena en context.user_data[storage_key].

_OPTIONS_HINT
    Constante de texto para opciones de cancelación. SIEMPRE usar esta constante, nunca escribir el hint inline.

Regla: si se necesita un nuevo tipo de validación repetida en 3+ handlers, primero proponer el helper al usuario y esperar aprobación antes de implementarlo.

Handlers que usan estos helpers actualmente:
ally_phone, ally_city, ally_barrio
courier_phone, courier_city, courier_barrio
admin_phone, admin_city, admin_barrio

2C. Convención obligatoria de claves en context.user_data

Cada flujo de registro usa su propio prefijo en TODAS sus claves de user_data.
No compartir claves entre flujos distintos aunque el campo sea "el mismo".

Prefijos establecidos:
- Flujo aliado:    ally_phone, ally_name, ally_owner, ally_document, city, barrio, address, ally_lat, ally_lng
- Flujo courier:   phone, courier_fullname, courier_idnumber, city, barrio, residence_address, courier_lat, courier_lng
- Flujo admin:     phone, admin_city, admin_barrio, admin_residence_address, admin_lat, admin_lng
- Flujo pedido:    pickup_*, pickup_city, pickup_barrio, new_pickup_address, new_pickup_city, new_pickup_barrio, customer_*, customer_city, customer_barrio, instructions, requires_cash, cash_required_amount, pedido_incentivo, pedido_incentivo_edit_order_id, pedido_pending_location_*, pedido_pending_prefill_address, pedido_pending_customer_city, pedido_pending_customer_barrio, etc.
- Flujo recarga:   recargar_target_type, recargar_target_id, recargar_admin_id, etc.
- Flujo ingreso externo (plataforma): ingreso_monto, ingreso_metodo
- Flujo ruta:      ruta_* (incluye ruta_pickup_city, ruta_pickup_barrio, ruta_temp_city, ruta_temp_barrio, etc.)
- Flujo agenda clientes: clientes_pending_* (clientes_pending_mode, clientes_pending_address_text, clientes_pending_lat, clientes_pending_lng, clientes_pending_city, clientes_pending_barrio, clientes_pending_notes), clientes_geo_mode (valores: "nuevo_cliente" | "dir_nueva" | "dir_editar" | "corregir_coords"), clientes_geo_address_input, current_customer_id, current_address_id
- Flujo mis ubicaciones (aliado): ally_locs_* (ally_locs_new_lat, ally_locs_new_lng, ally_locs_new_label, ally_locs_new_city, ally_locs_new_barrio)
- Flujo invitaciones admin: admin_invite_token (token temporal resuelto desde `/start` para preseleccionar admin en registro nuevo de aliado o repartidor)

Reglas:
- PROHIBIDO leer una clave de flujo A dentro de un handler de flujo B.
- Si se agrega una clave nueva, documentarla en esta sección en el mismo commit.
- PROHIBIDO usar claves genéricas ("data", "value", "temp") sin prefijo de flujo.

Regla obligatoria de direcciones (ciudad + barrio/sector):
- Toda creación/registro de una dirección (pickups del aliado, direcciones de clientes, paradas de ruta, etc.) DEBE pedir y guardar siempre ciudad y barrio/sector.

2D. Estándar obligatorio de callback_data

Formato estándar actual: `{dominio}_{accion}` o `{dominio}_{accion}_{id}`

También se aceptan formatos compuestos cuando el flujo lo requiere, por ejemplo:
- `pedido_inc_{order_id}x{monto}`
- `ruta_entregar_{route_id}_{seq}`

Prefijos de dominio existentes y sus dueños:
- admin_       → panel y acciones de administrador local
- admpedidos_  → panel de pedidos del administrador (listado, filtros por estado)
- agenda_      → agenda de pedidos
- ally_        → acciones específicas del aliado (fuera del flujo de pedido)
- allycust_    → agenda de clientes del aliado
- chgreq_      → solicitudes de cambio de perfil (profile_changes.py)
- chgteam_     → cambio de equipo/grupo
- config_      → configuración del sistema
- cotizar_     → flujo de cotización de envío
- courier_     → acciones de repartidor
- cust_        → acciones de cliente
- acust_       → agenda de clientes del administrador
- adirs_       → direcciones del administrador
- dir_         → gestión de direcciones de recogida del aliado
- guardar_     → guardar dirección de cliente tras un pedido
- menu_        → navegación de menú
- local_       → panel operativo del administrador local
- offer_       → sugerencias de incentivo/oferta
- order_       → ofertas y entrega de pedidos (order_delivery.py)
- pagos_       → sistema de pagos
- pedido_      → flujo de creación de pedidos
- perfil_      → cambios de perfil de usuarios (profile_changes.py)
- plat_        → panel de recargas/plataforma
- pickup_      → selección de punto de recogida
- preview_     → previsualización de pedido antes de confirmar
- pricing_     → configuración de tarifas
- rating_      → calificación post-entrega
- recargar_    → sistema de recargas
- recharge_    → revisión/aprobación de recargas (deprecado, compatibilidad vigente)
- ref_         → validación de referencias
- solequipo_   → solicitud de cambio/unión de equipo
- terms_       → aceptación de términos y condiciones
- ubicacion_   → selección de ubicación GPS
- ingreso_     → registro de ingreso externo del administrador de plataforma

Formato estándar vigente para selección de equipo:
- `ally_team_TEAM1`
- `courier_team_TEAM1`

Formato deprecado pero soportado temporalmente:
- `ally_team:TEAM1`
- `courier_team:TEAM1`

Ver inventario completo y gobernanza operativa en `docs/callback_governance_2026-03-12.md`.

Reglas:
- PROHIBIDO crear un prefijo nuevo sin aprobación explícita del usuario.
- PROHIBIDO usar callback_data sin prefijo de dominio.
- El separador vigente es guion bajo (_). No crear callbacks nuevos con `:`, guion, punto ni slash.
- Antes de agregar un callback nuevo, verificar con git grep que no existe uno equivalente.

2G. Entry points del sistema

Entry points vigentes:
- Bot Telegram → `Backend/main.py`
- Web FastAPI → `Backend/web_app.py`

Arranque local del bot:
- `python main.py`

Arranque local web:
- `uvicorn web_app:app --reload --port 8000`

2H. Regla obligatoria de documentación

Si un cambio modifica arquitectura, callbacks, entrypoints, estructura del repositorio o reglas del sistema, el cambio DEBE actualizar la documentación correspondiente en el mismo ciclo.

Orden obligatorio de actualización documental:
1. `AGENTS.md`
2. Documento específico del tema (`docs/callback_governance_2026-03-12.md`, `Backend/DEPLOY.md`, etc.)
3. `CLAUDE.md` si afecta arquitectura explicada o guía técnica

No se aceptan cambios estructurales sin actualización documental consistente.

2E. Regla de módulos adicionales

Módulos existentes y su dominio:
- db.py           → acceso a base de datos únicamente. Sin lógica de negocio.
- services.py     → toda la lógica de negocio que no es específica de un dominio grande.
- order_delivery.py → flujo completo de entrega de pedidos (publicación, callbacks, panel).
- profile_changes.py → flujo de cambios de perfil de usuarios.
- main.py         → orquestación, handlers, wiring.

Regla para crear un módulo nuevo:
Solo se crea un nuevo módulo .py si:
1. El dominio es claramente independiente del resto.
2. Agrupa más de 5 funciones cohesivas de ese dominio.
3. El usuario lo aprueba explícitamente.

PROHIBIDO crear módulos nuevos por conveniencia o para "desahogar" main.py.
La solución correcta para aliviar main.py es mover lógica a services.py.

2F. Patrón oficial de re-exportación en services.py

main.py NUNCA importa directamente de db.py.
Todo acceso a funciones de db.py desde main.py debe pasar por services.py.

Estructura obligatoria:

db.py          → define funciones de acceso a BD
services.py    → importa de db.py y re-exporta lo necesario para main.py
main.py        → importa exclusivamente de services.py (salvo 3 excepciones de arranque)

Excepciones permitidas en main.py (SOLO estas 3):
- from db import init_db
- from db import force_platform_admin
- from db import ensure_pricing_defaults

Cualquier otra importación directa de db.py en main.py es una violación de arquitectura.

Regla de re-exportación:
Si main.py necesita una función de db.py que aún no está en services.py:
1. Agregarla al bloque de re-exports en services.py (marcado # Re-exports para que main.py no acceda a db directamente)
2. Importarla en main.py desde services.py
3. PROHIBIDO importarla directamente desde db.py

Regla anti-importación circular:
Si un módulo secundario (profile_changes.py, order_delivery.py, etc.) necesita funciones de main.py
→ PROHIBIDO importar desde main en el módulo superior del archivo
→ Solución: mover la función a services.py y que ambos importen desde services.py
→ Solo permitida la importación lazy dentro de función (dentro del cuerpo) si es por dependencia circular confirmada
→ Documentar explícitamente por qué es lazy en un comentario inline

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

SQLite (entorno de pruebas unitarias / scripts puntuales)

PostgreSQL (DEV y PROD — ambos en Railway)

Nota: el bot DEV corre en Railway (rama staging) con PostgreSQL. No hay ejecución local del bot.
SQLite solo se usa como fallback en tests o herramientas de diagnóstico sin DATABASE_URL.

Reglas obligatorias

La selección de motor se determina exclusivamente por:

DATABASE_URL presente → PostgreSQL

DATABASE_URL ausente → SQLite (solo para pruebas locales sin Railway)

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

Ambiente (DEV/PROD)

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

4B. Regla obligatoria de expiración sin penalidad

Cuando un pedido o una ruta se cancela automáticamente porque se agotó la ventana de respuesta del mercado
(por ejemplo: nadie aceptó / nadie respondió dentro del tiempo configurado del flujo),
NO debe aplicarse penalidad a ningún actor.

Esto incluye:
- aliado
- admin creador de pedido especial
- repartidor

Reglas:
- La cancelación automática por falta de respuesta SIEMPRE se considera sin culpa de los actores.
- El mensaje al creador del servicio DEBE dejar explícito que no se aplicó ningún cargo.
- PROHIBIDO reutilizar motores de cancelación con penalidad para expiraciones automáticas de mercado.

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

5B. Regla obligatoria de auditoría transversal de flujos

Cuando se cree o cambie un flujo nuevo, el agente DEBE revisar explícitamente si esa misma lógica aplica
también a otros flujos equivalentes ya existentes.

Objetivo:
- mantener uniformidad operativa entre flujos que representan la misma regla de negocio
- evitar que una mejora quede implementada solo en un flujo y no en los demás
- privilegiar un mismo motor lógico con adaptadores mínimos por flujo

Obligaciones mínimas:
- auditar los flujos hermanos antes de cerrar el cambio
- identificar cuáles quedan cubiertos, cuáles no aplican y cuáles requieren adaptación
- si la regla sí aplica a varios flujos, implementarla de forma uniforme en el mismo ciclo o dejar explícita la brecha y su razón
- reutilizar helpers, servicios o motores existentes antes de duplicar lógica

Ejemplos típicos de auditoría transversal:
- pedido de aliado
- pedido especial de admin
- ruta multi-parada
- panel admin vs panel aliado vs callbacks del courier

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

python -m py_compile Backend/main.py Backend/services.py Backend/db.py Backend/order_delivery.py Backend/profile_changes.py

Si el cambio introduce una constante nueva usada por 2 o mÃ¡s handlers o flujos:
- DEBE declararse explÃ­citamente en el bloque global de constantes del archivo, o exponerse desde services.py
- PROHIBIDO usar nombres de constantes nuevos en handlers sin verificar primero con `rg` todos sus usos y su definiciÃ³n

Si el cambio toca un flujo crÃ­tico (registro, aprobaciÃ³n, recargas, pagos, cotizador, pedidos):
- NO basta con `py_compile`
- DEBE verificarse el paso exacto afectado del flujo en `staging` o dejar una evidencia visible de diagnÃ³stico (mensaje debug, marcador de versiÃ³n o log verificable) antes de dar el cambio por resuelto

Verificar imports huérfanos tras mover o eliminar funciones:
Para cada nombre movido o eliminado, ejecutar:
git grep "nombre_funcion" -- "*.py"
Si solo aparece en el bloque import y en ningún otro lugar → el import es huérfano y debe eliminarse.

Reportar claramente:

qué cambió

qué se eliminó

por qué

7. Git y ramas

Nunca trabajar directamente sobre main, excepto cuando el usuario lo ordene explÃ­citamente para promover trabajo ya integrado en staging hacia main (merge staging â†’ main y push a origin/main), siempre que no viole la regla 7B.

Confirmar siempre la rama activa antes de modificar código.

REGLA OPERATIVA (NUEVA, OBLIGATORIA):

Siempre se trabaja sobre la rama staging.

Todo commit y push del trabajo se hace directamente a origin/staging.

Las ramas temporales `verify/*` o `claude/*` pueden usarse cuando se necesite aislar una validación puntual,
pero NO son obligatorias para cambios estructurales de base de datos.

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

Implementarse y validarse en staging por defecto.

Usar rama verify/* solo si el usuario lo pide explícitamente o si hace falta aislar una validación puntual.

Desplegarse en entorno de prueba

Validarse con:

arranque limpio

operaciones reales

persistencia tras redeploy

Solo después puede mergearse a main.

PROHIBIDO promover a main un cambio de base de datos sin validación funcional previa en staging.

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

7D. Ramas protegidas y ramas de colaboradores

Las siguientes ramas son PERMANENTES y NUNCA deben borrarse:

- main       → producción (Railway PROD). NUNCA trabajar directamente aquí.
- staging    → rama de trabajo e integración. Aquí se desarrolla, se hace commit y se hace push.
- luisa-web  → rama de trabajo de la colaboradora Luisa (activa).

Flujo oficial de ramas:

  staging   ──(validado)──►  main
  verify/*  ──merge──►  staging  ──(validado)──►  main
  (opcional)
                         (entorno DEV:
                          BOT_TOKEN DEV
                          DATABASE_URL separada)

Reglas de flujo:
- PROHIBIDO mergear verify/* directamente a main sin pasar por staging.
- verify/* es opcional y solo se usa si hace falta aislar una validación puntual.
- Un cambio puede ir de staging a main solo cuando fue validado funcionalmente en staging.
- staging debe mantenerse al día con origin/staging.

Regla general para ramas de colaboradores:
- PROHIBIDO borrar ramas cuyo nombre no sea del prefijo claude/ o verify/
- Antes de borrar cualquier rama, verificar que pertenece a un agente IA o es una rama temporal propia
- En caso de duda, preguntar al usuario antes de borrar

Cómo identificar ramas seguras para borrar:
1. Ejecutar: git branch -r --merged origin/staging
2. Solo borrar ramas con prefijo claude/ o verify/ que estén en esa lista
3. NUNCA borrar ramas que no tengan esos prefijos sin confirmación explícita del usuario

7E. Regla de compatibilidad estructural antes de merge

PROHIBIDO hacer merge de una rama si su estructura de archivos no es compatible con main.

Señales de incompatibilidad estructural:
- La rama tiene archivos en el directorio raíz que en main están en Backend/
- La rama tiene archivos en Backend/ que en main están en el raíz
- La rama tiene paths diferentes para los mismos archivos lógicos

Procedimiento obligatorio antes de hacer merge:
1. Verificar que la rama fue creada a partir de origin/main (no de una versión antigua)
   git log --oneline origin/main..nombre-rama
2. Comparar la estructura de archivos clave:
   git diff origin/main nombre-rama -- --name-only
3. Si los paths difieren → ABORTAR el merge con git merge --abort

Procedimiento cuando hay incompatibilidad estructural:
1. Abortar: git merge --abort
2. Crear nueva rama desde origin/main: git checkout -b claude/apply-[nombre]-[ID] origin/main
3. Analizar los commits de la rama incompatible uno por uno: git show [hash]
4. Aplicar los cambios manualmente sobre los paths correctos de main
5. Verificar compilación: python -m py_compile Backend/main.py Backend/services.py Backend/db.py
6. Commitear y mergear normalmente

Regla de creación de ramas:
Toda nueva rama de trabajo DEBE crearse desde origin/main actualizado:
  git fetch origin
  git checkout -b claude/[nombre]-[ID] origin/main

PROHIBIDO crear ramas desde branches locales sin sincronizar o desde ramas que no sean origin/main.

8. Reglas específicas para agentes tipo Codex

Codex NO improvisa.

Debe:

Preguntar ante ambigüedad

Trabajar solo en el objetivo indicado

Mostrar evidencia si ejecuta comandos

9. Reglas del sistema de recargas (CRÍTICAS)

El sistema de recargas transfiere saldo del Admin hacia Repartidores/Aliados. Es el componente financiero más crítico del sistema.

Reglas de integridad:

Toda aprobación/rechazo de recarga DEBE ser idempotente.

PROHIBIDO aprobar o rechazar dos veces la misma solicitud.

En concurrencia (approve vs reject simultáneos), solo una operación gana.

Toda operación de recarga DEBE generar un registro en el ledger.

La actualización de balance y el registro en ledger deben ser atómicos (misma transacción).

Estados de recarga:

PENDING → APPROVED: balance transferido, ledger registrado.

PENDING → REJECTED: balance no cambia, ledger no registra movimiento.

APPROVED / REJECTED → estado terminal. PROHIBIDO cambiar a otro estado.

Reglas de validación:

Solo el Admin propietario del balance puede aprobar una recarga a su equipo.

PROHIBIDO modificar el balance de un admin sin registro en ledger.

Los estados de recarga usan normalize_role_status() antes de persistir.

Verificación obligatoria antes de aprobar:

Verificar que el estado sigue siendo PENDING (con SELECT FOR UPDATE en Postgres).

Si el estado ya cambió: retornar (False, "Ya procesado") sin modificar nada.

9B. Modelo de contabilidad de doble entrada (CRÍTICO)

El sistema implementa contabilidad de doble entrada. PROHIBIDO crear saldo de la nada.

Principio fundamental:

El Admin de Plataforma NO tiene saldo ilimitado ni exento de validación.

Para aprobar recargas, el Admin de Plataforma debe tener balance suficiente en admins.balance.

Para tener balance, el Admin de Plataforma DEBE registrar ingresos externos explícitamente.

Flujo de fondos obligatorio:

  Pago físico/transferencia del cliente
    → register_platform_income(admin_id, amount, method, note)
    → admins.balance sube en amount
    → ledger registra: kind=INCOME, from_type=EXTERNAL, from_id=0, to_type=PLATFORM/ADMIN

  Admin aprueba recarga a repartidor o aliado
    → admins.balance baja en amount
    → admin_couriers.balance o admin_allies.balance sube en amount
    → ledger registra: kind=RECHARGE, from_type=PLATFORM/ADMIN, from_id=admin_id, to_type=COURIER/ALLY

PROHIBIDO:

- Eximir al Admin de Plataforma de la verificación de balance antes de aprobar recargas.
- Aprobar una recarga si admins.balance < amount (sin importar si el admin es de plataforma o local).
- Registrar un ingreso sin generar su entrada correspondiente en ledger.
- Modificar el balance de cualquier actor sin registro simultáneo en ledger.

Función de ingreso externo (db.py → register_platform_income):

- Parámetros: admin_id, amount, method, note
- Llama internamente a update_admin_balance_with_ledger()
- Genera ledger con: kind="INCOME", from_type="EXTERNAL", from_id=0
- Re-exportada en services.py e importada en main.py desde services.py

Flujo de UI del ingreso externo (ConversationHandler ingreso_conv en main.py):

- Estados: INGRESO_MONTO=970, INGRESO_METODO=971, INGRESO_NOTA=972
- Prefijo de callbacks: ingreso_
- Claves de user_data: ingreso_monto, ingreso_metodo
- Accesible desde: menu Finanzas del Admin de Plataforma

9D. Recarga directa con plataforma como fallback (CRÍTICO)

Un aliado o repartidor puede siempre solicitar recarga directamente al Admin de Plataforma,
aunque pertenezca a un equipo de Admin Local.

Casos habilitados:
1. El Admin Local no tiene saldo suficiente para recargar.
2. El Admin Local no responde o no procesa la recarga.

Regla del interruptor de ganancias:

  El saldo recargado pertenece a quien lo aportó.
  Las ganancias generadas por ese saldo fluyen hacia el mismo aportante.

  Si el aliado/repartidor recargó con Admin Local → ganancias al Admin Local.
  Si el aliado/repartidor recargó con Plataforma   → ganancias a Plataforma.

  Al agotarse el saldo de plataforma y recargar nuevamente con el Admin Local,
  el flujo de ganancias vuelve automáticamente al Admin Local.

Consecuencia para el Admin Local:
  El Admin Local que no recarga a tiempo pierde las ganancias generadas por ese
  usuario mientras su saldo recargado provenga de la plataforma. Recupera las
  ganancias cuando el usuario vuelva a recargar con él.

PROHIBIDO:
  - Bloquear la opción de recarga con plataforma si el courier/ally pertenece a un Admin Local.
  - Asumir que platform solo aparece como opción cuando tiene vínculo APPROVED en admin_couriers/admin_allies.
  - Aprobar la recarga de plataforma si admins.balance (plataforma) < amount.

Implementación técnica (IMPLEMENTADO 2026-03-03):
  - UI (main.py → recargar_monto): mostrar "Plataforma" siempre, sin verificar vínculo APPROVED.
  - Validación (main.py → recargar_admin_callback): permitir platform_id aunque no esté en approved_links.
  - Aprobación (services.py → approve_recharge_request): cuando el aprobador es plataforma,
    crea o actualiza un vínculo directo admin_couriers/admin_allies con admin_id=platform_id y
    lo pone APPROVED. Todos los demás vínculos del courier/ally quedan INACTIVE (interruptor).
    Cuando un Admin Local aprueba después: su vínculo pasa a APPROVED, el de plataforma a INACTIVE.
  - Determinación de vínculo activo: _sync_courier_link_status y _sync_ally_link_status usan
    updated_at DESC (no created_at) para identificar el vínculo más reciente como APPROVED.
  - Ledger: registrar siempre PLATFORM → COURIER/ALLY para trazabilidad del origen del saldo.

9E. Red cooperativa — elegibilidad de couriers (CRÍTICO)

La plataforma opera como red cooperativa: cualquier courier activo puede tomar pedidos de
cualquier aliado, sin importar a qué admin pertenece cada uno. NO existen equipos aislados
para el despacho de pedidos.

PROHIBIDO:
  - Filtrar couriers elegibles por admin_id del aliado en get_eligible_couriers_for_order.
  - Cancelar un dispatch completo porque el admin de un courier no tiene saldo (ADMIN_SIN_SALDO
    de un courier solo excluye ESE courier, no cancela la oferta a otros).
  - Usar el admin del aliado para cobrar el fee del courier (y viceversa).

Regla de elegibilidad:
  get_eligible_couriers_for_order NO recibe ni aplica admin_id como filtro.
  Retorna todos los couriers con admin_couriers.status = 'APPROVED' y couriers.status = 'APPROVED'.

Regla de comisiones (simétrica):
  - Fee del aliado ($300): admin del aliado recibe $200, Plataforma recibe $100.
    Admin se determina con get_approved_admin_link_for_ally.
  - Fee del courier ($300): admin del courier recibe $200, Plataforma recibe $100.
    Admin se determina con order.courier_admin_id_snapshot (guardado al aceptar).
    Fallback: get_approved_admin_link_for_courier si el snapshot es NULL.
  - Si el admin es Plataforma gestionando su PROPIO equipo: el ledger debe registrar
    fee_admin_share como kind=FEE_INCOME (ganancia personal del administrador de plataforma)
    y fee_platform_share como kind=PLATFORM_FEE (ganancia de la sociedad inversora).
    PROHIBIDO registrar todo como FEE_INCOME cuando el admin es Plataforma.
  - Si el admin es Admin Local: fee_admin_share → FEE_INCOME del admin local, fee_platform_share → PLATFORM_FEE.
  - Pedidos de admin (creator_admin_id != NULL, ally_id = NULL):
    el admin creador NO paga fee. El courier que entrega sí paga su fee normal.
    _expire_order con ally_id=None no cobra ni crashea (guard implementado).
  - Cada admin gana únicamente de sus propios miembros.
  - Si el aliado tiene suscripción activa (check_ally_active_subscription(ally_id) == True):
    NO se cobra fee al aliado (ni fee_service_total ni fee_ally_commission_pct).
    El courier sigue pagando su fee normal. PROHIBIDO cobrar fee a aliado suscrito.

Regla de pre-verificación de saldo (publish_order_to_couriers):
  Para cada courier elegible, llamar get_approved_admin_id_for_courier(courier_id) y verificar
  check_service_fee_available(COURIER, courier_id, courier_admin_id) de forma individual.
  Si un courier falla: se excluye solo él. El dispatch continúa con los demás.

Implementado en (2026-03-03):
  - db.py → get_eligible_couriers_for_order: sin filtro AND ac.admin_id, params = []
  - order_delivery.py → publish_order_to_couriers: fee check con admin propio de cada courier
  - order_delivery.py → _handle_delivered: ally_admin_id y courier_admin_id separados

9C. Sincronización obligatoria de estado en tablas de vínculo

Las tablas admin_allies y admin_couriers tienen su propio campo status, independiente del campo status en allies y couriers. Ambos DEBEN mantenerse sincronizados.

PROHIBIDO actualizar allies.status o couriers.status sin actualizar también el status correspondiente en admin_allies o admin_couriers.

Helpers obligatorios en db.py:

_sync_ally_link_status(cur, ally_id, status, now_sql)
  → Se llama dentro de update_ally_status() y update_ally_status_by_id(), antes de conn.commit()
  → Si status == "APPROVED": el vínculo más reciente pasa a APPROVED, el resto a INACTIVE
  → Si status != "APPROVED": todos los vínculos del aliado pasan a INACTIVE

_sync_courier_link_status(cur, courier_id, status, now_sql)
  → Se llama dentro de update_courier_status() y update_courier_status_by_id(), antes de conn.commit()
  → Misma lógica que el helper de aliados, aplicada a admin_couriers

Regla de UI en main.py:

Cuando el callback de aprobación de aliado o repartidor (ally_approval_callback, etc.) crea o reutiliza un vínculo mediante upsert_admin_ally_link() o upsert_admin_courier_link(), debe pasarlo con status="APPROVED" explícito.

Síntoma del bug si no se respeta: "No hay admins disponibles para procesar recargas" al intentar recargar un aliado o repartidor recién aprobado.

X. Cotizador y uso de APIs (CRÍTICO: control de costos)

El cotizador usa la API de Google Maps (Distance Matrix / Places) para calcular distancias y geocodificar direcciones.

Regla de cuota diaria:

PROHIBIDO llamar a la API de Google Maps sin verificar api_usage_daily primero.

Si api_usage_daily >= límite configurado: retornar error informativo, NO llamar a la API.

Toda llamada a la API DEBE incrementar api_usage_daily en la misma operación (atómico).

Regla de costeo (IMPLEMENTADO):

- Toda llamada real a Google Maps (Distance Matrix / Geocode / Places) DEBE registrarse también como evento en api_usage_events (para conteo y costo promedio por operación).
- La función oficial para registrar es record_api_usage_event() en Backend/db.py (hace INSERT en api_usage_events + incrementa api_usage_daily en la misma transacción).
- PROHIBIDO guardar PII (direcciones completas, teléfonos, nombres, coordenadas) en meta_json de api_usage_events. Solo metadata no sensible (status, provider, mode).
- La estimación de costo por operación se configura por variables de entorno:
  - GOOGLE_COST_USD_PLACE_DETAILS
  - GOOGLE_COST_USD_GEOCODE_FORWARD
  - GOOGLE_COST_USD_PLACES_TEXT_SEARCH
  - GOOGLE_COST_USD_DISTANCE_MATRIX_COORDS
  - GOOGLE_COST_USD_DISTANCE_MATRIX_TEXT

Regla de caché:

Los resultados de distancia entre pares de coordenadas DEBEN cachearse.

PROHIBIDO recalcular una distancia ya cacheada para la misma consulta.

El caché vive en base de datos (tabla settings o equivalente).

Regla de geocodificación:

Las coordenadas de usuarios (lat/lng) se capturan vía Telegram (compartir ubicación GPS).

La API solo se usa para geocodificación inversa o búsqueda de direcciones escritas.

PROHIBIDO usar la API para validar ubicaciones que ya tienen coordenadas GPS válidas.

Regla global de resolución de ubicación por texto (OBLIGATORIA):

Todo flujo que capture ubicaciones por texto (cotizar, pedido, pickup, ruta u otros) DEBE usar el mismo pipeline funcional de cotización:

1. resolve_location(texto) como resolvedor principal.
2. Si method == "geocode" con formatted_address, mostrar confirmación (si/no) antes de persistir coordenadas.
3. Si el usuario rechaza, intentar siguiente candidato con resolve_location_next(...); si no hay más, pedir GPS.

PROHIBIDO implementar parseos ad-hoc de links/direcciones que omitan este pipeline en nuevos puntos de captura.

Regla de errores:

Si la API falla (timeout, error de red, cuota agotada): el cotizador retorna error claro al usuario.

PROHIBIDO propagar excepciones de la API sin capturar.

PROHIBIDO reintentar automáticamente sin informar al usuario.

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

13. Sistema de Tracking de Llegada (Pedidos)

Implementado en: order_delivery.py + main.py + db.py

13A. Protección de datos del cliente

PROHIBIDO revelar customer_name, customer_phone ni customer_address al repartidor en _handle_accept o en cualquier momento antes de que el aliado confirme la recogida.

Durante la oferta (pedido publicado / aún sin confirmación de recogida) SÍ está permitido mostrar únicamente:

- Mapas (PINs de Telegram) de recogida y entrega usando coordenadas ya guardadas.
- Ciudad + barrio/sector de recogida y entrega (sin dirección exacta).

El único lugar donde se revelan al repartidor la dirección exacta y los detalles del cliente (nombre/teléfono/dirección) es _notify_courier_pickup_approved (order_delivery.py), llamada tras la confirmación del aliado.

13B. Timers post-aceptación (obligatorios)

Al aceptar un pedido se programan SIEMPRE 3 jobs con job_queue.run_once:

arr_inactive_{order_id} — T+5 min: si el repartidor no se movió ≥50m hacia el pickup → liberar y re-ofrecer.
arr_warn_{order_id}    — T+15 min: notificar al aliado con opciones (buscar otro / llamar / esperar) y advertir al repartidor.
arr_deadline_{order_id} — T+20 min: liberar automáticamente y re-ofrecer.

PROHIBIDO programar solo algunos timers; se programan los 3 juntos o ninguno.

Los 3 jobs deben cancelarse explícitamente (via _cancel_arrival_jobs) en:
- _handle_release (repartidor libera manualmente)
- _handle_delivered (entrega exitosa)
- _handle_cancel_ally (aliado cancela)
- check_courier_arrival_at_pickup (GPS detecta llegada)
- _handle_find_another_courier (aliado solicita otro repartidor)

PROHIBIDO agregar nuevas rutas de exit al flujo de pedido sin llamar _cancel_arrival_jobs.

13C. Detección de llegada por GPS

check_courier_arrival_at_pickup(courier_id, lat, lng, context) en order_delivery.py se llama desde courier_live_location_handler en main.py en CADA actualización de live location.

Radio de llegada: ARRIVAL_RADIUS_KM = 0.1 (100 metros). PROHIBIDO cambiar este valor sin autorización.

PROHIBIDO marcar courier_arrived_at sin validación GPS (haversine_km ≤ ARRIVAL_RADIUS_KM). La función es idempotente: solo actúa si courier_arrived_at IS NULL.

Al detectar llegada: llama set_courier_arrived → _cancel_arrival_jobs → upsert_order_pickup_confirmation(PENDING) → _notify_ally_courier_arrived.

13D. Liberación por timeout

_release_order_by_timeout(order_id, courier_id, context, reason) centraliza la lógica de liberación automática. PROHIBIDO duplicar esta lógica.

Al liberar: cancela jobs, llama release_order_from_courier, agrega al courier a excluded_couriers en offer_cycles, notifica courier y aliado, reinicia ciclo de ofertas excluyendo al courier liberado.

13E. Posición al momento de aceptar

En _handle_accept se guarda la posición actual del repartidor en courier_accepted_lat / courier_accepted_lng (tabla orders). Esta posición es la base para el chequeo de inactividad en T+5.

PROHIBIDO usar residence_lat/lng como sustituto permanente; solo se usa como fallback si live_lat/lng no está disponible.

13F. Compatibilidad SQLite/PostgreSQL en funciones nuevas

PROHIBIDO usar .get() en objetos Row de la base de datos. Usar siempre _row_value(row, key) definido en order_delivery.py. sqlite3.Row no implementa .get(); RealDictRow de psycopg2 sí, pero el código debe ser compatible con ambos motores.

Excepción permitida: cuando db.py retorna explícitamente dict(row) (por ejemplo get_ally_by_public_token), el resultado ya es un dict Python y row["key"] es seguro. Aun así PROHIBIDO usar .get() — usar row["key"] con fallback explícito (ej. row["key"] or 0) para que el comportamiento ante NULL sea visible en el código.

REGLA ADICIONAL — SELECT debe incluir todas las columnas que el caller necesite:
Antes de usar row["columna"] en cualquier función que recibe un dict de BD, verificar que la query SELECT que lo produjo incluye esa columna. Si la columna existe en la tabla pero no está en el SELECT, row["columna"] lanza KeyError. Toda nueva columna de negocio agregada a una tabla (ej. delivery_subsidy en allies) debe añadirse explícitamente al SELECT de todas las funciones que retornan esa entidad.

REGLA ADICIONAL — Validación de enumerados en endpoints públicos:
Los endpoints FastAPI que aceptan campos con valores restringidos (ej. incentivo_cliente ∈ {0, 1000, 2000, 3000}) deben validar en backend con HTTPException 422 aunque la UI solo ofrezca esos valores. El backend no puede confiar en que el cliente siempre envíe datos correctos. Patrón obligatorio:
  ALLOWED = {0, 1000, 2000, 3000}
  value = body.field if body.field is not None else 0
  if value not in ALLOWED:
      raise HTTPException(status_code=422, detail=f"field debe ser uno de {sorted(ALLOWED)}.")

REGLA ADICIONAL — El backend es la fuente de verdad de precios y cálculos financieros:
PROHIBIDO usar valores de precio o cotización enviados por el cliente (body.quoted_price, body.total, etc.) como fuente de verdad para persistencia o cálculo financiero. El backend debe recalcular siempre el precio usando sus propias funciones (quote_order_by_coords, calcular_precio_distancia, etc.) a partir de los datos geográficos recibidos. Los campos de precio en el payload del cliente pueden mantenerse por compatibilidad de UI pero deben ignorarse en la lógica de negocio. Si el recálculo no es posible (falta de coordenadas, fallo de API), persistir los campos de cotización como NULL — nunca usar el valor enviado por el cliente como fallback.

13G. Pendientes (NO implementado aún)

- Cuenta regresiva visible (countdown) post-aceptación.
- Botón explícito "Llegué" del courier (hoy es auto-detección por live location).
- Persistencia ante reinicios: jobs T+5/T+15/T+20 y exclusión de couriers del ciclo viven en memoria.

14. Reglas de escritura de archivos con herramientas de IA

14A. Cuando el tool Edit no persiste los cambios

Sintoma: Edit reporta exito pero git diff no muestra el cambio, o el archivo vuelve a su estado original.
Causa comun: linter del IDE o servidor de lenguaje revierte el archivo inmediatamente despues de guardarlo.

Procedimiento obligatorio al detectar este problema:
1. Verificar con git diff que el cambio no esta presente.
2. Usar un script Python via Bash para escribir el archivo directamente:
   python3 << 'EOF'
   path = 'ruta/al/archivo.py'
   with open(path, 'r', encoding='utf-8') as f:
       content = f.read()
   content = content.replace(viejo_bloque, nuevo_bloque, 1)
   with open(path, 'w', encoding='utf-8') as f:
       f.write(content)
   EOF
3. Verificar con grep que el cambio persiste.
4. Ejecutar python -m py_compile para confirmar compilacion.

PROHIBIDO reintentar Edit indefinidamente si el patron de reversion es claro.
Cambiar de estrategia al tercer intento fallido.

14B. Escritura de secuencias de escape en archivos Python via bash

Problema: al escribir un archivo Python usando heredoc (<< 'PYEOF') o python3 -c "...",
la secuencia backslash-n dentro de strings Python se convierte en un salto de linea real
en lugar de quedar como los dos caracteres backslash + n que Python necesita interpretar
como escape de nueva linea.

Ejemplo del problema (INCORRECTO):
    line = '    text = "hola
world"'  # en heredoc 
 se convierte en newline real

Solucion obligatoria: usar chr(92) para construir el caracter backslash:
    bs = chr(92)       # chr(92) = backslash
    n_esc = bs + 'n'   # produce el escape 
 correcto en el archivo

Ejemplo correcto:
    bs = chr(92)
    n_esc = bs + 'n'
    line = '    text = "hola' + n_esc + 'world"'  # escribe hola
world correctamente

Esta regla aplica a CUALQUIER caracter de escape Python que deba aparecer en el archivo
generado: 	, 
, 
, \, etc.

PROHIBIDO usar secuencias de escape directas (
, 	) dentro de strings Python cuando
el objetivo es escribir esas secuencias literalmente en otro archivo Python.

14C. Funcion importada en handler pero nunca definida en services.py

Sintoma (detectado 2026-03-26):
    ImportError: cannot import name 'save_confirmed_geocoding' from 'services'
    El bot no arranca. El error aparece al iniciar main.py.

Causa:
    Un commit agrego una llamada a una funcion nueva (save_confirmed_geocoding) en
    handlers/order.py y la incluyo en el bloque import from services, pero nunca
    creo la funcion en services.py ni en db.py.
    El error solo se descubre al intentar correr el bot, no en py_compile del archivo
    que la llama (porque py_compile no resuelve imports dinamicamente).

Por que py_compile no lo detecta:
    python3 -m py_compile handlers/order.py no falla porque solo verifica sintaxis.
    El ImportError ocurre en tiempo de ejecucion cuando Python resuelve los imports.
    Para detectarlo hay que compilar main.py, que importa order.py transitivamente,
    o correr el bot directamente.

Correccion aplicada:
    Se definio save_confirmed_geocoding en services.py como wrapper de
    upsert_geocoding_text_cache (ya existia), guardando con source="confirmed".
    La funcion acepta (text, lat, lng) y falla silenciosamente si los parametros
    son invalidos (patron estandar del proyecto para operaciones de cache).

Regla preventiva obligatoria:
    Antes de agregar una funcion al bloque import from services en cualquier handler,
    verificar que existe:
        git grep "def nombre_funcion" -- "*.py"
    Si no aparece en services.py o db.py -> crearla antes de importarla.
    NUNCA importar una funcion que no existe aun.

Verificacion correcta para detectar este tipo de error antes de push:
    python3 -c "import sys; sys.path.insert(0, 'Backend'); import main"
    (este comando si resuelve los imports y falla si falta alguna funcion)


14D. sqlite3.Row no tiene metodo .get() — usar acceso directo por clave

Sintoma (detectado 2026-03-26):
    AttributeError: 'sqlite3.Row' object has no attribute 'get'
    El handler lanza excepcion silenciosa: el bot responde al callback (boton deja de girar)
    pero no realiza ninguna accion visible para el usuario ("no pasa nada").

Causa:
    Las funciones de db.py retornan sqlite3.Row en SQLite y RealDictRow en PostgreSQL.
    sqlite3.Row NO tiene el metodo dict.get(key, default).
    Solo soporta acceso por indice: row["key"] o row[0].
    Codigo incorrecto: admin_row.get("telegram_id")   <- AttributeError en SQLite
    Codigo correcto:   admin_row["telegram_id"]        <- funciona en SQLite y Postgres

Comportamiento de acceso directo en ambos motores:
    - sqlite3.Row["key"]: retorna None si el valor en la BD es NULL. No lanza KeyError.
    - RealDictRow["key"]: igual, retorna None si el valor es NULL.
    El comportamiento es equivalente a dict.get(key) — sin necesidad del metodo .get().

Por que es dificil de detectar:
    - py_compile no lo detecta (error de atributo en tiempo de ejecucion, no de sintaxis).
    - El error ocurre DESPUES de query.answer(): el boton deja de girar (parece que funciono)
      pero la accion no se completa. El usuario ve que "no pasa nada".
    - Solo falla en SQLite (desarrollo local). En PostgreSQL RealDictRow SI tiene .get(),
      por lo que el bug puede pasar desapercibido si solo se prueba en Railway.

Regla preventiva obligatoria:
    NUNCA usar .get() en objetos retornados por funciones de db.py.
    Usar siempre acceso directo: row["columna"].
    Si se necesita un valor por defecto: row["columna"] or valor_default

Casos corregidos en barrido completo (2026-03-26):
    handlers/registration.py    — ally_team_callback, courier_team_callback
    services.py                 — approve_role_registration, liquidate_route_additional_stops_fee,
                                  check_user_can_quote (actor_admin, target, ally, courier, route)
    handlers/recharges.py       — bloque de aprobacion local (ally fields)
    handlers/config.py          — admin["role"]
    handlers/location_agenda.py — loc fields en listado y detalle
    handlers/order.py           — ubicaciones, alias, estado del aliado
    handlers/route.py           — paradas y rutas
    handlers/customer_agenda.py — clientes y direcciones
    handlers/admin_panel.py     — admins y pendientes
    order_delivery.py           — ~24+ ocurrencias: ally_user, courier_user, route,
                                  order, courier, stop, dest, pickup_loc_row
    main.py                     — varios objetos de BD
    handlers/common.py          — ally["status"] en get_main_menu_keyboard (fallaba en /start)
                                  (omitido del primer barrido — archivo no estaba en la lista)

Leccion adicional: el barrido debe incluir TODOS los archivos del Backend, no solo los handlers
listados en CLAUDE.md. Verificar siempre con:
    grep -rn "\.get(" Backend/ --include="*.py" | grep -v "user_data\|requests\.\|geo\.\|json\.\|isinstance"

Excluidos del barrido (estos .get() son seguros):
    - context.user_data.get(...)        — siempre es dict de Python
    - geo.get(), cotizacion.get()       — dicts retornados por funciones de geocodeo
    - response.get(), route.get()       — dicts de requests/OSRM
    - p.get("lat"), p.get("lng")        — paradas de user_data (dicts)
    - bloques con isinstance(obj, dict) — ya tienen guard correcto


14E. query.answer() prematuro silencia alertas en callbacks

Sintoma:
    El boton de Telegram deja de girar (parece que funciono) pero no aparece ningun mensaje de error.
    El usuario ve que "no pasa nada". El error de negocio ocurrio pero fue silenciado.

Causa:
    Telegram solo permite llamar query.answer() UNA sola vez por callback query.
    Si se llama query.answer() al inicio del handler (patron comun para desactivar el spinner)
    y luego se intenta llamar query.answer("mensaje de error", show_alert=True) en un caso de error,
    la segunda llamada es silenciosamente ignorada por la API de Telegram.

    Patron incorrecto:
        def mi_callback(update, context):
            query = update.callback_query
            query.answer()                          # <- primer answer: OK
            ...
            if error:
                query.answer("Error", show_alert=True)  # <- IGNORADO por Telegram
                return

    Patron correcto:
        def mi_callback(update, context):
            query = update.callback_query
            if error_temprano:
                query.answer("Error", show_alert=True)  # <- unico answer, muestra alerta
                return
            ...
            query.answer()                          # <- answer al exito (una sola vez)
            query.edit_message_text("Exito")

Regla obligatoria:
    NUNCA llamar query.answer() al inicio de un handler si ese handler puede necesitar
    mostrar show_alert=True en rutas de error. Llamar query.answer() SOLO UNA VEZ,
    al final del camino exitoso. Los caminos de error llaman query.answer(msg, show_alert=True)
    directamente como su unico answer.

Detectado en (2026-03-26):
    handlers/recharges.py — ally_approval_callback: query.answer() en linea 2119 silenciaba
    todos los mensajes de error de approve_role_registration y validaciones previas.
    Fix: eliminar query.answer() prematuro; agregar query.answer() justo antes de
    query.edit_message_text() en el camino exitoso.


14F. Admin Plataforma debe poder aprobar cualquier aliado o repartidor pendiente

Regla de negocio:
    El Admin de Plataforma es el administrador global del sistema. Puede aprobar o rechazar
    CUALQUIER aliado o repartidor pendiente, sin importar a que equipo de admin local
    haya sido asignado ese usuario durante su registro.

Error corregido (2026-03-26):
    services.py — approve_role_registration: existia un bloqueo que impedia al admin plataforma
    aprobar registros cuyo selected_admin_id difiriera del propio admin_id de plataforma.
    El mensaje de error ("La aprobacion operativa debe hacerla ese admin") nunca era visible
    porque ademas estaba silenciado por el query.answer() prematuro (ver 14E).

    Codigo eliminado:
        if is_platform_actor:
            if selected_admin_id != actor_admin_id:
                return {"ok": False, "message": "..."}

    Comportamiento correcto:
        - Admin Plataforma: puede aprobar cualquier registro PENDING (sin restriccion de equipo).
        - Admin Local: solo puede aprobar registros de su propio equipo (restriccion intacta).

    Al aprobar, el link se crea bajo el selected_admin_id original (el equipo que el usuario eligio),
    no bajo el admin_id de plataforma. Esto preserva la asignacion de equipo correcta.


15. Colaboración entre agentes IA (Claude Code y Codex)

Luis Felipe trabaja en VS Code con múltiples agentes activos simultáneamente: Claude Code y Codex.
En ocasiones ambos agentes trabajan al mismo tiempo sobre la misma rama (staging).
Estas reglas garantizan la armonia del codigo y que ningun agente deshaga el trabajo del otro.

15A. Registro obligatorio — WORKLOG.md

Existe el archivo WORKLOG.md en la raiz del repositorio. Es el mecanismo principal de coordinacion.

Al INICIAR una sesion de trabajo:
  1. git pull origin staging  (traer cambios antes de empezar).
  2. Leer git log --oneline -15 origin/staging para ver que hizo el otro agente recientemente.
  3. Leer WORKLOG.md para detectar sesiones activas del otro agente.
  4. Agregar una entrada en la seccion "Sesiones activas" de WORKLOG.md con:
     - Agente (claude / codex)
     - Fecha y hora de inicio
     - Archivos que se van a modificar
     - Descripcion breve de la tarea
  5. Commit + push del WORKLOG: "[claude] worklog: inicio — <tarea breve>"

Al FINALIZAR una sesion de trabajo:
  1. Mover la entrada de "Sesiones activas" a "Historial reciente" en WORKLOG.md con estado COMPLETADO o PENDIENTE.
  2. Commit + push del WORKLOG: "[claude] worklog: cierre — <tarea breve>"

PROHIBIDO iniciar trabajo sin actualizar WORKLOG.md primero.
PROHIBIDO olvidar cerrar la entrada al terminar la sesion.

15B. Prefijo obligatorio en commits

Todo commit generado por un agente IA DEBE comenzar con el prefijo de su agente:
  - Claude Code: [claude] feat: ...
  - Codex:       [codex] feat: ...

El prefijo va siempre al inicio del titulo del commit, antes de feat/fix/docs/etc.
Adicionalmente, Claude Code incluye al pie: Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

Para filtrar commits por agente:
  git log --oneline --grep="[claude]"
  git log --oneline --grep="[codex]"

PROHIBIDO omitir el prefijo en cualquier commit generado por un agente IA.

15C. Reglas de no-interferencia (critico)

PROHIBIDO borrar, revertir o modificar cambios realizados por otro agente sin:
  1. Informar primero a Luis Felipe: que cambio del otro agente es problematico y por que.
  2. Esperar autorizacion explicita antes de actuar.

Si se detecta codigo defectuoso, conflicto o regresion introducida por otro agente:
  - PROHIBIDO corregirlo directamente.
  - Obligatorio reportar a Luis Felipe: archivo exacto, funcion, hash del commit, descripcion del problema.
  - Esperar instruccion explicita antes de tocar el codigo del otro agente.

15D. Protocolo ante solapamiento detectado

Si al leer WORKLOG.md o git log se detecta que el otro agente esta tocando los mismos archivos:
  1. PAUSAR la tarea actual.
  2. Notificar a Luis Felipe: "El agente X esta modificando <archivo> (ver WORKLOG.md o commit <hash>). Necesito instruccion antes de continuar."
  3. No continuar hasta recibir instruccion.

Si al hacer git push se recibe rechazo por fast-forward (el otro agente pusheo primero):
  - PROHIBIDO git push --force.
  - Hacer git pull, revisar los cambios del otro agente, y reportar a Luis Felipe si hay conflicto.

15E. Archivos de alto riesgo (zonas de conflicto)

Los siguientes archivos son modificados frecuentemente por ambos agentes.
Requieren especial atencion al verificar WORKLOG.md antes de editar:

  Backend/main.py          — orquestador central, handlers, flujos
  Backend/services.py      — logica de negocio y re-exports
  Backend/db.py            — acceso a base de datos
  Backend/order_delivery.py — flujo completo de pedidos
  AGENTS.md                — reglas del proyecto
  CLAUDE.md                — documentacion del proyecto

Para estos archivos: OBLIGATORIO leer git log --follow -5 <archivo> antes de editar.

15F. Objetivo

La coordinacion entre agentes pasa SIEMPRE por Luis Felipe.
Ningun agente tiene autoridad para resolver conflictos con otro agente por su cuenta.
El objetivo es que el trabajo de ambos agentes sume, nunca que uno deshaga al otro.

15G. Protocolo pre-push (obligatorio antes de cada git push)

Antes de ejecutar git push origin staging, el agente DEBE:

  1. Verificar si el otro agente pusheo mientras se trabajaba:
       git fetch origin staging
       git log --oneline HEAD..origin/staging

  2. Segun el resultado:

     a) Sin commits nuevos en origin/staging:
          → Push normal. No hay riesgo de solapamiento.

     b) Hay commits nuevos pero en archivos DISTINTOS a los que se modificaron:
          → git pull --ff-only origin staging
          → Verificar compilacion: python -m py_compile Backend/main.py Backend/services.py Backend/db.py Backend/order_delivery.py Backend/profile_changes.py
          → Push si todo compila.

     c) Hay commits nuevos en los MISMOS archivos que se modificaron:
          → PAUSAR. PROHIBIDO hacer push.
          → Reportar a Luis Felipe: "El agente X pusheo cambios en <archivo> mientras trabajaba.
             Mis cambios: <descripcion>. Sus cambios: <hash> <descripcion>.
             Necesito instruccion antes de pushear."
          → Esperar instruccion explicita.

 3. PROHIBIDO git push --force en cualquier circunstancia.

Comando rapido para detectar solapamiento de archivos:
  git diff --name-only HEAD origin/staging
  (compara contra los archivos que tu modificaste en esta sesion)

15H. Coherencia obligatoria entre DEV y PROD

Los bots de DEV y PROD deben mantenerse coherentes entre si en toda regla funcional visible
para usuarios, operadores o administradores.

Reglas:

1. Todo cambio en requisitos, validaciones, textos operativos, estados, botones o flujos del bot
   DEBE dejar consistentes entre si a staging (DEV) y main (PROD).
2. PROHIBIDO dar por terminada una tarea si el cambio deja a un bot con una regla y al otro con
   una distinta, salvo instruccion explicita de Luis Felipe.
3. Si un cambio modifica un requisito funcional, el agente DEBE actualizar en el mismo trabajo:
   - la logica real que valida el requisito
   - los textos del bot que lo describen
   - la documentacion normativa aplicable
4. Si por instruccion explicita el cambio queda solo en DEV, el agente DEBE reportarlo de forma
   textual y exacta como: "IMPLEMENTADO SOLO EN DEV; PROD sigue distinto por instruccion explicita."
5. Antes de promover staging a main, verificar especificamente que los archivos tocados para ese
   cambio reflejan la misma regla en ambos entornos.

16. Donde documentar (routing de documentacion)

Cuando Luis Felipe da la orden "documenta esto", el agente debe determinar el destino
correcto sin preguntar, usando esta tabla:

| Tipo de contenido                                              | Documento destino         |
|----------------------------------------------------------------|---------------------------|
| Regla obligatoria, restriccion, prohibicion, protocolo         | AGENTS.md                 |
| Leccion aprendida, solucion a problema tecnico recurrente      | AGENTS.md (seccion 14)    |
| Protocolo de coordinacion entre agentes IA                     | AGENTS.md (seccion 15)    |
| Arquitectura, estructura del proyecto, flujo, convencion       | CLAUDE.md                 |
| Sesion activa o cierre de sesion de un agente                  | WORKLOG.md                |
| Algo que es regla Y necesita detalle operativo / comandos      | AGENTS.md (regla) + CLAUDE.md (detalle) |

Reglas de aplicacion:

1. Si el contenido es una REGLA (algo que un agente debe o no debe hacer): va en AGENTS.md.
2. Si el contenido explica COMO funciona el sistema o como trabajar con el: va en CLAUDE.md.
3. Si un tema ya esta cubierto en AGENTS.md con detalle completo: CLAUDE.md solo agrega
   un parrafo de referencia o comandos practicos, nunca repite el contenido completo.
4. WORKLOG.md es exclusivo para registro de sesiones de agentes. No es un destino de documentacion general.
5. Si el contenido no encaja claramente en ningun documento: preguntar a Luis Felipe antes de documentar.

17. Documentar cambios estructurales (obligatorio en el mismo commit)

Todo cambio que agregue o modifique la estructura del proyecto DEBE documentarse
en el mismo commit que lo implementa. No en un commit posterior.

Tabla de routing estructural:

| Se agrega o modifica...                        | Actualizar en CLAUDE.md                        |
|------------------------------------------------|------------------------------------------------|
| Nueva tabla en la BD                           | Seccion "Tablas Principales"                   |
| Nueva columna relevante en tabla existente     | Seccion "Tablas Principales" (fila de la tabla)|
| Nuevo modulo .py en Backend/                   | Seccion "Estructura del Repositorio"           |
| Nueva variable de entorno                      | Tabla "Variables de Entorno"                   |
| Nuevo prefijo de callback                      | Tabla de prefijos de callback                  |
| Nuevo flow de conversacion (ConversationHandler)| Seccion "Convenciones de Estado"              |
| Nueva funcion publica en db.py                 | Seccion de la capa de datos o tabla relevante  |
| Nueva capa, modulo web o ruta de API           | Seccion "Arquitectura de Capas" o "web/"       |
| Nueva constante de tiempo o radio (order_delivery) | Seccion "Sistema de Tracking de Llegada"   |

Reglas de aplicacion:

1. El agente no debe esperar una orden separada de "documenta esto" para cambios estructurales.
   La documentacion va incluida en el mismo commit del cambio.
2. Si el cambio no encaja en ninguna fila de la tabla: agregar una nota breve en la seccion
   mas cercana de CLAUDE.md y mencionar el archivo y funcion exactos.
3. La descripcion en CLAUDE.md debe ser de una linea por elemento nuevo. No un parrafo.
4. El git log es el historial cronologico. CLAUDE.md es la referencia de estado actual.
   No hay CHANGELOG separado.

Este documento representa el estándar definitivo y vigente del proyecto Domiquerendona.

Complemento operativo: CLAUDE.md contiene la estructura del repositorio, arquitectura de capas, convenciones de desarrollo, guía de variables de entorno, flujo de desarrollo local, testing y despliegue. AGENTS.md define las reglas obligatorias; CLAUDE.md explica el cómo y el qué del sistema. Ambos documentos deben leerse juntos y no tienen conflictos entre sí.

---

18. Regla de presentacion de codigo para revision

Cuando el usuario pida "mostrar codigo para revision" o "codigo exacto para revision final":

1. Mostrar SOLO el codigo final resultante. NUNCA mostrar el codigo anterior ni un diff.
2. No usar formato "antes/despues". No usar bloques con codigo viejo tachado o comentado.
3. Si se piden varios bloques, pegarlos en orden limpio, uno tras otro, sin comparaciones.
4. El codigo que se muestra debe ser el que esta en el archivo en ese momento, exactamente como quedaria al ser leido por otro agente o herramienta.

Razon: el usuario comparte estas revisiones con otras herramientas (como ChatGPT) que no
distinguen colores de diff y se confunden si ven codigo viejo y nuevo mezclados.

## Sección 18 — Reglas post-modularización: verificación de completitud

### Contexto
Durante el merge de la rama `luisa-web` (modularización de `main.py` en `handlers/`) se detectaron
en producción 4 errores de arranque causados por funciones referenciadas en `main.py` que no
existían en los módulos destino:

| Función | Problema | Módulo correcto |
|---|---|---|
| `update_order_payment` | Import en main.py pero no exportada por services.py en Railway | Eliminado (no usado) |
| `admin_pedido_tarifa_handler` | Importada desde handlers/order pero nunca definida | Eliminado (no usado) |
| `pedido_incentivo_menu_callback` | Definida en handlers/order pero no incluida en el import de main.py | Agregado al import |
| `pedido_incentivo_existing_fixed_callback` | Definida en handlers/order pero no incluida en el import de main.py | Agregado al import |
| `admin_config_callback` | Función de ~400 líneas que no fue movida a ningún módulo durante la modularización | Restaurada en handlers/admin_panel.py |

### Regla 18A — Checklist obligatorio antes de mergear una rama de modularización

Antes de hacer merge de cualquier rama que mueva funciones entre archivos, ejecutar:
```bash
# 1. Verificar que todos los nombres importados en main.py existen en sus módulos
python -c "
import ast

files = {
    'handlers/admin_panel.py', 'handlers/ally_bandeja.py', 'handlers/common.py',
    'handlers/config.py', 'handlers/courier_panel.py', 'handlers/customer_agenda.py',
    'handlers/location_agenda.py', 'handlers/order.py', 'handlers/quotation.py',
    'handlers/recharges.py', 'handlers/registration.py', 'handlers/route.py',
    'handlers/states.py',
}
defined = {}
for path in files:
    with open(path, encoding='utf-8-sig') as f:
        tree = ast.parse(f.read())
    defined[path] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined[path].add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined[path].add(t.id)

with open('main.py', encoding='utf-8-sig') as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('handlers.'):
        mod_file = node.module.replace('.', '/') + '.py'
        for alias in node.names:
            name = alias.name
            if name == '*':
                continue
            if mod_file in defined and name not in defined[mod_file]:
                print(f'FALTANTE: {name} importado desde {mod_file} pero no definido ahi')
print('Verificacion completa')
"

# 2. Verificar que todos los callbacks en dp.add_handler están importados
# (ver script completo en AGENTS.md Sección 18B)
```

### Regla 18B — Verificar callbacks en dp.add_handler
```bash
python -c "
import ast

with open('main.py', encoding='utf-8-sig') as f:
    src = f.read()
tree = ast.parse(src)
defined = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        defined.add(node.name)
    elif isinstance(node, ast.Import):
        for a in node.names:
            defined.add(a.asname or a.name)
    elif isinstance(node, ast.ImportFrom):
        for a in node.names:
            defined.add(a.asname or a.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                defined.add(t.id)

missing = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == 'add_handler':
            for arg in node.args:
                if isinstance(arg, ast.Call):
                    inner = arg.func
                    htype = inner.attr if isinstance(inner, ast.Attribute) else ''
                    if htype in ('CallbackQueryHandler', 'CommandHandler', 'MessageHandler') and arg.args:
                        cb = arg.args[0]
                        if isinstance(cb, ast.Name) and cb.id not in defined:
                            missing.append((htype, cb.id))

for htype, name in sorted(set(missing)):
    print(f'NO DEFINIDO [{htype}]: {name}')
if not missing:
    print('Todos los callbacks OK')
"
```

### Regla 18C — Durante una modularización, al mover una función

Antes de eliminarla de `main.py`, verificar con grep que fue correctamente copiada al módulo destino:
```bash
grep -n "def nombre_funcion" handlers/modulo_destino.py
```
Si no aparece → NO eliminar de main.py todavía.

### Regla 18D — Al hacer merge de rama de modularización

Ejecutar siempre el checklist 18A, 18B y 18E **antes del push a staging**. Un crash en producción
por import faltante es evitable al 100% con estas verificaciones locales.

### Regla 18E — Verificar imports internos de cada handler (NameErrors en ejecucion)

**Contexto:** `py_compile` solo detecta errores de sintaxis. Los NameErrors por funciones
llamadas dentro de un handler sin estar importadas solo explotan cuando esa rama de código
se ejecuta. Detectados en 2026-03-20: 21 faltantes en `admin_panel.py`, 1 en `recharges.py`.

**PROHIBIDO** hacer push a staging tras mover codigo a handlers/ sin ejecutar este script:

```bash
cd Backend/
python3 << 'PYEOF'
import re, os

base = os.getcwd()

def get_imported(src):
    names = set()
    for block in re.findall(r'from\s+\S+\s+import\s+\(([^)]+)\)', src, re.DOTALL):
        for n in re.findall(r'\b([A-Za-z_]\w*)\b', block): names.add(n)
    for line in re.findall(r'^from\s+\S+\s+import\s+([^(\n]+)', src, re.M):
        if '(' not in line:
            for n in re.findall(r'\b([A-Za-z_]\w*)\b', line): names.add(n)
    return names

# Construir inventario de services.py
with open(base+'/services.py', 'r', encoding='utf-8') as f: svc = f.read()
svc_available = set(re.findall(r'^def (\w+)', svc, re.M))
for block in re.findall(r'from db import \((.*?)\)', svc, re.DOTALL):
    for name in re.findall(r'\b([a-z_][a-z0-9_]+)\b', block):
        svc_available.add(name)

found_issues = False
for hname in ['admin_panel','ally_bandeja','config','courier_panel','customer_agenda',
              'location_agenda','order','quotation','recharges','registration','route']:
    path = base+f'/handlers/{hname}.py'
    with open(path, 'r', encoding='utf-8') as f: src = f.read()
    imported = get_imported(src)
    defined = set(re.findall(r'^(?:def|class)\s+(\w+)', src, re.M))
    known = imported | defined
    missing = sorted([n for n in svc_available
                      if n not in known and re.search(r'\b'+re.escape(n)+r'\s*\(', src)])
    if missing:
        found_issues = True
        print(f'FALTANTE en {hname}.py: {missing}')

if not found_issues:
    print('OK — todos los handlers tienen sus imports de services completos')
PYEOF
```

**Qué verifica:** para cada handler, busca funciones de `services.py` (y sus re-exports de `db.py`)
que son llamadas en el cuerpo pero no están en el bloque `from services import (...)`.

**Falsos positivos conocidos:** palabras como `py`, `no`, `parada` (provienen de comentarios
en el bloque re-exports de services.py). Ignorarlos — no son funciones reales.

**Causa raiz del error:** al extraer una funcion de main.py a un handler, se copia el cuerpo
pero no se revisan sistematicamente todas las dependencias. La solucion es ejecutar este script
antes de cada push, no despues.

---

## Sección 19 — Uniformidad de flujos de pedido

**REGLA OBLIGATORIA:** Todo ajuste de comportamiento (UX, validaciones, timers, GPS, botones,
textos) aplicado a cualquiera de los tres flujos de pedido DEBE aplicarse a los otros dos.

Los tres flujos que siempre viajan juntos:

| Flujo | Archivo | Handler principal |
|-------|---------|-------------------|
| Pedido de aliado | `handlers/order.py` + `order_delivery.py` | `nuevo_pedido_conv` |
| Pedido especial de admin | `handlers/order.py` + `order_delivery.py` | `admin_pedido_conv` |
| Ruta multi-parada | `handlers/route.py` + `order_delivery.py` | `nueva_ruta_conv` |

**Aplica especialmente a:**
- Radios GPS (ARRIVAL_RADIUS_KM, DELIVERY_RADIUS_KM)
- Timers de tracking (T+5, T+15, T+20, auto-confirm T+2)
- Botones de ayuda al admin (pin de recogida mal ubicado, pin de entrega mal ubicado)
- Flujo de confirmación de llegada al pickup
- Mensajes de estado al courier y al aliado

**Antes de cerrar cualquier cambio a flujos de pedido:** verificar los 3 flujos y documentar
en CLAUDE.md si se agregan constantes, funciones o callbacks nuevos.
