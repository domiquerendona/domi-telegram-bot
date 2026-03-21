# CLAUDE.md — Guía técnica y arquitectura explicada de Domiquerendona

Este archivo describe la estructura del proyecto, flujos de trabajo y convenciones técnicas del repositorio. Es un complemento explicativo de `AGENTS.md`, que define las reglas obligatorias.

> **IMPORTANTE:** Las reglas de `AGENTS.md` tienen prioridad absoluta. Este documento explica el "qué" y el "cómo" del sistema; `AGENTS.md` define el "no harás".
>
> **Alcance de este documento:** `CLAUDE.md` explica arquitectura, módulos, despliegue y flujos. No define normas obligatorias. Las reglas normativas del proyecto están en `AGENTS.md`.

---

## Visión General del Proyecto

**Domiquerendona** es una plataforma de domicilios (delivery) que opera en Colombia. El sistema consta de:

1. **Bot de Telegram** (Backend/): bot conversacional que gestiona pedidos, registros y operaciones de todos los actores del sistema.
2. **API Web** (Backend/web/): API REST con FastAPI que expone endpoints para el panel administrativo.
3. **Panel Web** (Frontend/): aplicación Angular 21 con SSR para administradores del panel. Soporta dos roles: `ADMIN_PLATFORM` (acceso total) y `ADMIN_LOCAL` (vistas filtradas por equipo).

Los actores principales del sistema son:
- **Platform Admin**: administrador global de la plataforma (un solo usuario).
- **Admin Local**: administra un equipo de repartidores y aliados en una zona. Sus atribuciones son:
  - Aprobar o rechazar miembros pendientes de su equipo (repartidores y aliados).
  - Inactivar miembros activos (`APPROVED` → `INACTIVE`) y reactivarlos (`INACTIVE` → `APPROVED`).
  - **NO puede** rechazar definitivamente (`REJECTED`) — esa acción es exclusiva del Admin de Plataforma.
  - Gestiona pedidos de su equipo y aprueba recargas de saldo a sus miembros.
- **Aliado (Ally)**: negocio asociado (restaurante, tienda, etc.) que genera pedidos.
- **Repartidor (Courier)**: entrega los pedidos.
- **Cliente (Customer)**: destinatario del pedido (no tiene cuenta en el bot).

---

## Estructura del Repositorio

```
domi-telegram-bot/
├── AGENTS.md                     # Reglas obligatorias del proyecto (leer primero)
├── CLAUDE.md                     # Este archivo
├── .gitignore                    # Ignora __pycache__, .env, *.db, etc.
│
├── Backend/                      # Lógica del bot y API
│   ├── main.py                   # Wiring, UI global, arranque del bot (~2 324 líneas — modularización completa 2026-03-20)
│   ├── web_app.py                # Bootstrap FastAPI (app, routers, CORS, /)
│   ├── services.py               # Lógica de negocio + re-exports de db.py
│   ├── db.py                     # Acceso exclusivo a base de datos
│   ├── order_delivery.py         # Flujo completo de entrega de pedidos
│   ├── profile_changes.py        # Flujo de cambios de perfil de usuarios
│   ├── imghdr.py                 # Utilidad para detección de imágenes
│   ├── requirements.txt          # Dependencias Python
│   ├── Dockerfile                # Imagen Docker del backend
│   ├── Procfile                  # Comando de arranque para Railway
│   ├── .env.example              # Plantilla de variables de entorno
│   ├── DEPLOY.md                 # Guía de separación DEV/PROD
│   ├── TESTING.md                # Documento histórico de testing (fase antigua)
│   │
│   ├── handlers/                 # Paquete de ConversationHandlers extraídos de main.py (modularización completa)
│   │   ├── __init__.py
│   │   ├── states.py             # Constantes de estado para todos los ConversationHandlers
│   │   ├── common.py             # Helpers compartidos: cancel_conversacion, ensure_terms, _fmt_pesos, _geo_siguiente_o_gps, etc.
│   │   ├── config.py             # tarifas_conv, config_alertas_oferta_conv, config_ally_subsidy_conv, config_ally_minpurchase_conv
│   │   ├── quotation.py          # cotizar_conv (flujo de cotización de envío)
│   │   ├── location_agenda.py    # admin_dirs_conv, ally_locs_conv (gestión de ubicaciones)
│   │   ├── customer_agenda.py    # clientes_conv, agenda_conv, admin_clientes_conv, ally_clientes_conv
│   │   ├── registration.py       # soy_aliado/ally_conv, soy_repartidor/courier_conv, soy_admin/admin_conv, admin_cedula handlers
│   │   ├── recharges.py          # recargar_conv, configurar_pagos_conv, ingreso_conv, cmd_saldo, admin_local_callback, ally_approval_callback
│   │   ├── order.py              # nuevo_pedido_conv, pedido_incentivo_conv, offer_suggest_inc_conv, admin_pedido_conv (~99 funciones)
│   │   ├── route.py              # nueva_ruta_conv (flujo de rutas multi-parada, ~32 funciones)
│   │   ├── admin_panel.py        # admin_menu, admin_menu_callback, aliados_pendientes, repartidores_pendientes, admins_pendientes, admin_ver_pendiente, admin_aprobar_rechazar_callback, pendientes, volver_menu_global, courier_pick_admin_callback, reference validation helpers
│   │   ├── ally_bandeja.py       # ally_bandeja_solicitudes, ally_mi_enlace, ally_enlace_refresh_callback, _ally_bandeja_mostrar_*, ally_bandeja_callback
│   │   └── courier_panel.py      # courier_earnings_start, courier_earnings_callback, _courier_earnings_group_by_date, _courier_earnings_buttons
│   │
│   ├── migrations/
│   │   └── postgres_schema.sql   # Schema completo para PostgreSQL
│   │
│   └── web/                      # Módulo FastAPI (panel web)
│       ├── __init__.py
│       ├── admin/
│       │   ├── __init__.py
│       │   └── services.py       # Lógica: approve_user, reject_user, deactivate_user
│       ├── api/
│       │   ├── __init__.py
│       │   ├── admin.py          # Endpoints: POST /admin/users/{id}/approve, etc.
│       │   ├── dashboard.py      # Endpoints del dashboard
│       │   └── users.py          # Endpoints de usuarios
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── dependencies.py   # get_current_user (dependencia FastAPI)
│       │   └── guards.py         # is_admin(), can_access_system(), is_blocked()
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── user.py           # Pydantic schemas (UserResponse, etc.)
│       ├── teams/
│       │   └── models.py         # Modelos de equipos
│       ├── users/
│       │   ├── __init__.py
│       │   ├── models.py         # UserRole, UserStatus (enums)
│       │   ├── repository.py     # get_user_by_id(), etc.
│       │   ├── roles.py          # RBAC: ADMIN_ALLOWED, COURIER_ONLY, etc.
│       │   └── status.py         # ACTIVE_USERS, BLOCKED_USERS
│       └── wallet/
│           ├── __init__.py
│           └── models.py         # Modelos de billetera
│
├── Frontend/                     # Panel administrativo Angular
│   ├── angular.json
│   ├── package.json              # Angular 21, SSR, vitest
│   ├── tsconfig.json
│   └── src/
│       ├── main.ts               # Entry point cliente
│       ├── main.server.ts        # Entry point SSR
│       ├── server.ts             # Express SSR server
│       └── app/
│           ├── app.ts            # Componente raíz
│           ├── app.routes.ts     # Rutas del cliente
│           ├── core/
│           │   ├── guards/       # auth.guard.ts
│           │   ├── interceptors/ # auth.interceptor.ts
│           │   └── services/     # api.ts (servicio HTTP)
│           ├── features/
│           │   └── superadmin/
│           │       ├── dashboard/
│           │       ├── settings/
│           │       └── users/
│           └── layout/
│               ├── components/   # header/, sidebar/
│               └── superadmin-layout/
│
├── docs/
│   ├── HITOS.md                  # Documento histórico de hitos
│   ├── reglas_operativas.md      # Matriz de estados y botones UI
│   ├── testing_strategy.md       # Estrategia de testing vigente
│   ├── alineacion_codigo_documentacion_2026-03-12.md  # Snapshot histórico de auditoría
│   └── callback_governance_2026-03-12.md              # Fuente de verdad de callbacks
│
├── migrations/
│   ├── migrate_sqlite_to_postgres.py
│   └── postgres_schema.sql       # Copia del schema en raíz (legacy)
│
└── tests/
    ├── test_recharge_idempotency.py   # Tests de idempotencia en recargas
    └── test_status_validation.py      # Tests de validación de estados
```

---

## Arquitectura de Capas (Backend)

La regla más importante del proyecto es la separación estricta en tres capas:

```
handlers/*  ──importa──►  main.py  ──importa──►  services.py  ──importa──►  db.py
    │                        │                       │                        │
    │  (ConversationHandlers, │  (wiring, UI, start,  │  (lógica de negocio,  │  (SQL, queries,
    │   flujos de pedido,     │   menu, arranque)     │   re-exports de db)   │   conexiones)
    │   rutas, recargas,      │                       │                        │
    │   registro, config)     └── order_delivery.py ──┘                        │
    │                         └── profile_changes.py ─────────────────────────►┘
    │
    └── (importan desde services.py y order_delivery.py, nunca desde main.py)
```

### `db.py` — Capa de Datos
- **Único responsable** de toda interacción con la base de datos.
- Detecta motor en tiempo de arranque: `DATABASE_URL` presente → PostgreSQL; ausente → SQLite.
- Usa el placeholder global `P` (`%s` para Postgres, `?` para SQLite) en todas las queries.
- La regla obligatoria de conexiones y compatibilidad multi-motor está en `AGENTS.md`.
- Helpers multi-motor: `_insert_returning_id()`, `_row_value()`.

### `services.py` — Capa de Negocio
- Contiene toda la lógica de negocio que no es específica de un módulo grande.
- Importa desde `db.py` y re-exporta funciones para que `main.py` no acceda a `db.py` directamente.
- El bloque de re-exports está marcado con el comentario: `# Re-exports para que main.py no acceda a db directamente`.
- El patrón obligatorio de re-export está documentado en `AGENTS.md`.

### `main.py` — Orquestador
- Contiene: wiring (registro de handlers), `start`, `menu`, handlers de UI global, arranque del bot, `main()`.
- Los ConversationHandlers están en `handlers/` — `main.py` los importa y los registra con `dp.add_handler()`.
- Las restricciones obligatorias sobre qué puede y qué no puede vivir en `main.py` están en `AGENTS.md`.
- **Excepciones permitidas** en `main.py` (solo estas 3):
  ```python
  from db import init_db
  from db import force_platform_admin
  from db import ensure_pricing_defaults
  ```

### `handlers/` — Paquete de ConversationHandlers

Paquete creado en la modularización 2026-03-18/20. Cada módulo agrupa funciones y ConversationHandlers por dominio. Regla: **ningún módulo en `handlers/` importa desde `main.py`**.

| Módulo | Contenido |
|--------|-----------|
| `states.py` | Todas las constantes de estado (enteros) de todos los ConversationHandlers |
| `common.py` | Helpers compartidos sin dependencia de `main.py`: `cancel_conversacion`, `cancel_por_texto`, `ensure_terms`, `show_main_menu`, `show_flow_menu`, `_fmt_pesos`, `_geo_siguiente_o_gps`, `_mostrar_confirmacion_geocode`, `_handle_text_field_input`, `_handle_phone_input`, `_OPTIONS_HINT`, `CANCELAR_VOLVER_MENU_FILTER` |
| `config.py` | `tarifas_conv`, `config_alertas_oferta_conv`, `config_ally_subsidy_conv`, `config_ally_minpurchase_conv` |
| `quotation.py` | `cotizar_conv` (flujo de cotización de envío del aliado) |
| `location_agenda.py` | `admin_dirs_conv` (mis ubicaciones admin), `ally_locs_conv` (mis ubicaciones aliado) |
| `customer_agenda.py` | `clientes_conv`, `agenda_conv`, `admin_clientes_conv`, `ally_clientes_conv` |
| `registration.py` | `ally_conv` (soy_aliado), `courier_conv` (soy_repartidor), `admin_conv` (soy_admin), handlers de cédula/selfie |
| `recharges.py` | `recargar_conv`, `configurar_pagos_conv`, `ingreso_conv`, `cmd_saldo`, `admin_local_callback`, `ally_approval_callback` |
| `order.py` | `nuevo_pedido_conv`, `pedido_incentivo_conv`, `offer_suggest_inc_conv`, `admin_pedido_conv` — flujo completo de creación de pedidos (~99 funciones) |
| `route.py` | `nueva_ruta_conv` — flujo de rutas multi-parada (~32 funciones) |
| `admin_panel.py` | `admin_menu`, `admin_menu_callback`, `aliados_pendientes`, `repartidores_pendientes`, `admins_pendientes`, `admin_ver_pendiente`, `admin_aprobar_rechazar_callback`, `pendientes`, `volver_menu_global`, `courier_pick_admin_callback`, helpers de referencias |
| `ally_bandeja.py` | `ally_bandeja_solicitudes`, `ally_mi_enlace`, `ally_enlace_refresh_callback`, `_ally_bandeja_mostrar_*`, `ally_bandeja_callback` |
| `courier_panel.py` | `courier_earnings_start`, `courier_earnings_callback`, helpers internos de ganancias |

