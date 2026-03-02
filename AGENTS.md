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
- Flujo pedido:    pickup_*, customer_*, instructions, requires_cash, cash_required_amount, pedido_incentivo, pedido_incentivo_edit_order_id, etc.
- Flujo recarga:   recargar_target_type, recargar_target_id, recargar_admin_id, etc.
- Flujo ingreso externo (plataforma): ingreso_monto, ingreso_metodo

Reglas:
- PROHIBIDO leer una clave de flujo A dentro de un handler de flujo B.
- Si se agrega una clave nueva, documentarla en esta sección en el mismo commit.
- PROHIBIDO usar claves genéricas ("data", "value", "temp") sin prefijo de flujo.

2D. Estándar obligatorio de callback_data

Formato: {dominio}_{accion} o {dominio}_{accion}_{id}

Prefijos de dominio existentes y sus dueños:
- admin_       → panel y acciones de administrador local
- admpedidos_  → panel de pedidos del administrador (listado, filtros por estado)
- agenda_      → agenda de pedidos
- ally_        → acciones específicas del aliado (fuera del flujo de pedido)
- chgreq_      → solicitudes de cambio de perfil (profile_changes.py)
- chgteam_     → cambio de equipo/grupo
- config_      → configuración del sistema
- cotizar_     → flujo de cotización de envío
- courier_     → acciones de repartidor
- cust_        → acciones de cliente
- dir_         → gestión de direcciones de recogida del aliado
- guardar_     → guardar dirección de cliente tras un pedido
- menu_        → navegación de menú
- order_       → ofertas y entrega de pedidos (order_delivery.py)
- pagos_       → sistema de pagos
- pedido_      → flujo de creación de pedidos
- perfil_      → cambios de perfil de usuarios (profile_changes.py)
- pickup_      → selección de punto de recogida
- preview_     → previsualización de pedido antes de confirmar
- pricing_     → configuración de tarifas
- recargar_    → sistema de recargas
- ref_         → validación de referencias
- terms_       → aceptación de términos y condiciones
- ubicacion_   → selección de ubicación GPS
- ingreso_     → registro de ingreso externo del administrador de plataforma

Reglas:
- PROHIBIDO crear un prefijo nuevo sin aprobación explícita del usuario.
- PROHIBIDO usar callback_data sin prefijo de dominio.
- El separador es siempre guion bajo (_). No usar guion, punto ni slash.
- Antes de agregar un callback nuevo, verificar con git grep que no existe uno equivalente.

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

python -m py_compile Backend/main.py Backend/services.py Backend/db.py order_delivery.py profile_changes.py

Verificar imports huérfanos tras mover o eliminar funciones:
Para cada nombre movido o eliminado, ejecutar:
git grep "nombre_funcion" -- "*.py"
Si solo aparece en el bloque import y en ningún otro lugar → el import es huérfano y debe eliminarse.

Reportar claramente:

qué cambió

qué se eliminó

por qué

7. Git y ramas

Nunca trabajar directamente sobre main.

Confirmar siempre la rama activa antes de modificar código.

REGLA OPERATIVA (NUEVA, OBLIGATORIA):

Siempre se trabaja sobre la rama staging.

Todo commit y push del trabajo se hace directamente a origin/staging.

Excepción única:
- Cambios estructurales de base de datos (ver 7B) se implementan en verify/* y luego se mergean a staging.

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

7D. Ramas protegidas y ramas de colaboradores

Las siguientes ramas son PERMANENTES y NUNCA deben borrarse:

- main       → producción (Railway PROD). NUNCA trabajar directamente aquí.
- staging    → rama de trabajo e integración. Aquí se desarrolla, se hace commit y se hace push.
- luisa-web  → rama de trabajo de la colaboradora Luisa (activa).

Flujo oficial de ramas:

  staging   ──(validado)──►  main
  verify/*  ──merge──►  staging  ──(validado)──►  main
                         (entorno DEV:
                          BOT_TOKEN DEV
                          DATABASE_URL separada)

Reglas de flujo:
- PROHIBIDO mergear verify/* directamente a main sin pasar por staging.
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

Implementación técnica:
  - UI (main.py → recargar_monto): mostrar "Plataforma" siempre, sin verificar vínculo APPROVED.
  - Validación (main.py → recargar_admin_callback): permitir platform_id aunque no esté en approved_links.
  - Aprobación (services.py → approve_recharge_request): cuando el aprobador es plataforma y el
    destinatario es COURIER/ALLY sin vínculo directo con plataforma, actualizar el balance en el
    vínculo APPROVED activo que el courier/ally sí tiene (con su admin local).
  - Ledger: registrar siempre PLATFORM → COURIER/ALLY para trazabilidad del origen del saldo.

Estado: PENDIENTE DE IMPLEMENTACIÓN (regla de negocio aprobada, código no modificado aún).

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

PROHIBIDO revelar customer_name, customer_phone ni customer_address al repartidor en _handle_accept o en cualquier momento antes de que el aliado confirme la llegada.

El único lugar donde se revelan estos datos al repartidor es _notify_courier_pickup_approved (order_delivery.py), llamada tras la confirmación del aliado.

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

Este documento representa el estándar definitivo y vigente del proyecto Domiquerendona.

Complemento operativo: CLAUDE.md contiene la estructura del repositorio, arquitectura de capas, convenciones de desarrollo, guía de variables de entorno, flujo de desarrollo local, testing y despliegue. AGENTS.md define las reglas obligatorias; CLAUDE.md explica el cómo y el qué del sistema. Ambos documentos deben leerse juntos y no tienen conflictos entre sí.