### Módulos Especializados
- **`order_delivery.py`**: flujo completo de publicación, ofertas y entrega de pedidos.
- **`profile_changes.py`**: flujo de solicitudes de cambio de perfil de usuarios.

### Regla Anti-Importación Circular

Si un módulo secundario (`profile_changes.py`, `order_delivery.py`, etc.) necesita una función de `main.py`, la regla obligatoria de resolución está en `AGENTS.md`.
En la práctica, este repositorio resuelve esos casos moviendo la función a `services.py` o, solo si es inevitable, usando import lazy documentado.

---

## Base de Datos

### Motor Dual (SQLite + PostgreSQL)

| Ambiente | Motor | Configuración |
|----------|-------|---------------|
| LOCAL (desarrollo) | SQLite | `DATABASE_URL` no definida; usa `DB_PATH` |
| PROD (Railway) | PostgreSQL | `DATABASE_URL` presente |

La selección es automática en `db.py`:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
DB_ENGINE = "postgres" if DATABASE_URL else "sqlite"
P = "%s" if DB_ENGINE == "postgres" else "?"
```

### Estados Estándar

Todos los roles (admin, aliado, repartidor) usan exactamente estos estados:

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Registro nuevo, esperando aprobación |
| `APPROVED` | Aprobado y activo, puede operar |
| `INACTIVE` | Desactivado temporalmente, puede reactivarse |
| `REJECTED` | Rechazado (estado terminal desde UI) |

**Reglas de transición:**
- `PENDING` → Aprobar → `APPROVED` / Rechazar → `REJECTED`
- `APPROVED` → Desactivar → `INACTIVE`
- `INACTIVE` → Activar → `APPROVED`
- `REJECTED` → estado terminal (no hay botones de acción)

### Separación de Identificadores

**NUNCA mezclar:**
- `telegram_id` → solo para mensajería en Telegram
- `users.id` → ID interno principal
- `admins.id`, `couriers.id`, `allies.id` → IDs de rol

### Reglas de Migraciones

Las reglas obligatorias de migraciones y cambios estructurales de base de datos están en `AGENTS.md`.
Aquí solo se conserva el contexto técnico: las migraciones del proyecto son no destructivas, idempotentes y compatibles con datos existentes.

### Tablas Principales

| Tabla | Descripción |
|-------|-------------|
| `users` | Todos los usuarios del bot (por `telegram_id`) |
| `admins` | Administradores locales y de plataforma |
| `couriers` | Repartidores |
| `allies` | Aliados (negocios) |
| `identities` | Identidad global (teléfono + documento únicos) |
| `admin_couriers` | Vínculos admin ↔ repartidor con estado y balance |
| `admin_allies` | Vínculos admin ↔ aliado con estado y balance |
| `admin_locations` | Ubicaciones de recogida guardadas por administradores (para pedidos especiales). Columna `status TEXT DEFAULT 'ACTIVE'` para soft-delete. |
| `admin_customers` | Clientes de entrega del admin (personas que le solicitan domicilios). Campos: `admin_id`, `name`, `phone`, `notes`, `status`. |
| `admin_customer_addresses` | Direcciones de entrega de cada cliente del admin. Campos: `customer_id`, `label`, `address_text`, `city`, `barrio`, `notes`, `lat`, `lng`, `status`. |
| `orders` | Pedidos con todo su ciclo de vida. Columnas de tracking: `courier_arrived_at` (timestamp GPS), `courier_accepted_lat/lng` (posición al aceptar, base T+5), `dropoff_lat/lng` (coordenadas del punto de entrega). Columnas de pedido admin: `creator_admin_id` (NULL = pedido de aliado, valor = admin creador), `ally_id` (nullable, NULL en pedidos especiales de admin) |
| `order_support_requests` | Solicitudes de ayuda por pin mal ubicado. Campos: `order_id` (nullable), `route_id` (nullable), `route_seq` (nullable, para rutas), `courier_id`, `admin_id`, `status` (PENDING/RESOLVED), `resolution` (DELIVERED/CANCELLED_COURIER/CANCELLED_ALLY), `created_at`, `resolved_at`, `resolved_by`. |
| `recharge_requests` | Solicitudes de recarga de saldo |
| `ledger` | Libro contable de todas las transacciones |
| `settings` | Configuración del sistema (clave-valor) |
| `profile_change_requests` | Solicitudes de cambio de perfil |
| `web_users` | Usuarios del panel web (login con contraseña hasheada). Campos: `id`, `username` (UNIQUE), `password_hash` (bcrypt), `role` (`ADMIN_PLATFORM`\|`ADMIN_LOCAL`), `status` (`APPROVED`\|`INACTIVE`), `admin_id` (FK → admins.id, NULL para ADMIN_PLATFORM), `created_at`, `updated_at`. Seed inicial desde `WEB_ADMIN_USER`/`WEB_ADMIN_PASSWORD` via `ensure_web_admin()`. |

---

## Flujos de Conversación (Bot de Telegram)

### Convenciones de Estado (`context.user_data`)

La convenci??n obligatoria de claves est?? en AGENTS.md.
Aqu?? se resume el mapa actual de prefijos usados por los flujos:

| Flujo | Prefijos de claves |
|-------|-------------------|
| Registro aliado | `ally_phone`, `ally_name`, `ally_owner`, `ally_document`, `city`, `barrio`, `address`, `ally_lat`, `ally_lng` |
| Registro repartidor | `phone`, `courier_fullname`, `courier_idnumber`, `city`, `barrio`, `residence_address`, `courier_lat`, `courier_lng` |
| Registro admin | `phone`, `admin_city`, `admin_barrio`, `admin_residence_address`, `admin_lat`, `admin_lng` |
| Pedido | `pickup_*`, `customer_*`, `instructions`, `requires_cash`, `cash_required_amount` |
| Recarga | `recargar_target_type`, `recargar_target_id`, `recargar_admin_id` |
| Ingreso externo (plataforma) | `ingreso_monto`, `ingreso_metodo` |
| Agenda clientes (coordenadas) | `clientes_geo_mode` (`corregir_coords` al agregar/corregir coords), `current_customer_id`, `current_address_id`, `clientes_geo_address_input` |

### Convención de `callback_data`

Las reglas obligatorias de callbacks están en `AGENTS.md`.
La fuente de verdad operativa del inventario vigente es `docs/callback_governance_2026-03-12.md`.

Formato: `{dominio}_{accion}` o `{dominio}_{accion}_{id}`

Separador operativo actual: guion bajo (`_`).

| Prefijo | Dominio |
|---------|---------|
| `admin_` | Panel y acciones de administrador local |
| `admpedidos_` | Panel de pedidos del administrador |
| `agenda_` | Agenda de pedidos |
| `ally_` | Acciones del aliado |
| `chgreq_` | Solicitudes de cambio de perfil |
| `chgteam_` | Cambio de equipo/grupo |
| `config_` | Configuración del sistema |
| `cotizar_` | Flujo de cotización de envío |
| `courier_` | Acciones de repartidor |
| `cust_` | Acciones de cliente. Incluye: `cust_dir_corregir_coords` (abre flujo para agregar/corregir coords de una dirección guardada), `cust_geo_si` / `cust_geo_no` (confirmar geocoding en flujo de dirección) |
| `dir_` | Gestión de direcciones de recogida |
| `guardar_` | Guardar dirección de cliente |
| `menu_` | Navegación de menú |
| `order_` | Ofertas y entrega de pedidos. Incluye: `order_find_another_{id}` (aliado busca otro courier), `order_call_courier_{id}` (aliado ve teléfono del courier), `order_wait_courier_{id}` (aliado sigue esperando), `order_delivered_confirm_{id}` / `order_delivered_cancel_{id}` (confirmación de entrega en courier — requiere GPS activo y radio ≤100m), `order_confirm_pickup_{id}` (courier confirma recogida del pedido), `order_pinissue_{id}` (courier reporta pin de entrega mal ubicado), `order_release_reason_{id}_{reason}` / `order_release_confirm_{id}_{reason}` / `order_release_abort_{id}` (liberación responsable con motivo) |
| `admin_pinissue_` | Panel de soporte de pin mal ubicado — pedidos. Incluye: `admin_pinissue_fin_{id}` (admin finaliza servicio), `admin_pinissue_cancel_courier_{id}` (admin cancela, falla del courier), `admin_pinissue_cancel_ally_{id}` (admin cancela, falla del aliado) |
| `admin_ruta_pinissue_` | Panel de soporte de pin mal ubicado — rutas. Incluye: `admin_ruta_pinissue_fin_{route_id}_{seq}`, `admin_ruta_pinissue_cancel_courier_{route_id}_{seq}`, `admin_ruta_pinissue_cancel_ally_{route_id}_{seq}` |
| `pagos_` | Sistema de pagos |
| `pedido_` | Flujo de creación de pedidos. Incluye: `pedido_nueva_dir` (nueva dirección para cliente recurrente → va a `PEDIDO_UBICACION` con geocoding completo, igual que cotización), `pedido_geo_si` / `pedido_geo_no` (confirmar geocoding de dirección de entrega), `pedido_sel_addr_{id}` (seleccionar dirección guardada del cliente) |
| `perfil_` | Cambios de perfil |
| `pickup_` | Selección de punto de recogida |
| `preview_` | Previsualización de pedido |
| `pricing_` | Configuración de tarifas |
| `recargar_` | Sistema de recargas |
| `ref_` | Validación de referencias |
| `terms_` | Aceptación de términos y condiciones |
| `ubicacion_` | Selección de ubicación GPS |
| `ingreso_` | Registro de ingreso externo del Admin de Plataforma |
| `admin_pedido_` | Flujo de creación de pedido especial del admin. Incluye: `admin_nuevo_pedido` (entry point), `admin_pedido_pickup_{id}` (seleccionar pickup guardado), `admin_pedido_nueva_dir` (nueva dirección pickup), `admin_pedido_geo_pickup_si/no` (confirmar geo pickup), `admin_pedido_geo_si/no` (confirmar geo entrega), `admin_pedido_sin_instruc` (sin instrucciones), `admin_pedido_inc_{1500|2000|3000}` (incentivos fijos en preview), `admin_pedido_inc_otro` (incentivo libre), `admin_pedido_confirmar` (publicar), `admin_pedido_cancelar` (cancelar) |
| `offer_inc_` | Sugerencia T+5 de incentivo (aliado y admin). Incluye: `offer_inc_{order_id}x{1500|2000|3000}` (incentivos fijos), `offer_inc_otro_{order_id}` (incentivo libre) |

**Antes de agregar un callback nuevo:** `git grep "nuevo_prefijo" -- "*.py"` para verificar que no existe ya.

### Repartidor: Pedidos en curso

En `Backend/main.py:courier_pedidos_en_curso()` existe el botón "Pedidos en curso" para el repartidor:
- Muestra el pedido activo (`orders.status` en `ACCEPTED`/`PICKED_UP`) y/o la ruta activa (`routes.status` en `ACCEPTED`).
- Botones:
  - Si `orders.status == ACCEPTED`:
    - "Solicitar confirmacion de recogida" → `order_pickup_{id}`.
    - "Liberar pedido" → `order_release_{id}` → requiere motivo y confirmación (`order_release_reason_{id}_{reason}` → `order_release_confirm_{id}_{reason}`).
  - Si `orders.status == PICKED_UP`:
    - "Finalizar pedido" → `order_delivered_confirm_{id}` → pregunta "Ya entregaste?" → `order_delivered_{id}` o `order_delivered_cancel_{id}`.
  - "Entregar siguiente parada" (ruta) → `ruta_entregar_{route_id}_{seq}` (si hay paradas pendientes).
  - "Liberar ruta" → `ruta_liberar_{route_id}` → requiere motivo y confirmación (`ruta_liberar_motivo_{route_id}_{reason}` → `ruta_liberar_confirmar_{route_id}_{reason}`).
- Mientras exista pedido o ruta en curso, el courier no puede aceptar nuevas ofertas (`order_accept_*` / `ruta_aceptar_*`).
  - Al liberar un pedido, se notifica al admin del equipo para revisión del motivo.
  - Al liberar pedido o ruta, el servicio se re-oferta a otros repartidores excluyendo al courier que liberó (no se le vuelve a ofrecer a él).
  - Solo el aliado puede CANCELAR el servicio; el courier solo puede LIBERAR para re-ofertar (con motivo y revisión).

### Helpers de Input Reutilizables (`main.py`)

Cuando 3 o más handlers comparten la misma lógica de validación, se usan helpers:

```python
_handle_phone_input(update, context, storage_key, current_state, next_state, flow, next_prompt)
# Valida mínimo 7 dígitos. Almacena en context.user_data[storage_key].

_handle_text_field_input(update, context, error_msg, storage_key, current_state, next_state, flow, next_prompt)
# Valida que el texto no esté vacío. Almacena en context.user_data[storage_key].

_OPTIONS_HINT  # Constante de texto para opciones de cancelación. SIEMPRE usar la constante.
```

---

## Reglas de Código

### Anti-duplicación (obligatorio antes de escribir)

```bash
# Buscar handlers existentes
git grep "nombre_handler" -- "*.py"

# Buscar callbacks existentes
git grep "callback_prefix_" -- "*.py"

# Buscar funciones
git grep "def nombre_funcion" -- "*.py"
```

### Regla para Mover Funciones a `services.py`

Una función DEBE moverse a `services.py` si:
1. Llama a cualquier función importada de `db.py`
2. Valida roles, permisos o estados de usuario
3. Lee o interpreta configuración desde BD
4. Tiene lógica condicional basada en datos persistidos

### Crear un Nuevo Módulo `.py`

Solo cuando:
1. El dominio es claramente independiente del resto.
2. Agrupa más de 5 funciones cohesivas de ese dominio.
3. El usuario lo aprueba explícitamente.

**PROHIBIDO** crear módulos por conveniencia o para "desahogar" `main.py`.

### Estilo General

- No usar `parse_mode` ni Markdown en mensajes del bot.
- Una función = una sola responsabilidad clara.
- No crear funciones similares o redundantes.
- No introducir nuevos patrones si ya existe uno funcional.
- No reescribir archivos completos sin autorización.

---

## Variables de Entorno

Archivo de referencia: `Backend/.env.example`

| Variable | Descripción | Requerida en |
|----------|-------------|--------------|
| `ENV` | `DEV` o `PROD` | Siempre |
| `BOT_TOKEN` | Token del bot de Telegram | Siempre (distinto por ambiente) |
| `ADMIN_USER_ID` | Telegram ID del admin de plataforma | Siempre |
| `COURIER_CHAT_ID` | ID del grupo de repartidores en Telegram | DEV y PROD |
| `RESTAURANT_CHAT_ID` | ID del grupo de aliados en Telegram | DEV y PROD |
| `DATABASE_URL` | URL de conexión PostgreSQL | DEV y PROD (Railway) |
| `WEB_ADMIN_USER` | Username del admin inicial del panel web | Opcional (default: `admin`) |
| `WEB_ADMIN_PASSWORD` | Contraseña del admin inicial del panel web | Opcional (default: `changeme`) |

**Regla de oro:** NUNCA usar el mismo `BOT_TOKEN` en DEV y PROD simultáneamente.

En PROD: si `DATABASE_URL` no está presente, el sistema debe lanzar error fatal y no arrancar.

---

## Desarrollo y pruebas

> **El bot DEV corre en Railway** (rama `staging`), no en local.
> Para ver cualquier cambio en el bot DEV: **`git push origin staging`**.
> Railway auto-deploya al recibir el push. Ver `Backend/DEPLOY.md`.

### Backend — compilación y verificación (sin necesidad de correr local)

```bash
cd Backend/

# Verificar que el código compila antes de hacer push
python3 -m py_compile main.py db.py order_delivery.py profile_changes.py services.py handlers/states.py handlers/common.py handlers/config.py handlers/quotation.py handlers/location_agenda.py handlers/customer_agenda.py handlers/registration.py handlers/recharges.py handlers/order.py handlers/route.py handlers/admin_panel.py handlers/ally_bandeja.py handlers/courier_panel.py

# Instalar dependencias si se necesita inspeccionar algo localmente
pip install -r requirements.txt
```

### Frontend (Panel Angular)

```bash
cd Frontend/

# Instalar dependencias
npm install

# Servidor de desarrollo (Angular en puerto 4200)
npm start   # equivale a: ng serve

# Build de producción
npm run build

# Ejecutar tests
npm test
```

El backend permite CORS desde `http://localhost:4200` en modo desarrollo.

### Inicializar/Reiniciar Base de Datos (LOCAL)

```bash
cd Backend/
# Inicializar desde cero
python3 -c "from db import init_db; init_db()"

# Inicializar con admin de plataforma
python3 -c "from db import init_db, force_platform_admin; init_db(); force_platform_admin()"
```

---

## Testing

### Tests Automáticos

Los tests están en `tests/` y usan `unittest`:

```bash
cd Backend/
python -m unittest tests/test_recharge_idempotency.py tests/test_status_validation.py

# Output esperado:
# Ran 7 tests in ~2s → OK
```

**Cobertura actual:**
- `test_recharge_idempotency.py`: idempotencia y concurrencia en aprobar/rechazar recargas, carrera approve vs reject.
- `test_status_validation.py`: normalización de estados válidos, rechazo de estados inválidos, protección de `update_recharge_status`.

### Verificación de Compilación (obligatorio tras cambios)

```bash
cd Backend/
python -m py_compile main.py services.py db.py order_delivery.py profile_changes.py
```

### Verificación de Imports Huérfanos

Tras mover o eliminar funciones:

```bash
git grep "nombre_funcion" -- "*.py"
# Si solo aparece en el bloque import → importación huérfana, eliminar
```

---

## Despliegue

### Arquitectura: dos servicios Railway permanentes

| Ambiente | Rama git | Trigger de deploy |
|----------|----------|-------------------|
| **DEV** | `staging` | `git push origin staging` |
| **PROD** | `main` | `git push origin main` (o merge staging→main) |

Para reglas obligatorias de ramas y despliegue, ver `AGENTS.md`.
Este documento solo resume cómo se reflejan los cambios en DEV y remite a `Backend/DEPLOY.md` para el detalle operativo.

### Railway (ambos servicios)

- **Motor**: `worker: python3 main.py` (Procfile)
- **Variables**: configurar en el dashboard de Railway por servicio (sin `.env`)
- **Base de datos**: PostgreSQL con `DATABASE_URL` (cada servicio tiene la suya)
- DEV y PROD usan **BOT_TOKEN distintos** — nunca el mismo token en ambos

### Docker

```bash
cd Backend/
docker build -t domi-backend .
docker run --env-file .env domi-backend
```

### API Web (FastAPI)

La API corre con Uvicorn (incluido en `requirements.txt`):

```bash
cd Backend/
uvicorn web_app:app --reload --port 8000
```

Endpoints principales:
- `GET /` — Health check HTML
- `POST /admin/users/{user_id}/approve` — Aprobar usuario (requiere rol admin)
- Endpoints de `/users/` y `/dashboard/`

CORS configurado para permitir `http://localhost:4200` en desarrollo.

---

## Git y Ramas

### Estructura de Ramas

Las reglas normativas de ramas viven en `AGENTS.md`.
Aquí solo se mantiene un resumen explicativo de las ramas que existen hoy en el repositorio:

| Rama/Prefijo | Tipo | Uso actual |
|---|---|---|
| `main` | Permanente | Producción (Railway PROD) |
| `staging` | Permanente | Integración y trabajo diario |
| `claude/` | Temporal | Ramas temporales de asistentes |
| `verify/` | Temporal | Validaciones acotadas, especialmente de BD |
| `luisa-web` | Permanente | Rama de trabajo de la colaboradora Luisa |

### Flujo de Trabajo

```
staging   ──(validado)──►  main
verify/*  ──merge──►  staging  ──(validado)──►  main
                        (entorno DEV:
                         BOT_TOKEN DEV
                         DATABASE_URL separada)
```

Para el flujo obligatorio de trabajo y merge, ver `AGENTS.md`.
Aquí basta con recordar que el entorno DEV se alimenta desde `staging` y que la validación funcional ocurre antes de promover cambios a `main`.

### Verificación de Compatibilidad Estructural (Obligatorio Antes de Merge)

Las validaciones obligatorias antes de merge están definidas en `AGENTS.md`.
Esta sección conserva solo los comandos de referencia para inspeccionar compatibilidad estructural cuando haga falta.

```bash
# 1. Verificar que la rama fue creada desde origin/main
git log --oneline origin/main..nombre-rama

# 2. Comparar estructura de archivos
git diff origin/main nombre-rama -- --name-only

# 3. Si los paths difieren → ABORTAR
git merge --abort
```

Si hay incompatibilidad estructural:
1. Abortar el merge.
2. Crear nueva rama desde `origin/main`: `git checkout -b claude/apply-[nombre]-[ID] origin/main`
3. Analizar commits de la rama incompatible uno por uno: `git show [hash]`
4. Aplicar los cambios manualmente sobre los paths correctos de `main`.
5. Compilar y merge normal.

### Checklist Pre-merge a `main`

Obligatorio cuando el cambio afecta BD, migraciones, `init_db()`, flujos críticos o sistema de recargas:

1. Compilación sin errores: `python -m py_compile ...`
2. No duplicaciones: `git grep` limpio
3. Arranque sin crash, tablas creadas, inserciones reales funcionan
4. `DATABASE_URL` presente en PROD
5. Verificación funcional: `/start`, `/menu`, registro real, cambio de estado
6. Evidencia documentada antes de merge (cuando afecte BD o flujos críticos)

---

## Gestión de Roles (Panel Web - FastAPI)

### Multi-usuario (IMPLEMENTADO 2026-03-13)

El panel soporta múltiples usuarios con roles distintos. Los usuarios se almacenan en `web_users` con contraseñas hasheadas con **bcrypt**.

**Roles del panel:**

| Rol | Valor en BD | Acceso |
|-----|-------------|--------|
| Admin Plataforma | `ADMIN_PLATFORM` | Datos globales + gestión de usuarios del panel |
| Admin Local | `ADMIN_LOCAL` | Datos filtrados por su equipo (admin_id) |

**Flujo de autenticación:**
1. `POST /auth/login` verifica bcrypt → retorna `{ token, username, role }`
2. Frontend guarda `admin_token`, `admin_username`, `admin_role` en localStorage
3. `AuthService` (Angular) lee `admin_role` y mantiene permisos en signals
4. `RoleGuard` (`role.guard.ts`) protege rutas por permiso (ej. `manage_settings`)
5. `AuthGuard` verifica presencia del token; si no existe, llama `authService.clear()` y redirige a login

**Seeding del admin inicial:**
- `ensure_web_admin()` en `db.py` crea el usuario `ADMIN_PLATFORM` al arrancar la app si no existe.
- Credenciales desde variables de entorno `WEB_ADMIN_USER` / `WEB_ADMIN_PASSWORD`.
- Es idempotente: no sobreescribe si ya existe.
- Llamado en `web_app.py` al arrancar: `init_db(); ensure_web_admin()`.

**Scoping de datos por rol (`_scoped_admin_id` en `web/api/admin.py`):**
- `ADMIN_PLATFORM` → `admin_id = None` → datos globales
- `ADMIN_LOCAL` → `admin_id = current_user.admin_id` → datos del equipo

**Endpoints de gestión de usuarios del panel (solo `ADMIN_PLATFORM`):**
- `GET /admin/web-users` — lista todos los usuarios del panel
- `POST /admin/web-users` — crea nuevo usuario (username, password, role, admin_id opcional)
- `PATCH /admin/web-users/{id}/status` — activa (`APPROVED`) o inactiva (`INACTIVE`) un usuario

**Funciones nuevas en `db.py` (re-exportadas en `services.py`):**
- `create_web_user(username, password_hash, role, admin_id)` → int
- `get_web_user_by_username(username)` → row
- `get_web_user_by_id(user_id)` → row
- `list_web_users()` → list[row]
- `update_web_user_status(user_id, status)`
- `update_web_user_password(user_id, password_hash)`
- `ensure_web_admin()` — seed idempotente desde env vars

**Frontend Angular:**
- `AuthService` (`core/services/auth.service.ts`) — mantiene `_role` y `_permissions` como signals, mapa estático `ROLE_PERMISSIONS` espejo del backend, métodos: `setUser(role)`, `hasPermission(perm)`, `isPlatformAdmin()`, `clear()`
- `RoleGuard` (`core/guards/role.guard.ts`) — guard funcional `CanActivateFn`, lee `route.data[‘requiredPermission’]`
- Rutas protegidas con `requiredPermission: ‘manage_settings’`: `settings` y `administradores`
- Sidebar: items "Administradores" y "Configuración" visibles solo si `authService.isPlatformAdmin()`

**Permisos por rol (frontend y backend son espejo):**

| Permiso | ADMIN_PLATFORM | ADMIN_LOCAL |
|---------|:-:|:-:|
| `view_dashboard` | ✓ | ✓ |
| `view_users` | ✓ | ✓ |
| `approve_user` | ✓ | ✓ |
| `reject_user` | ✓ | — |
| `deactivate_user` | ✓ | ✓ |
| `reactivate_user` | ✓ | ✓ |
| `view_couriers_map` | ✓ | ✓ |
| `view_unassigned_orders` | ✓ | ✓ |
| `manage_settings` | ✓ | — |

---

### Roles y grupos (código existente)

La capa web tiene su propio modelo de roles/estados independiente del bot:

```python
# web/users/roles.py
PLATFORM_ADMIN_ONLY = {UserRole.PLATFORM_ADMIN}
ADMIN_ALLOWED = {UserRole.PLATFORM_ADMIN, UserRole.ADMIN_LOCAL}
COURIER_ONLY = {UserRole.COURIER}
ALLY_ONLY = {UserRole.ALLY}
CAN_OPERATE_ORDERS = {UserRole.COURIER, UserRole.ADMIN_LOCAL, UserRole.PLATFORM_ADMIN}
```

Guards disponibles en `web/auth/guards.py`:
- `is_admin(user)` → verifica si tiene rol administrativo
- `can_access_system(user)` → verifica si el estado le permite operar
- `is_blocked(user)` → verifica si está bloqueado

---

## Convenciones de Código

### Python (Backend)

- Python 3.11+ (según Dockerfile)
- Sin type hints en código existente (no agregar innecesariamente)
- Sin f-strings de Markdown en mensajes del bot (prohibido `parse_mode`)
- Imports agrupados: stdlib → terceros → locales
- Funciones de BD retornan `dict` (RealDictCursor en Postgres, Row con acceso por clave en SQLite)
- **Datetimes UTC**: usar `datetime.now(timezone.utc).replace(tzinfo=None)` — NUNCA `datetime.utcnow()` (deprecated Python 3.12+). El `.replace(tzinfo=None)` mantiene el datetime "naive" que espera el resto del código y la BD. Limpieza completa:
  - 2026-03-13: `db.py`, `order_delivery.py`, `main.py` (limpieza inicial).
  - 2026-03-17: `main.py` — eliminado lazy `import datetime` dentro de función; añadido `from datetime import datetime, timezone` al bloque de imports stdlib (top-level). Docstring de `order_delivery.py:_get_order_durations` actualizado para no mencionar la API deprecated.

### TypeScript/Angular (Frontend)

- Angular 21 con standalone components
- SSR habilitado con `@angular/ssr`
- Prettier configurado: `printWidth: 100`, `singleQuote: true`
- Tests con vitest (no Jest ni Karma)
- Separación en: `core/` (guards, interceptors, services) y `features/` (vistas)

---

## Sistema de Recargas (Reglas Críticas)

El sistema de recargas transfiere saldo del Admin hacia Repartidores/Aliados. Es el componente financiero más crítico.

### Reglas de Integridad
- Toda aprobación/rechazo es **idempotente**: no se puede procesar dos veces la misma solicitud.
- En concurrencia (approve vs reject simultáneos), **solo una operación gana**.
- Actualización de balance + registro en ledger son **atómicos** (misma transacción).
- Solo el Admin propietario puede aprobar recargas a su equipo.

### Estados de Recarga

| Transición | Efecto |
|-----------|--------|
| `PENDING` → `APPROVED` | Balance transferido, ledger registrado |
| `PENDING` → `REJECTED` | Sin cambio de balance ni ledger |
| `APPROVED` / `REJECTED` | Estado terminal. **PROHIBIDO** cambiar. |

### Verificación Obligatoria Antes de Aprobar
```python
# Verificar que el estado sigue siendo PENDING (SELECT FOR UPDATE en Postgres)
# Si ya cambió: retornar (False, "Ya procesado") sin tocar nada
```

Los estados usan `normalize_role_status()` antes de persistir. **PROHIBIDO** modificar balance sin registro en ledger.

### Modelo de Contabilidad de Doble Entrada

El sistema implementa contabilidad de doble entrada. El Admin de Plataforma no tiene saldo ilimitado; debe registrar ingresos externos antes de poder aprobar recargas.

**Flujo de fondos:**

```
Pago externo (transferencia/efectivo)
  → register_platform_income(admin_id, amount, method, note)  [db.py]
  → admins.balance += amount
  → ledger: kind=INCOME | from_type=EXTERNAL | from_id=0 → to_type=PLATFORM/ADMIN

Admin aprueba recarga a repartidor o aliado
  → approve_recharge_request()  [services.py]
  → admins.balance -= amount
  → admin_couriers.balance o admin_allies.balance += amount
  → ledger: kind=RECHARGE | from_type=PLATFORM/ADMIN | from_id=admin_id → to_type=COURIER/ALLY
```

Las restricciones obligatorias de contabilidad y saldo están en `AGENTS.md`.
Aquí se documenta el modelo funcional ya implementado y los puntos donde ese comportamiento vive.

**Flujo de UI — Registrar ingreso externo** (`ingreso_conv`, `main.py`):
- Estados: `INGRESO_MONTO=970`, `INGRESO_METODO=971`, `INGRESO_NOTA=972`
- Prefijo callbacks: `ingreso_`
- Claves user_data: `ingreso_monto`, `ingreso_metodo`
- Función en db.py: `register_platform_income(admin_id, amount, method, note)`
- Re-exportada en services.py; importada en main.py desde services.py

### Recarga Directa con Plataforma como Fallback

Un aliado o repartidor puede siempre solicitar recarga directamente al Admin de Plataforma, aunque pertenezca a un equipo de Admin Local. Los casos habilitados son:
1. El Admin Local no tiene saldo suficiente.
2. El Admin Local no responde o no procesa la recarga.

**Regla del interruptor de ganancias:**
El saldo recargado pertenece a quien lo aportó. Las ganancias generadas por ese saldo fluyen hacia el mismo aportante:
- Saldo aportado por Admin Local → ganancias al Admin Local.
- Saldo aportado por Plataforma → ganancias a Plataforma.

Al agotarse el saldo de plataforma y recargar nuevamente con el Admin Local, el flujo de ganancias vuelve al Admin Local. El Admin Local que no recarga a tiempo pierde las ganancias de ese usuario mientras el saldo activo provenga de plataforma.

**Implementación técnica (IMPLEMENTADO 2026-03-03):**
- `main.py → recargar_monto`: muestra "Plataforma" siempre para COURIER/ALLY.
- `main.py → recargar_admin_callback`: permite `platform_id` aunque no esté en `approved_links`. Detecta admin PENDING y redirige a Plataforma.
- `services.py → approve_recharge_request`: cuando Plataforma aprueba para COURIER/ALLY, crea o actualiza un vínculo directo `admin_couriers`/`admin_allies` con `admin_id = platform_id`. El vínculo plataforma queda `APPROVED`; todos los otros vínculos del usuario quedan `INACTIVE`. Ledger registra `PLATFORM → COURIER/ALLY`. Cuando Admin Local re-recarga, el vínculo local pasa a `APPROVED` y plataforma a `INACTIVE` (interruptor).
- `db.py → _sync_courier_link_status` y `_sync_ally_link_status`: usan `updated_at DESC` (no `created_at`) para determinar el vínculo activo en cambios de estado. Garantiza que el vínculo del último financiador siempre sea el activo.

**Restricciones absolutas:**
- PROHIBIDO bloquear la opción plataforma por ausencia de vínculo `admin_couriers`/`admin_allies`.
- PROHIBIDO aprobar si `admins.balance` (plataforma) < monto solicitado.
- Todo movimiento debe registrarse en ledger con el origen correcto.

### Red Cooperativa — Todos los Couriers para Todos los Aliados (IMPLEMENTADO 2026-03-03)

La plataforma opera como una **red cooperativa**: cualquier repartidor activo (de cualquier admin) puede tomar pedidos de cualquier aliado (de cualquier admin). No existen equipos aislados.

**Regla de elegibilidad:**
- `get_eligible_couriers_for_order` en `db.py` NO filtra por `admin_id`. Retorna todos los repartidores con `admin_couriers.status = 'APPROVED'` y `couriers.status = 'APPROVED'`.
- El parámetro `admin_id` existe pero es opcional (`admin_id=None`) y se ignora en la query.

**Modelo de comisiones (simétrico):**
- Aliado crea pedido → fee $300 al aliado al entregar (o al expirar sin courier) → $200 al admin del aliado, $100 a Plataforma.
- Courier entrega pedido → fee $300 al courier → $200 al admin del courier, $100 a Plataforma.
- Cada admin gana $200 por cada servicio de sus propios miembros, sin importar con quién interactúan.
- Si el admin es Plataforma: gana los $300 completos (no hay split).
- Pedidos creados por admin (admin_pedido): **el admin creador no paga fee**; solo paga el courier que entrega ($200 su admin, $100 a Plataforma).

**Flujo técnico post-implementación:**
```
Aliado (Admin A) crea pedido
  → publish_order_to_couriers(admin_id=A)
  → check_service_fee_available(ALLY, ally_id, admin_id=A)   # verifica que aliado tenga $300
  → get_eligible_couriers_for_order(ally_id=X)               # Sin filtro → TODOS los couriers activos
  → Para cada courier: get_approved_admin_id_for_courier(courier_id) → courier_admin_id
    → check_service_fee_available(COURIER, courier_id, courier_admin_id)
    → Solo pasan couriers con saldo en su propio admin ($300 mínimo)

Courier (Admin B) acepta
  → courier_admin_id_snapshot = B (guardado en orders al aceptar)

Courier entrega
  → apply_service_fee(ALLY, ally_id, admin_id=A)
      admin_allies.balance(aliado) −$300 | admins.balance(Admin A) +$200 | admins.balance(Plataforma) +$100
  → apply_service_fee(COURIER, courier_id, admin_id=B)
      admin_couriers.balance(courier) −$300 | admins.balance(Admin B) +$200 | admins.balance(Plataforma) +$100
```

**Archivos modificados:**
- `db.py → get_eligible_couriers_for_order`: sin filtro `AND ac.admin_id = {P}`, `params = []`
- `order_delivery.py → publish_order_to_couriers`: fee check usa `get_approved_admin_id_for_courier(courier_id)` por courier; elimina lógica de `admin_without_balance` global
- `order_delivery.py → _handle_delivered`: `ally_admin_id` desde `get_approved_admin_link_for_ally`; `courier_admin_id` desde `order["courier_admin_id_snapshot"]` con fallback a `get_approved_admin_link_for_courier`; cada fee usa su propio admin; balance post-fee usa `courier_admin_id`

---

### Sincronización de Estado en Tablas de Vínculo

`admin_allies.status` y `admin_couriers.status` son campos independientes de `allies.status` y `couriers.status`. Ambos **siempre deben estar sincronizados**.

**Bug síntoma:** "No hay admins disponibles para procesar recargas" al intentar recargar un aliado/repartidor recién aprobado. Ocurre cuando `allies.status = APPROVED` pero `admin_allies.status` sigue en `PENDING`.

**Solución implementada — helpers en `db.py`:**
- `_sync_ally_link_status(cur, ally_id, status, now_sql)`: sincroniza `admin_allies.status` al final de cada actualización de estado de aliado.
- `_sync_courier_link_status(cur, courier_id, status, now_sql)`: ídem para repartidores.
- Ambos se llaman dentro de `update_ally_status()`, `update_ally_status_by_id()`, `update_courier_status()`, `update_courier_status_by_id()`, antes de `conn.commit()`.

**Comportamiento del sync:**
- Si `status == "APPROVED"`: el vínculo más recientemente actualizado (por `updated_at DESC`) → `APPROVED`; el resto → `INACTIVE`. El `updated_at` se actualiza en cada recarga, por lo que el último financiador es siempre el equipo activo.
- Si `status != "APPROVED"`: todos los vínculos del usuario → `INACTIVE`.

---

## Sistema de Tracking de Llegada (order_delivery.py)

Implementado en commit `b06fc3e`. Controla el ciclo post-aceptación del courier hasta la confirmación de llegada al punto de recogida.

### Flujo completo

```
Oferta publicada → courier acepta
  ↓ _handle_accept
  - Mensaje SIN datos del cliente (solo barrio destino + tarifa + pickup address)
  - Mensaje incluye instruccion explicita: navegar al pickup (Google Maps/Waze) y liberar si no puede llegar
  - Guarda courier_accepted_lat/lng en orders (base para T+5)
  - Programa 3 jobs:
      arr_inactive_{id}  T+5 min
      arr_warn_{id}      T+15 min
      arr_deadline_{id}  T+20 min

  T+5:  ¿Movimiento ≥50m hacia pickup? No → _release_order_by_timeout
  T+15: Notificar aliado (Buscar otro / Llamar / Seguir esperando) + advertir courier
  T+20: _release_order_by_timeout automático

  (En paralelo, cada live location update llama check_courier_arrival_at_pickup)
  GPS detecta ≤100m del pickup:
    → set_courier_arrived (idempotente)
    → _cancel_arrival_jobs (cancela T+5/T+15/T+20)
    → upsert_order_pickup_confirmation(PENDING)
    → _notify_ally_courier_arrived (botones: Confirmar / No ha llegado)

  Aliado confirma (order_pickupconfirm_approve_):
    → _handle_pickup_confirmation_by_ally(approve=True)
    → status = PICKED_UP
    → _notify_courier_pickup_approved → courier recibe customer_name/phone/address exacta (en oferta solo ve mapas + ciudad/barrio)
```

- Para rutas: `order_delivery.py → _handle_route_accept` también incluye instrucción de navegación al pickup (Google Maps/Waze) y opción de liberar ruta.

### Constantes (order_delivery.py)

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `ARRIVAL_INACTIVITY_SECONDS` | 300 (5 min) | Timeout de inactividad Rappi-style |
| `ARRIVAL_WARN_SECONDS` | 900 (15 min) | Notificación al aliado |
| `ARRIVAL_DEADLINE_SECONDS` | 1200 (20 min) | Auto-liberación |
| `ARRIVAL_RADIUS_KM` | 0.1 (100 m) | Radio de detección de llegada |
| `ARRIVAL_MOVEMENT_THRESHOLD_KM` | 0.05 (50 m) | Movimiento mínimo hacia pickup en T+5 |

### Funciones nuevas en order_delivery.py

| Función | Descripción |
|---------|-------------|
| `check_courier_arrival_at_pickup(courier_id, lat, lng, context)` | Pública. Llamada desde main.py en cada live location |
| `_cancel_arrival_jobs(context, order_id)` | Cancela los 3 jobs por nombre |
| `_release_order_by_timeout(order_id, courier_id, context, reason)` | Liberación centralizada (T+5 y T+20) |
| `_arrival_inactivity_job(context)` | Job T+5 |
| `_arrival_warn_ally_job(context)` | Job T+15 |
| `_arrival_deadline_job(context)` | Job T+20 |
| `_notify_ally_courier_arrived(context, order, courier_name)` | Notificación al aliado con botones |
| `_handle_find_another_courier(update, context, order_id)` | Callback aliado busca otro |
| `_handle_wait_courier(update, context, order_id)` | Callback aliado sigue esperando |

### Nuevas columnas en `orders`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `courier_arrived_at` | SQLite: TEXT / Postgres: TIMESTAMP | Timestamp cuando GPS detecta llegada (≤100m). NULL = no llegó aún |
| `courier_accepted_lat` | REAL | Latitud del courier al momento de aceptar (base para T+5) |
| `courier_accepted_lng` | REAL | Longitud del courier al momento de aceptar (base para T+5) |

### Nuevas funciones en db.py

- `set_courier_arrived(order_id)` — idempotente, solo actúa si `courier_arrived_at IS NULL`
- `set_courier_accepted_location(order_id, lat, lng)` — guarda posición al aceptar
- `get_active_order_for_courier(courier_id)` — retorna orden activa del courier (`ACCEPTED`/`PICKED_UP`)
- `get_active_route_for_courier(courier_id)` — retorna ruta activa del courier (`ACCEPTED`)

Re-exportadas en `services.py`.

### Pendientes (NO implementado aún)

- Cuenta regresiva visible (countdown) en la oferta/estado post-aceptación.
- Botón explícito "Llegué" para courier (hoy es detección automática por live location).
- Persistencia fuerte ante reinicios: los jobs T+5/T+15/T+20 y `excluded_couriers` viven en memoria (`context.bot_data`) y se pierden si el proceso se reinicia.

---

## Sistema de Incentivos (order_delivery.py + main.py)

### Incentivo al crear pedido (aliado)

Disponible en el flujo de creación de pedido (`nuevo_pedido_conv`). Antes de confirmar, el aliado puede agregar un incentivo adicional con botones fijos (+$1.000, +$1.500, +$2.000, +$3.000) o monto libre.

- Estado: `PEDIDO_INCENTIVO_MONTO = 60`
- ConversationHandler: `pedido_incentivo_conv` (entry point: `pedido_add_incentivo_{id}`)
- DB: `add_order_incentive(order_id, delta)` en `db.py`, re-exportada en `services.py`
- `ally_increment_order_incentive(telegram_id, order_id, delta)` en `services.py`

### Ciclo de pedido actualizado (IMPLEMENTADO 2026-03-09)

**Ciclo de pedido**

0 min → pedido publicado  
5 min → sugerencia de incentivo adicional  
10 min → expiración automática  

**Cancelación del aliado**

≤60 segundos desde creación → cancelación sin costo  
>60 segundos desde creación → cobro de $300  
Expiración automática → cobro de $300  
Pedidos creados por administrador (ally_id = None) → nunca se cobra comisión  

### Sugerencia T+5 — "Nadie ha tomado el pedido" (IMPLEMENTADO 2026-03-06)

Aplica a **todos los pedidos** (aliado y admin). 5 minutos después de publicar el pedido, si sigue en status `PUBLISHED` (ningún courier lo aceptó), se envía un mensaje al creador sugiriendo agregar incentivo.

**Constante:** `OFFER_NO_RESPONSE_SECONDS = 300` (order_delivery.py)

**Flujo:**
1. `publish_order_to_couriers()` programa job `offer_no_response_{order_id}` con T+5.
2. Al dispararse: `_offer_no_response_job(context)` — verifica que el pedido siga en `PUBLISHED`, obtiene `telegram_id` del creador (aliado o admin), envía mensaje con botones.
3. Si courier acepta antes del T+5: `_cancel_no_response_job(context, order_id)` cancela el job.
4. Si aliado/admin cancela el pedido: también se cancela el job.
5. La sugerencia es única (no se repite si el admin no agrega incentivo).

**Botones de la sugerencia:** `offer_inc_{id}x1500`, `offer_inc_{id}x2000`, `offer_inc_{id}x3000`, `offer_inc_otro_{id}`

**Al agregar incentivo desde la sugerencia:**
- `offer_suggest_inc_fixed_callback` (patrón `^offer_inc_\d+x(1500|2000|3000)$`)
- `offer_suggest_inc_otro_start` → estado `OFFER_SUGGEST_INC_MONTO = 915` → `offer_suggest_inc_monto_handler`
- Llama `ally_increment_order_incentive` o `admin_increment_order_incentive` según tipo de pedido
- Llama `repost_order_to_couriers(order_id, context)` → re-oferta a todos los couriers activos + reinicia T+5

**Re-oferta (`repost_order_to_couriers`):**
- Limpia `excluded_couriers` del `bot_data` para ese pedido
- Llama `clear_offer_queue(order_id)` (borra queue en BD)
- Llama `publish_order_to_couriers(order_id, ally_id, context, skip_fee_check=True, ...)`
- `skip_fee_check=True` omite verificación de saldo (ya verificada al crear el pedido)

**Funciones clave:**
- `order_delivery.py`: `_cancel_no_response_job`, `_offer_no_response_job`, `repost_order_to_couriers`
- `main.py`: `offer_suggest_inc_fixed_callback`, `offer_suggest_inc_otro_start`, `offer_suggest_inc_monto_handler`, `offer_suggest_inc_conv`
- `services.py`: `admin_get_order_for_incentive(telegram_id, order_id)`, `admin_increment_order_incentive(telegram_id, order_id, delta)`
- `db.py`: `clear_offer_queue(order_id)`

---

## Pedido Especial del Admin (IMPLEMENTADO 2026-03-06)

Permite a un Admin Local o Admin de Plataforma crear pedidos directamente, con tarifa libre (sin cálculo automático) y sin débito de saldo.

### Características

- **Sin fee al admin creador**: el admin no paga comisión por crear el pedido. El courier que lo entrega sí paga su fee normal ($300).
- **Sin fee check del aliado**: no hay aliado, `ally_id=NULL`, `skip_fee_check=True` omite la verificación de saldo.
- **Tarifa manual**: el admin ingresa el monto que pagará al courier.
- **Sin débito de saldo al admin**: el pago de la tarifa al courier se maneja fuera del sistema.
- **`creator_admin_id`**: nueva columna en `orders` que identifica al admin creador (NULL = pedido de aliado).
- **`ally_id = NULL`**: los pedidos especiales de admin no tienen `ally_id`.
- **Direcciones de recogida**: el admin gestiona sus propias ubicaciones de pickup en `admin_locations`.
- **Incentivos opcionales**: se pueden agregar incentivos (+$1.500/+$2.000/+$3.000/libre) antes de publicar.
- **T+5 aplica igual**: si nadie acepta en 5 min, recibe la sugerencia de incentivo.

### Tabla `admin_locations`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | BIGSERIAL/INTEGER | PK |
| `admin_id` | BIGINT | FK → admins.id |
| `label` | TEXT | Nombre/etiqueta de la ubicación |
| `address` | TEXT | Dirección completa |
| `city` | TEXT | Ciudad |
| `barrio` | TEXT | Barrio |
| `phone` | TEXT | Teléfono del punto (opcional) |
| `lat` | REAL | Latitud |
| `lng` | REAL | Longitud |
| `is_default` | INTEGER | 1 = default del admin |
| `use_count` | INTEGER | Contador de usos |
| `is_frequent` | INTEGER | 1 = dirección frecuente |
| `last_used_at` | TIMESTAMP | Última vez usada |
| `created_at` | TIMESTAMP | Fecha de creación |

### Funciones en `db.py`

- `create_admin_location(admin_id, label, address, city, barrio, phone=None, lat=None, lng=None) → int`
- `get_admin_locations(admin_id) → list`
- `get_admin_location_by_id(location_id, admin_id) → dict`
- `get_default_admin_location(admin_id) → dict`
- `set_default_admin_location(location_id, admin_id)`
- `increment_admin_location_usage(location_id, admin_id)`

Todas re-exportadas en `services.py`.

### Flujo de creación (`admin_pedido_conv` en `main.py`)

```
Entry: callback admin_nuevo_pedido
  → admin_nuevo_pedido_start()
  → Estado ADMIN_PEDIDO_PICKUP (908)

ADMIN_PEDIDO_PICKUP:
  admin_pedido_pickup_callback  → selecciona ubicación guardada → ADMIN_PEDIDO_CUST_NAME
  admin_pedido_nueva_dir_start  → pide texto → ADMIN_PEDIDO_PICKUP
  admin_pedido_pickup_text_handler → geocodifica → muestra confirmación
  admin_pedido_geo_pickup_callback (si/no) → confirma pickup → ADMIN_PEDIDO_CUST_NAME
  admin_pedido_pickup_gps_handler → guarda GPS → ADMIN_PEDIDO_CUST_NAME

ADMIN_PEDIDO_CUST_NAME (909): admin_pedido_cust_name_handler → ADMIN_PEDIDO_CUST_PHONE
ADMIN_PEDIDO_CUST_PHONE (910): admin_pedido_cust_phone_handler → ADMIN_PEDIDO_CUST_ADDR

ADMIN_PEDIDO_CUST_ADDR (911):
  admin_pedido_cust_addr_handler → geocodifica → muestra confirmación
  admin_pedido_geo_callback (si/no) → confirma → ADMIN_PEDIDO_TARIFA
  admin_pedido_cust_gps_handler → guarda GPS → ADMIN_PEDIDO_TARIFA

ADMIN_PEDIDO_TARIFA (912): admin_pedido_tarifa_handler → ADMIN_PEDIDO_INSTRUC

ADMIN_PEDIDO_INSTRUC (913):
  admin_pedido_instruc_handler / admin_pedido_sin_instruc_callback → preview
  admin_pedido_inc_fijo_callback (1500/2000/3000) → actualiza preview
  admin_pedido_inc_otro_callback → ADMIN_PEDIDO_INC_MONTO
  admin_pedido_confirmar_callback → crea pedido → publica → END

ADMIN_PEDIDO_INC_MONTO (916): admin_pedido_inc_monto_handler → preview → ADMIN_PEDIDO_INSTRUC
```

### Estados

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `ADMIN_PEDIDO_PICKUP` | 908 | Selección de punto de recogida |
| `ADMIN_PEDIDO_CUST_NAME` | 909 | Nombre del cliente |
| `ADMIN_PEDIDO_CUST_PHONE` | 910 | Teléfono del cliente |
| `ADMIN_PEDIDO_CUST_ADDR` | 911 | Dirección de entrega (con geocoding) |
| `ADMIN_PEDIDO_TARIFA` | 912 | Tarifa manual al courier |
| `ADMIN_PEDIDO_INSTRUC` | 913 | Instrucciones + preview final |
| `OFFER_SUGGEST_INC_MONTO` | 915 | Monto libre en sugerencia T+5 |
| `ADMIN_PEDIDO_INC_MONTO` | 916 | Monto libre de incentivo en creación admin |

### User data keys del flujo (prefijo `admin_ped_`)

| Clave | Contenido |
|-------|-----------|
| `admin_ped_admin_id` | ID interno del admin en DB |
| `admin_ped_pickup_id` | ID de admin_location (None si GPS/nueva) |
| `admin_ped_pickup_addr` | Dirección de recogida (texto) |
| `admin_ped_pickup_lat/lng` | Coordenadas de recogida |
| `admin_ped_pickup_city/barrio` | Ciudad/barrio de recogida |
| `admin_ped_geo_pickup_pending` | Dict con geo pendiente de confirmar (pickup) |
| `admin_ped_cust_name/phone/addr` | Datos del cliente |
| `admin_ped_dropoff_lat/lng` | Coordenadas de entrega |
| `admin_ped_dropoff_city/barrio` | Ciudad/barrio de entrega |
| `admin_ped_geo_cust_pending` | Dict con geo pendiente de confirmar (entrega) |
| `admin_ped_tarifa` | Tarifa manual (int, COP) |
| `admin_ped_incentivo` | Incentivo adicional (int, COP, default 0) |
| `admin_ped_instruc` | Instrucciones para el courier |

### Publicación del pedido admin

En `admin_pedido_confirmar_callback`:
1. `create_order(ally_id=None, creator_admin_id=admin_id, ...)` — crea el pedido
2. `publish_order_to_couriers(order_id, None, context, admin_id_override=admin_id, skip_fee_check=True)` — publica a todos los couriers activos
3. `increment_admin_location_usage(pickup_location_id, admin_id)` — si ubicación guardada

**Nota:** `skip_fee_check=True` omite la verificación previa de saldo del aliado (no hay aliado). El courier que acepta el pedido sí paga su fee normal al entregar ($300 → $200 a su admin, $100 a Plataforma). El admin creador no paga ninguna comisión.

---

## Cotizador y Uso de APIs (Control de Costos)

El cotizador usa **Google Maps API** (Distance Matrix / Places). Tiene cuota diaria limitada.

### Regla de Cuota
- **PROHIBIDO** llamar a la API sin verificar `api_usage_daily` primero.
- Si `api_usage_daily >= límite`: retornar error informativo, **no llamar** a la API.
- Toda llamada debe incrementar `api_usage_daily` de forma atómica.

### Costeo por Operación (Google Maps) — IMPLEMENTADO

Además del fusible diario (`api_usage_daily`), existe tracking por evento para estimar costo promedio por tipo de operación:

- Tabla: `api_usage_events` (SQLite y PostgreSQL).
- Inserción oficial: `Backend/db.py:record_api_usage_event()` (INSERT en `api_usage_events` + incrementa `api_usage_daily` en la misma transacción).
- Instrumentación centralizada: `Backend/services.py` registra eventos en:
  - `google_place_details()` → `place_details`
  - `google_geocode_forward()` → `geocode_forward`
  - `google_places_text_search()` → `places_text_search`
  - `get_distance_from_api_coords()` → `distance_matrix_coords`
  - `get_distance_from_api()` → `distance_matrix_text`
- Estimación de costo por variables de entorno (valores en USD por llamada):
  - `GOOGLE_COST_USD_PLACE_DETAILS`
  - `GOOGLE_COST_USD_GEOCODE_FORWARD`
  - `GOOGLE_COST_USD_PLACES_TEXT_SEARCH`
  - `GOOGLE_COST_USD_DISTANCE_MATRIX_COORDS`
  - `GOOGLE_COST_USD_DISTANCE_MATRIX_TEXT`
- Privacidad: **PROHIBIDO** guardar direcciones/coords o cualquier PII en `api_usage_events.meta_json`. Solo metadata no sensible (status, provider, mode).
- Helper de consulta rápida: `Backend/services.py:get_google_maps_cost_summary(days=7)`.

### Regla de Caché
- Distancias entre pares de coordenadas **deben cachearse** en base de datos.
- **PROHIBIDO** recalcular una distancia ya cacheada para la misma consulta.

### Regla de Geocodificación
- Coordenadas (lat/lng) se capturan vía Telegram (ubicación GPS). La API solo se usa para geocodificación inversa o búsqueda de direcciones escritas.
- **PROHIBIDO** usar la API para validar ubicaciones que ya tienen GPS válido.
- Todo flujo que reciba direcciones por texto (cotizar, pedido, pickup, ruta) debe reutilizar el pipeline de resolución de cotización: `resolve_location(texto)` + confirmación de candidato geocodificado (si/no) + fallback con `resolve_location_next(...)` antes de exigir GPS.

### Manejo de Errores de API
- Si la API falla: retornar error claro al usuario. **PROHIBIDO** propagar excepciones sin capturar ni reintentar automáticamente.

---

## Flujo de Trabajo con IA

### Donde documentar

Regla de routing — tabla completa en **AGENTS.md Sección 16**.

Regla de cambios estructurales — tabla completa en **AGENTS.md Sección 17**:
todo cambio estructural (nueva tabla, módulo, variable de entorno, callback, flow)
debe documentarse en la sección correspondiente de este archivo **en el mismo commit**.
El `git log` es el historial cronológico. CLAUDE.md es la referencia de estado actual.

Regla de routing — tabla completa en **AGENTS.md Sección 16**:

| Contenido | Destino |
|-----------|--------|
| Regla, restricción, protocolo obligatorio | `AGENTS.md` |
| Arquitectura, flujo, convención operativa | `CLAUDE.md` |
| Sesión activa o cierre de agente | `WORKLOG.md` |
| Regla + detalle operativo | `AGENTS.md` (regla) + `CLAUDE.md` (detalle) |

Si el contenido ya está cubierto en AGENTS.md: CLAUDE.md solo agrega referencia o comandos, nunca repite.

### Colaboración entre Agentes IA (Claude Code y Codex)

Luis Felipe trabaja en VS Code con múltiples agentes activos simultáneamente: **Claude Code** y **Codex**.
En ocasiones ambos agentes trabajan al mismo tiempo sobre la misma rama (`staging`).
Las reglas completas están en `AGENTS.md`.
Aquí solo se conserva un resumen operativo y las referencias a comandos que ayudan a coordinar el trabajo.

#### WORKLOG.md — Registro de sesiones

Archivo en la raíz del repo que cada agente actualiza al iniciar y cerrar sesión.

**Al iniciar:**
```bash
git pull origin staging
git log --oneline -15 origin/staging   # ver qué hizo el otro agente
cat WORKLOG.md                          # ver sesiones activas
# Agregar entrada en "Sesiones activas" y hacer commit+push:
git commit -m "[claude] worklog: inicio — <tarea breve>"
git push origin staging
```

**Al cerrar:**
```bash
# Mover entrada a "Historial" con estado COMPLETADO/PENDIENTE y hacer commit del WORKLOG
git commit -m "[claude] worklog: cierre — <tarea breve>"

# PROTOCOLO PRE-PUSH OBLIGATORIO:
git fetch origin staging
git log --oneline HEAD..origin/staging    # hay commits nuevos del otro agente?
git diff --name-only HEAD origin/staging  # solapan con tus archivos?

# Sin solapamiento -> push normal
git push origin staging

# Con solapamiento en mismos archivos -> PAUSAR
# Reportar a Luis Felipe antes de pushear
```

> Si hay solapamiento real con commits nuevos del otro agente, revisar `AGENTS.md` y escalar la decisión a Luis Felipe.

#### Prefijo obligatorio en commits

| Agente | Formato |
|--------|---------|
| Claude Code | `[claude] feat: descripción` |
| Codex | `[codex] feat: descripción` |

Para filtrar por agente: `git log --oneline --grep="[claude]"`

#### Pautas de no-interferencia

- No modificar o revertir trabajo del otro agente sin autorización de Luis Felipe.
- Si se detecta un error del otro agente: reportarlo con evidencia y esperar instrucción.
- Si se detecta solapamiento en `WORKLOG.md` o `git log`: pausar y notificar a Luis Felipe.
- Si `git push` es rechazado por fast-forward: revisar estado remoto y seguir el protocolo de `AGENTS.md`.

#### Archivos de alto riesgo

Verificar WORKLOG.md y `git log --follow -5 <archivo>` antes de editar cualquiera de estos:
`Backend/main.py` · `Backend/services.py` · `Backend/db.py` · `Backend/order_delivery.py` · `AGENTS.md` · `CLAUDE.md`

La coordinación entre agentes pasa por Luis Felipe.

### Antes de Cambiar Código
1. Mostrar el **bloque exacto** que se va a modificar.
2. Explicar brevemente **qué** se cambia y **por qué**.
3. Confirmar: rama activa + archivo exacto.

### Durante el Trabajo
- No asumir errores solo por ver diffs.
- No repetir pasos ya completados.
- No reescribir archivos completos sin autorización.
- Trabajar **solo** en el objetivo indicado. **PROHIBIDO** ampliar alcance sin aprobación.
- Cambios mínimos: un solo objetivo por instrucción.

### Cuando el tool Edit no persiste los cambios

**Sintoma:** Edit reporta exito pero `git diff` no muestra el cambio, o el archivo vuelve a su estado previo.  
**Causa:** linter del IDE o servidor de lenguaje revierte el archivo inmediatamente al guardarlo.

**Procedimiento:**
1. Detectar con `git diff --name-only` que el cambio no persiste.
2. Cambiar de estrategia al tercer intento fallido — no seguir reintentando Edit.
3. Usar un script Python via Bash:

```bash
python3 << 'EOF'
path = 'ruta/al/archivo.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace(viejo_bloque, nuevo_bloque, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
EOF
```

### Escritura de secuencias de escape en archivos Python via bash

**Problema:** al escribir un archivo `.py` desde un heredoc bash (`<< 'PYEOF'`) o `python3 -c`, la secuencia `
` dentro de strings Python se convierte en un salto de linea real en lugar de quedar como los dos caracteres `\` + `n`.

**Solucion obligatoria:** usar `chr(92)` para construir el caracter backslash:

```python
bs = chr(92)       # chr(92) = backslash
n_esc = bs + 'n'   # produce el escape 
 correcto en el archivo escrito

# Ejemplo: escribir la linea  text = "hola
world"
line = '    text = "hola' + n_esc + 'world"'
```

Esta regla aplica a cualquier caracter de escape que deba quedar literal en el archivo generado: `
`, `	`, `
`, `\`, etc.

**PROHIBIDO** usar secuencias de escape directas (`
`, `	`) dentro de strings Python al construir contenido de otro archivo Python.

### Después de los Cambios

Ejecutar siempre:
```bash
cd Backend/
python -m py_compile main.py services.py db.py order_delivery.py profile_changes.py
```

Verificar imports huérfanos tras mover o eliminar funciones:
```bash
git grep "nombre_funcion" -- "*.py"
# Si solo aparece en el bloque import y en ningún otro lugar → importación huérfana, eliminar
```

Reportar claramente: qué cambió, qué se eliminó, por qué.

### Veracidad Técnica

Siempre separar entre:
- **IMPLEMENTADO**: existe en el código hoy. Indicar `archivo:función`.
- **PROPUESTA / FUTURO**: no existe aún. Indicarlo explícitamente.

**PROHIBIDO** afirmar que algo existe sin verificarlo primero.

### Protocolo de Decisiones

```
Exponer opciones → preguntar → esperar confirmación → ejecutar
```

**PROHIBIDO** cerrar decisiones de cambio por iniciativa propia.

### Estilo de Colaboración

- Priorizar **estabilidad** sobre velocidad.
- Preguntar antes de decidir. No improvisar soluciones.
- Asumir que el usuario es técnico, detallista y quiere **control total** del sistema.

---

## Contexto de Negocio Relevante

- El sistema opera en **Colombia** (moneda: COP, teléfonos: +57XXXXXXXXXX).
- El cotizador usa la API de Google Maps para calcular distancias. Hay un límite diario de llamadas (`api_usage_daily`) para controlar costos.
- El sistema de recargas transfiere saldo del Admin a Repartidores/Aliados. Es crítico que sea idempotente ante concurrencia.
- Los pedidos siguen el ciclo: `PENDING` → publicado a repartidores → aceptado → recogida confirmada → entregado (o cancelado en cualquier paso).
- La plataforma opera como **red cooperativa**: cualquier repartidor activo puede tomar pedidos de cualquier aliado, sin importar a qué admin pertenece cada uno. No existen equipos aislados para el despacho de pedidos.
- Un Admin Local gestiona su equipo (aprueba/inactiva repartidores y aliados) y gana comisiones de sus propios miembros. Puede aprobar/rechazar miembros pendientes, inactivar activos y reactivar inactivos; el rechazo definitivo (`REJECTED`) es exclusivo del Admin de Plataforma.
- La referencia de versión financiera estable es el tag `v0.1-admin-saldos` (ledger confiable desde ese punto).
- El sistema usa **contabilidad de doble entrada**: el Admin de Plataforma debe registrar ingresos externos (`register_platform_income`) para tener saldo y poder aprobar recargas. PROHIBIDO crear saldo sin origen contable.
- Las tablas `admin_allies` y `admin_couriers` tienen su propio campo `status` que debe mantenerse sincronizado con `allies.status` / `couriers.status`. Los helpers `_sync_ally_link_status` y `_sync_courier_link_status` en `db.py` garantizan esta sincronía automáticamente en cada actualización de estado.

---

## Agendas del Admin (IMPLEMENTADO 2026-03-07)

El Admin Local y el Admin de Plataforma tienen dos agendas propias:

1. **Agenda de clientes de entrega** (`admin_customers` + `admin_customer_addresses`): registrar clientes recurrentes que solicitan domicilios, con sus datos de entrega. Espejo exacto de la agenda `ally_customers`.
2. **Mis Direcciones** (`admin_locations`): gestión CRUD completa de los puntos de recogida del admin. Antes solo se podían agregar durante el pedido; ahora tiene UI de gestión independiente.

### Flujo `admin_clientes_conv`

Entry: callback `admin_mis_clientes` (botón en menú admin)

| Estado | Constante | Descripción |
|--------|-----------|-------------|
| `ADMIN_CUST_MENU` | 925 | Menú principal |
| `ADMIN_CUST_NUEVO_NOMBRE` | 926 | Nombre del nuevo cliente |
| `ADMIN_CUST_NUEVO_TELEFONO` | 927 | Teléfono del nuevo cliente |
| `ADMIN_CUST_NUEVO_NOTAS` | 928 | Notas internas del cliente |
| `ADMIN_CUST_NUEVO_DIR_LABEL` | 929 | Etiqueta de la primera dirección |
| `ADMIN_CUST_NUEVO_DIR_TEXT` | 930 | Dirección (con geocoding) |
| `ADMIN_CUST_BUSCAR` | 931 | Búsqueda por nombre/teléfono |
| `ADMIN_CUST_VER` | 932 | Detalle del cliente |
| `ADMIN_CUST_EDITAR_NOMBRE` | 933 | Editar nombre |
| `ADMIN_CUST_EDITAR_TELEFONO` | 934 | Editar teléfono |
| `ADMIN_CUST_EDITAR_NOTAS` | 935 | Editar notas |
| `ADMIN_CUST_DIR_NUEVA_LABEL` | 936 | Etiqueta de nueva dirección |
| `ADMIN_CUST_DIR_NUEVA_TEXT` | 937 | Nueva dirección (geocoding) |
| `ADMIN_CUST_DIR_EDITAR_LABEL` | 938 | Editar etiqueta de dirección |
| `ADMIN_CUST_DIR_EDITAR_TEXT` | 939 | Editar dirección |
| `ADMIN_CUST_DIR_EDITAR_NOTA` | 940 | Editar nota de entrega |
| `ADMIN_CUST_DIR_CIUDAD` | 941 | Ciudad de la dirección |
| `ADMIN_CUST_DIR_BARRIO` | 942 | Barrio (punto de persistencia) |
| `ADMIN_CUST_DIR_CORREGIR` | 943 | Corregir/agregar coordenadas |

**Prefijo callbacks**: `acust_`
**Prefijo user_data**: `acust_`
**Funciones DB**: `create_admin_customer`, `list_admin_customers`, `search_admin_customers`, `update_admin_customer`, `archive_admin_customer`, `restore_admin_customer`, `get_admin_customer_by_id`, `create_admin_customer_address`, `list_admin_customer_addresses`, `update_admin_customer_address`, `archive_admin_customer_address`, `get_admin_customer_address_by_id`

### Flujo `admin_dirs_conv`

Entry: callback `admin_mis_dirs` (botón en menú admin)

| Estado | Constante | Descripción |
|--------|-----------|-------------|
| `ADMIN_DIRS_MENU` | 945 | Lista de ubicaciones de recogida |
| `ADMIN_DIRS_NUEVA_LABEL` | 946 | Nombre del lugar (etiqueta) |
| `ADMIN_DIRS_NUEVA_TEXT` | 947 | Dirección (con geocoding) |
| `ADMIN_DIRS_NUEVA_TEL` | 948 | Teléfono del punto (opcional) |
| `ADMIN_DIRS_VER` | 949 | Detalle de una ubicación |

**Prefijo callbacks**: `adirs_`
**Prefijo user_data**: `adirs_`
**Funciones DB**: `get_admin_locations`, `get_admin_location_by_id`, `create_admin_location`, `update_admin_location`, `archive_admin_location`

### Integración en `admin_pedido_conv`

Al avanzar al paso `ADMIN_PEDIDO_CUST_NAME`, se muestra un botón "Seleccionar de mis clientes". El admin puede:
- Escribir el nombre directamente (flujo manual existente)
- Seleccionar de su agenda → ver sus direcciones guardadas → seleccionar una (salta a `ADMIN_PEDIDO_TARIFA`) o ingresar nueva (va a `ADMIN_PEDIDO_CUST_ADDR`)

| Estado | Constante | Descripción |
|--------|-----------|-------------|
| `ADMIN_PEDIDO_SEL_CUST` | 917 | Lista de clientes para seleccionar |
| `ADMIN_PEDIDO_SEL_CUST_ADDR` | 918 | Seleccionar dirección del cliente |

**Callbacks nuevos en `admin_pedido_conv`**:
- `admin_pedido_sel_cust` → `admin_pedido_sel_cust_handler`
- `acust_pedido_sel_{id}` → `admin_pedido_cust_selected`
- `acust_pedido_addr_{id}` → `admin_pedido_addr_selected`
- `acust_pedido_addr_nueva` → `admin_pedido_addr_nueva`

---

## Flujo de Entrega con Validación GPS (IMPLEMENTADO 2026-03-12)

### Nuevo ciclo de entrega

```
Aliado confirma llegada del courier al pickup
  → courier recibe botón "Confirmar recogida" (sin GPS requerido)
  → courier confirma → PICKED_UP + datos del cliente revelados + jobs T+30/T+60

Courier intenta finalizar el servicio:
  → GPS inactivo (con pedido activo) → BLOQUEADO — instrucciones para reactivar
  → GPS activo + courier a ≤100m de dropoff_lat/lng → confirmación normal
  → GPS activo + courier a >100m → explicación + botón "Estoy aquí pero el pin está mal"
```

**Aplica igual a rutas multi-parada**: cada parada valida GPS + distancia a `route_destinations.dropoff_lat/lng`.

### Constantes en `order_delivery.py`

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `DELIVERY_RADIUS_KM` | 0.1 (100 m) | Radio máximo para finalizar entrega |
| `DELIVERY_REMINDER_SECONDS` | 1800 (30 min) | Job recordatorio al courier en PICKED_UP |
| `DELIVERY_ADMIN_ALERT_SECONDS` | 3600 (60 min) | Job alerta al admin si courier no finaliza |
| `GPS_INACTIVE_MSG` | (constante texto) | Mensaje estándar cuando GPS está inactivo |

### Helper GPS

```python
_is_courier_gps_active(courier) → bool
# Retorna True si live_location_active == 1 y live_lat/live_lng no son None
```

### GPS bloqueante (con servicio activo)

- `mi_repartidor()` en `main.py`: si el courier tiene pedido o ruta activa (`ACCEPTED`/`PICKED_UP`) y GPS inactivo → muestra aviso con instrucciones antes del menú.
- Las funciones `_handle_delivered_confirm`, `_handle_pin_issue_report`, `_handle_route_deliver_stop`, `_handle_route_pin_issue` también verifican GPS y bloquean si está inactivo.
- **NO aplica** cuando el courier no tiene servicios activos.

---

## Flujo de Soporte por Pin Mal Ubicado (IMPLEMENTADO 2026-03-12)

### Flujo completo — Pedido normal

```
Courier reporta "Estoy aquí pero el pin está mal" (order_pinissue_{id})
  → Crea order_support_requests (idempotente: no crea duplicados)
  → Notifica al admin del equipo en Telegram:
      - Datos del pedido y cliente
      - Link Google Maps al pin de entrega guardado (dropoff_lat/lng)
      - Link Google Maps a ubicación actual del courier (live_lat/lng)
      - Link Telegram directo al courier (para chat)
      - Botones: Finalizar / Cancelar falla courier / Cancelar falla aliado
  → Courier: "Solicitud enviada. Permanece en el lugar."

Admin toca Finalizar:
  → resolve_support_request(DELIVERED) + apply_service_fee(ALLY) + apply_service_fee(COURIER)
  → set_order_status(DELIVERED)
  → Courier notificado: "Admin finalizó el servicio"

Admin toca Cancelar falla courier:
  → resolve_support_request(CANCELLED_COURIER) + apply_service_fee(COURIER solo)
  → cancel_order(ADMIN)
  → Courier notificado: "Pedido cancelado. Falla atribuida a ti. Devuelve el producto."

Admin toca Cancelar falla aliado:
  → resolve_support_request(CANCELLED_ALLY) + apply_service_fee(ALLY) + apply_service_fee(COURIER)
  → cancel_order(ADMIN)
  → Courier notificado: "Pedido cancelado. Falla del aliado. Devuelve el producto."
```

### Flujo completo — Ruta multi-parada

```
Courier reporta pin malo en parada (ruta_pinissue_{route_id}_{seq})
  → Misma lógica de notificación al admin, con datos de la parada
  → Admin puede: Finalizar parada / Cancelar parada (courier) / Cancelar parada (aliado)
  → Al resolver: courier continúa con las demás paradas pendientes
  → Al finalizar la ruta: si hay paradas canceladas → resumen de devoluciones al courier
```

### Tabla de fees por resolución

| Acción admin | Aliado | Courier | Estado orden |
|---|:---:|:---:|---|
| Finalizar | $300 | $300 | DELIVERED |
| Cancelar falla courier | $0 | $300 | CANCELLED |
| Cancelar falla aliado | $300 | $300 | CANCELLED |

### Funciones nuevas en `order_delivery.py`

| Función | Descripción |
|---------|-------------|
| `_notify_courier_awaiting_pickup_confirm(context, order)` | Envía botón "Confirmar recogida" al courier tras aprobación del aliado |
| `_handle_confirm_pickup(update, context, order_id)` | Courier confirma recogida → PICKED_UP + revela datos |
| `_handle_delivered_confirm(update, context, order_id)` | Valida GPS + distancia antes de la confirmación de entrega |
| `_handle_pin_issue_report(update, context, order_id)` | Courier reporta pin malo; crea solicitud y notifica admin |
| `_notify_admin_pin_issue(context, order, courier, admin_id, support_id)` | Envía alerta al admin con datos y botones |
| `_handle_admin_pinissue_action(update, context, order_id, action)` | Admin resuelve: fin/cancel_courier/cancel_ally |
| `_do_deliver_order(context, order, courier_id)` | Aplica fees y marca DELIVERED (usado por admin al finalizar) |
| `_notify_courier_support_resolved(context, courier_id, order_id, resolution)` | Notifica al courier el resultado |
| `_handle_route_pin_issue(update, context, route_id, seq)` | Equivalente para rutas |
| `_notify_admin_route_pin_issue(context, route, stop, courier, admin_id, support_id)` | Alerta al admin con datos de la parada |
| `_handle_admin_route_pinissue_action(update, context, route_id, seq, action)` | Admin resuelve parada de ruta |
| `_notify_courier_route_stop_resolved(context, courier_id, route_id, seq, resolution)` | Notifica al courier resultado de parada |
| `_cancel_delivery_reminder_jobs(context, order_id)` | Cancela jobs T+30 y T+60 |
| `_delivery_reminder_job(context)` | Job T+30: recordatorio al courier en PICKED_UP |
| `_delivery_admin_alert_job(context)` | Job T+60: alerta al admin si courier no finaliza |

### Funciones nuevas en `db.py`

| Función | Descripción |
|---------|-------------|
| `create_order_support_request(courier_id, admin_id, order_id, route_id, route_seq)` | Crea solicitud; retorna id generado |
| `get_pending_support_request(order_id, route_id, route_seq)` | Retorna solicitud PENDING del pedido o parada |
| `resolve_support_request(support_id, resolution, resolved_by)` | Marca como RESOLVED; retorna bool |
| `cancel_route_stop(route_id, seq, resolution)` | Marca parada con CANCELLED_COURIER o CANCELLED_ALLY |
| `get_all_pending_support_requests()` | Lista todos los PENDING con datos de courier y pedido (para panel web) |
| `get_support_request_full(support_id)` | Retorna solicitud con todos los datos JOIN para el panel web |

Todas re-exportadas en `services.py`.

### Panel web — Solicitudes de ayuda (`/superadmin/soporte`)

El panel web del Platform Admin expone:

| Endpoint | Descripción |
|----------|-------------|
| `GET /admin/support-requests` | Lista todas las solicitudes (PENDING y recientes RESOLVED) |
| `GET /admin/support-requests/{id}` | Detalle completo con datos de courier, pedido, mapas |
| `POST /admin/support-requests/{id}/resolve` | Resuelve la solicitud (mismo modelo de fees que el bot) |

El componente Angular (`SoporteComponent`) muestra:
- Tabla de solicitudes con estado y datos del courier
- Panel de detalle con link al pin de entrega y ubicación del courier (Google Maps)
- Link Telegram directo al courier para comunicación
- Botones de acción: Finalizar / Cancelar falla courier / Cancelar falla aliado
- **Nota:** la resolución desde el panel web aplica los fees en BD pero NO envía notificaciones Telegram al courier (el courier solo recibe notificación cuando el admin actúa desde el bot).


---

## Enlace de Pedido del Aliado (PARCIALMENTE IMPLEMENTADO — ver nota abajo)

> Descripcion funcional completa en `docs/business/contexto-negocio-domiquerendona.md` seccion 5B.

### Que hay que construir (notas tecnicas minimas)

**Base de datos - cambios minimos:**
- Columna `public_token TEXT UNIQUE` en tabla `allies` - UUID por aliado para construir la URL publica.
- Tabla nueva `ally_form_requests` - bandeja temporal de solicitudes recibidas por formulario.
  Campos: `id`, `ally_id`, `customer_name`, `customer_phone`, `delivery_address`,
  `delivery_city`, `delivery_barrio`, `notes`, `lat`, `lng`,
  `status` (PENDING/CONVERTED_ORDER/SAVED_CONTACT/DISMISSED), `created_at`.
- No se necesitan cambios en `ally_customers`, `ally_customer_addresses` ni `orders`.

**Backend - nuevo router publico en FastAPI:**
- Archivo nuevo: `Backend/web/api/form.py` - router sin autenticacion.
- `GET /form/{token}` - valida token, retorna nombre del aliado.
- `POST /form/{token}/submit` - recibe datos, inserta en `ally_form_requests`, notifica al aliado por Telegram.
- Registro en `web_app.py` sin tocar routers existentes.
- CORS: agregar dominio del formulario publico a `origins`.

**Bot Telegram - entry points nuevos en main.py:**
- Handler "Mi enlace de pedidos" en menu del aliado: llama `get_or_create_ally_public_token(ally_id)`.
- Handler callback "Crear pedido": inicia `nuevo_pedido_conv` con `context.user_data` prellenado.
- Handler callback "Guardar en agenda": llama `create_ally_customer` + `create_customer_address`.
- Handler callback "Ignorar": marca solicitud como DISMISSED.
- Prefijo de callbacks pendiente de aprobacion antes de implementar.

**Frontend - componente publico:**
- Ruta `/form/:token` sin `AuthGuard` en `app.routes.ts`.
- Componente `FormPedidoComponent` en `Frontend/src/app/features/public/`.
- Pasos: telefono (siempre primero) -> reconocimiento de cliente -> direccion -> mapa -> cotizacion.

**Funciones db.py que hacen falta:**
- `get_or_create_ally_public_token(ally_id)` -> str (UUID)
- `get_ally_by_public_token(token)` -> dict
- `create_ally_form_request(ally_id, ...)` -> int
- `get_ally_form_request_by_id(request_id, ally_id)` -> dict
- `update_ally_form_request_status(request_id, status)`
Todas deben re-exportarse en `services.py`.

**Funciones db.py reutilizables sin cambios:**
- `get_ally_customer_by_phone(ally_id, phone)` - detecta cliente existente
- `create_ally_customer`, `create_customer_address` - crea desde solicitud
- `create_order` - mismo contrato que el flujo bot

**Orden de implementacion recomendado:**
1. Migracion (columna `public_token` + tabla `ally_form_requests`) + funciones db.py
2. Router publico `/form/` + notificacion Telegram basica
3. Handlers bot para Crear / Guardar / Ignorar desde notificacion
4. Boton "Mi enlace" en menu del aliado
5. Frontend formulario publico minimo viable
6. Cotizacion en el formulario
7. Subsidio del aliado + incentivo del cliente

---

## Subsidio de domicilio + valor de compra (IMPLEMENTADO 2026-03-16)

Bloque cerrado funcionalmente. Cubre: subsidio fijo, subsidio condicional por compra mínima,
declaración informativa del cliente en el formulario, confirmación por el aliado en el bot,
persistencia de snapshot en el pedido y visibilidad para aliado y admin.

### Qué resuelve este bloque

- El aliado puede configurar un subsidio al domicilio del cliente: fijo (aplica siempre)
  o condicional (aplica solo si el valor de compra confirmado supera un umbral).
- El formulario público informa el subsidio disponible sin prometérselo cuando es condicional.
- El bot le pregunta al aliado el valor de compra real antes de crear el pedido.
- El pedido guarda un snapshot inmutable del subsidio aplicado y el precio al cliente.

### Fuente de verdad

| Dato | Fuente | Tipo |
|------|--------|------|
| Configuración del subsidio | `allies.delivery_subsidy` | Operativo |
| Condición de compra mínima | `allies.min_purchase_for_subsidy` | Operativo |
| Valor declarado por el cliente | `ally_form_requests.purchase_amount_declared` | **Informativo únicamente** |
| Valor confirmado por el aliado | `orders.purchase_amount` | **Fuente de verdad financiera** |
| Subsidio efectivamente aplicado | `orders.delivery_subsidy_applied` | Snapshot histórico |
| Precio pagado por el cliente | `orders.customer_delivery_fee` | Snapshot histórico |
| Tarifa del courier | `orders.total_fee` | Ortogonal al subsidio, nunca cambia |

### Regla crítica de diseño

`purchase_amount_declared` (del formulario) es SOLO una sugerencia visual que se muestra
al aliado en el bot. NUNCA se usa como fuente de verdad para calcular subsidios ni fees.
El subsidio condicional se aplica únicamente sobre `orders.purchase_amount` (confirmado por el aliado).

### Comportamiento de `customer_delivery_fee`

`customer_delivery_fee` se persiste como `max(subtotal_servicio - subsidio_efectivo, 0)`.
Esto significa que cuando `subsidio_efectivo = 0`, el campo toma el valor completo del domicilio
(no queda NULL). Solo queda NULL si el pedido no tiene ally activo o no tiene tarifa calculada
(p.ej., pedido especial de admin sin ally).

Consecuencia en vistas: tanto el detalle del aliado como el del admin muestran
`"Domicilio al cliente: $X"` incluso cuando `"Subsidio aplicado: No"`, porque el campo
no es nulo — simplemente muestra el precio completo sin descuento.

### Pendiente puntual — Frontend

`FormPedidoComponent` (`Frontend/src/app/features/public/form-pedido.ts`) está implementado
y registrado en rutas (`/form/:token`). Maneja `purchase_amount_declared` y `subsidioAliado`.
Pendiente puntual: no consume aún el campo `subsidy_conditional` del response de `quote_form`
(backend lo retorna pero el frontend no lo usa para mostrar el mensaje condicional al cliente).

### Lo que NO hace este bloque

- No afecta `total_fee` ni `apply_service_fee` ni el ledger contable.
- No modifica la tarifa del courier.
- No hace reporting financiero sobre subsidios históricos.
- No cubre el subsidio aportado por el cliente (`incentivo_cliente`) — eso es un campo separado.

### Funciones clave

| Función | Archivo | Descripción |
|---------|---------|-------------|
| `compute_ally_subsidy(delivery_subsidy, min_purchase, purchase_amount)` | `services.py` | Helper puro, 5 reglas |
| `construir_resumen_pedido(context)` | `main.py` | Calcula subsidio y cachea en user_data |
| `pedido_confirmacion_callback(...)` | `main.py` | Pasa snapshot a `create_order` |
| `_ally_bandeja_mostrar_pedido(...)` | `main.py` | Vista subsidio desde bandeja aliado |
| `_admin_order_detail(...)` | `order_delivery.py` | Vista subsidio desde panel admin |
| `config_ver_ally_` handler | `main.py` | Config subsidio visible en detalle del aliado |
| `quote_form` / `submit_form` | `web/api/form.py` | Cotización y submit público |

### Fecha de cierre

2026-03-16

---

*Última actualización: 2026-03-16*

