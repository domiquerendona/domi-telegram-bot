# CLAUDE.md â€” GuÃ­a tÃ©cnica y arquitectura explicada de Domiquerendona

Este archivo describe la estructura del proyecto, flujos de trabajo y convenciones tÃ©cnicas del repositorio. Es un complemento explicativo de `AGENTS.md`, que define las reglas obligatorias.

> **IMPORTANTE:** Las reglas de `AGENTS.md` tienen prioridad absoluta. Este documento explica el "quÃ©" y el "cÃ³mo" del sistema; `AGENTS.md` define el "no harÃ¡s".
>
> **Alcance de este documento:** `CLAUDE.md` explica arquitectura, mÃ³dulos, despliegue y flujos. No define normas obligatorias. Las reglas normativas del proyecto estÃ¡n en `AGENTS.md`.

---

## VisiÃ³n General del Proyecto

**Domiquerendona** es una plataforma de domicilios (delivery) que opera en Colombia. El sistema consta de:

1. **Bot de Telegram** (Backend/): bot conversacional que gestiona pedidos, registros y operaciones de todos los actores del sistema.
2. **API Web** (Backend/web/): API REST con FastAPI que expone endpoints para el panel administrativo.
3. **Panel Web** (Frontend/): aplicaciÃ³n Angular 21 con SSR para el superadministrador.

Los actores principales del sistema son:
- **Platform Admin**: administrador global de la plataforma (un solo usuario).
- **Admin Local**: administra un equipo de repartidores y aliados en una zona. Sus atribuciones son:
  - Aprobar o rechazar miembros pendientes de su equipo (repartidores y aliados).
  - Inactivar miembros activos (`APPROVED` â†’ `INACTIVE`) y reactivarlos (`INACTIVE` â†’ `APPROVED`).
  - **NO puede** rechazar definitivamente (`REJECTED`) â€” esa acciÃ³n es exclusiva del Admin de Plataforma.
  - Gestiona pedidos de su equipo y aprueba recargas de saldo a sus miembros.
- **Aliado (Ally)**: negocio asociado (restaurante, tienda, etc.) que genera pedidos.
- **Repartidor (Courier)**: entrega los pedidos.
- **Cliente (Customer)**: destinatario del pedido (no tiene cuenta en el bot).

---

## Estructura del Repositorio

```
domi-telegram-bot/
â”œâ”€â”€ AGENTS.md                     # Reglas obligatorias del proyecto (leer primero)
â”œâ”€â”€ CLAUDE.md                     # Este archivo
â”œâ”€â”€ .gitignore                    # Ignora __pycache__, .env, *.db, etc.
â”‚
â”œâ”€â”€ Backend/                      # LÃ³gica del bot y API
â”‚   â”œâ”€â”€ main.py                   # Arranque del bot Telegram, handlers, wiring, UI
â”‚   â”œâ”€â”€ web_app.py                # Bootstrap FastAPI (app, routers, CORS, /)
â”‚   â”œâ”€â”€ services.py               # LÃ³gica de negocio + re-exports de db.py
â”‚   â”œâ”€â”€ db.py                     # Acceso exclusivo a base de datos
â”‚   â”œâ”€â”€ order_delivery.py         # Flujo completo de entrega de pedidos
â”‚   â”œâ”€â”€ profile_changes.py        # Flujo de cambios de perfil de usuarios
â”‚   â”œâ”€â”€ imghdr.py                 # Utilidad para detecciÃ³n de imÃ¡genes
â”‚   â”œâ”€â”€ requirements.txt          # Dependencias Python
â”‚   â”œâ”€â”€ Dockerfile                # Imagen Docker del backend
â”‚   â”œâ”€â”€ Procfile                  # Comando de arranque para Railway
â”‚   â”œâ”€â”€ .env.example              # Plantilla de variables de entorno
â”‚   â”œâ”€â”€ DEPLOY.md                 # GuÃ­a de separaciÃ³n DEV/PROD
â”‚   â”œâ”€â”€ TESTING.md                # Documento histÃ³rico de testing (fase antigua)
â”‚   â”‚
â”‚   â”œâ”€â”€ migrations/
â”‚   â”‚   â””â”€â”€ postgres_schema.sql   # Schema completo para PostgreSQL
â”‚   â”‚
â”‚   â””â”€â”€ web/                      # MÃ³dulo FastAPI (panel web)
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ admin/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â””â”€â”€ services.py       # LÃ³gica: approve_user, reject_user, deactivate_user
â”‚       â”œâ”€â”€ api/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â”œâ”€â”€ admin.py          # Endpoints: POST /admin/users/{id}/approve, etc.
â”‚       â”‚   â”œâ”€â”€ dashboard.py      # Endpoints del dashboard
â”‚       â”‚   â””â”€â”€ users.py          # Endpoints de usuarios
â”‚       â”œâ”€â”€ auth/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â”œâ”€â”€ dependencies.py   # get_current_user (dependencia FastAPI)
â”‚       â”‚   â””â”€â”€ guards.py         # is_admin(), can_access_system(), is_blocked()
â”‚       â”œâ”€â”€ schemas/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â””â”€â”€ user.py           # Pydantic schemas (UserResponse, etc.)
â”‚       â”œâ”€â”€ teams/
â”‚       â”‚   â””â”€â”€ models.py         # Modelos de equipos
â”‚       â”œâ”€â”€ users/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â”œâ”€â”€ models.py         # UserRole, UserStatus (enums)
â”‚       â”‚   â”œâ”€â”€ repository.py     # get_user_by_id(), etc.
â”‚       â”‚   â”œâ”€â”€ roles.py          # RBAC: ADMIN_ALLOWED, COURIER_ONLY, etc.
â”‚       â”‚   â””â”€â”€ status.py         # ACTIVE_USERS, BLOCKED_USERS
â”‚       â””â”€â”€ wallet/
â”‚           â”œâ”€â”€ __init__.py
â”‚           â””â”€â”€ models.py         # Modelos de billetera
â”‚
â”œâ”€â”€ Frontend/                     # Panel administrativo Angular
â”‚   â”œâ”€â”€ angular.json
â”‚   â”œâ”€â”€ package.json              # Angular 21, SSR, vitest
â”‚   â”œâ”€â”€ tsconfig.json
â”‚   â””â”€â”€ src/
â”‚       â”œâ”€â”€ main.ts               # Entry point cliente
â”‚       â”œâ”€â”€ main.server.ts        # Entry point SSR
â”‚       â”œâ”€â”€ server.ts             # Express SSR server
â”‚       â””â”€â”€ app/
â”‚           â”œâ”€â”€ app.ts            # Componente raÃ­z
â”‚           â”œâ”€â”€ app.routes.ts     # Rutas del cliente
â”‚           â”œâ”€â”€ core/
â”‚           â”‚   â”œâ”€â”€ guards/       # auth.guard.ts
â”‚           â”‚   â”œâ”€â”€ interceptors/ # auth.interceptor.ts
â”‚           â”‚   â””â”€â”€ services/     # api.ts (servicio HTTP)
â”‚           â”œâ”€â”€ features/
â”‚           â”‚   â””â”€â”€ superadmin/
â”‚           â”‚       â”œâ”€â”€ dashboard/
â”‚           â”‚       â”œâ”€â”€ settings/
â”‚           â”‚       â””â”€â”€ users/
â”‚           â””â”€â”€ layout/
â”‚               â”œâ”€â”€ components/   # header/, sidebar/
â”‚               â””â”€â”€ superadmin-layout/
â”‚
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ HITOS.md                  # Documento histÃ³rico de hitos
â”‚   â”œâ”€â”€ reglas_operativas.md      # Matriz de estados y botones UI
â”‚   â”œâ”€â”€ testing_strategy.md       # Estrategia de testing vigente
â”‚   â”œâ”€â”€ alineacion_codigo_documentacion_2026-03-12.md  # Snapshot histÃ³rico de auditorÃ­a
â”‚   â””â”€â”€ callback_governance_2026-03-12.md              # Fuente de verdad de callbacks
â”‚
â”œâ”€â”€ migrations/
â”‚   â”œâ”€â”€ migrate_sqlite_to_postgres.py
â”‚   â””â”€â”€ postgres_schema.sql       # Copia del schema en raÃ­z (legacy)
â”‚
â””â”€â”€ tests/
    â”œâ”€â”€ test_recharge_idempotency.py   # Tests de idempotencia en recargas
    â””â”€â”€ test_status_validation.py      # Tests de validaciÃ³n de estados
```

---

## Arquitectura de Capas (Backend)

La regla mÃ¡s importante del proyecto es la separaciÃ³n estricta en tres capas:

```
main.py  â”€â”€importaâ”€â”€â–º  services.py  â”€â”€importaâ”€â”€â–º  db.py
    â”‚                       â”‚                        â”‚
    â”‚  (handlers, wiring,   â”‚  (lÃ³gica de negocio,  â”‚  (SQL, queries,
    â”‚   UI, estado de flujo) â”‚   re-exports de db)   â”‚   conexiones)
    â”‚                       â”‚                        â”‚
    â””â”€â”€ order_delivery.py â”€â”€â”˜                        â”‚
    â””â”€â”€ profile_changes.py â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”˜
```

### `db.py` â€” Capa de Datos
- **Ãšnico responsable** de toda interacciÃ³n con la base de datos.
- Detecta motor en tiempo de arranque: `DATABASE_URL` presente â†’ PostgreSQL; ausente â†’ SQLite.
- Usa el placeholder global `P` (`%s` para Postgres, `?` para SQLite) en todas las queries.
- La regla obligatoria de conexiones y compatibilidad multi-motor estÃ¡ en `AGENTS.md`.
- Helpers multi-motor: `_insert_returning_id()`, `_row_value()`.

### `services.py` â€” Capa de Negocio
- Contiene toda la lÃ³gica de negocio que no es especÃ­fica de un mÃ³dulo grande.
- Importa desde `db.py` y re-exporta funciones para que `main.py` no acceda a `db.py` directamente.
- El bloque de re-exports estÃ¡ marcado con el comentario: `# Re-exports para que main.py no acceda a db directamente`.
- El patrÃ³n obligatorio de re-export estÃ¡ documentado en `AGENTS.md`.

### `main.py` â€” Orquestador
- Solo contiene: registro de handlers, funciones handler (validar â†’ llamar services â†’ retornar estado), helpers de UI, gestiÃ³n de estado de flujo, constantes de UI.
- Las restricciones obligatorias sobre quÃ© puede y quÃ© no puede vivir en `main.py` estÃ¡n en `AGENTS.md`.
- **Excepciones permitidas** en `main.py` (solo estas 3):
  ```python
  from db import init_db
  from db import force_platform_admin
  from db import ensure_pricing_defaults
  ```

### MÃ³dulos Especializados
- **`order_delivery.py`**: flujo completo de publicaciÃ³n, ofertas y entrega de pedidos.
- **`profile_changes.py`**: flujo de solicitudes de cambio de perfil de usuarios.

### Regla Anti-ImportaciÃ³n Circular

Si un mÃ³dulo secundario (`profile_changes.py`, `order_delivery.py`, etc.) necesita una funciÃ³n de `main.py`, la regla obligatoria de resoluciÃ³n estÃ¡ en `AGENTS.md`.
En la prÃ¡ctica, este repositorio resuelve esos casos moviendo la funciÃ³n a `services.py` o, solo si es inevitable, usando import lazy documentado.

---

## Base de Datos

### Motor Dual (SQLite + PostgreSQL)

| Ambiente | Motor | ConfiguraciÃ³n |
|----------|-------|---------------|
| LOCAL (desarrollo) | SQLite | `DATABASE_URL` no definida; usa `DB_PATH` |
| PROD (Railway) | PostgreSQL | `DATABASE_URL` presente |

La selecciÃ³n es automÃ¡tica en `db.py`:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
DB_ENGINE = "postgres" if DATABASE_URL else "sqlite"
P = "%s" if DB_ENGINE == "postgres" else "?"
```

### Estados EstÃ¡ndar

Todos los roles (admin, aliado, repartidor) usan exactamente estos estados:

| Estado | DescripciÃ³n |
|--------|-------------|
| `PENDING` | Registro nuevo, esperando aprobaciÃ³n |
| `APPROVED` | Aprobado y activo, puede operar |
| `INACTIVE` | Desactivado temporalmente, puede reactivarse |
| `REJECTED` | Rechazado (estado terminal desde UI) |

**Reglas de transiciÃ³n:**
- `PENDING` â†’ Aprobar â†’ `APPROVED` / Rechazar â†’ `REJECTED`
- `APPROVED` â†’ Desactivar â†’ `INACTIVE`
- `INACTIVE` â†’ Activar â†’ `APPROVED`
- `REJECTED` â†’ estado terminal (no hay botones de acciÃ³n)

### SeparaciÃ³n de Identificadores

**NUNCA mezclar:**
- `telegram_id` â†’ solo para mensajerÃ­a en Telegram
- `users.id` â†’ ID interno principal
- `admins.id`, `couriers.id`, `allies.id` â†’ IDs de rol

### Reglas de Migraciones

Las reglas obligatorias de migraciones y cambios estructurales de base de datos estÃ¡n en `AGENTS.md`.
AquÃ­ solo se conserva el contexto tÃ©cnico: las migraciones del proyecto son no destructivas, idempotentes y compatibles con datos existentes.

### Tablas Principales

| Tabla | DescripciÃ³n |
|-------|-------------|
| `users` | Todos los usuarios del bot (por `telegram_id`) |
| `admins` | Administradores locales y de plataforma |
| `couriers` | Repartidores |
| `allies` | Aliados (negocios) |
| `identities` | Identidad global (telÃ©fono + documento Ãºnicos) |
| `admin_couriers` | VÃ­nculos admin â†” repartidor con estado y balance |
| `admin_allies` | VÃ­nculos admin â†” aliado con estado y balance |
| `admin_locations` | Ubicaciones de recogida guardadas por administradores (para pedidos especiales). Columna `status TEXT DEFAULT 'ACTIVE'` para soft-delete. |
| `admin_customers` | Clientes de entrega del admin (personas que le solicitan domicilios). Campos: `admin_id`, `name`, `phone`, `notes`, `status`. |
| `admin_customer_addresses` | Direcciones de entrega de cada cliente del admin. Campos: `customer_id`, `label`, `address_text`, `city`, `barrio`, `notes`, `lat`, `lng`, `status`. |
| `orders` | Pedidos con todo su ciclo de vida. Columnas de tracking: `courier_arrived_at` (timestamp GPS), `courier_accepted_lat/lng` (posiciÃ³n al aceptar, base T+5), `dropoff_lat/lng` (coordenadas del punto de entrega). Columnas de pedido admin: `creator_admin_id` (NULL = pedido de aliado, valor = admin creador), `ally_id` (nullable, NULL en pedidos especiales de admin) |
| `order_support_requests` | Solicitudes de ayuda por pin mal ubicado. Campos: `order_id` (nullable), `route_id` (nullable), `route_seq` (nullable, para rutas), `courier_id`, `admin_id`, `status` (PENDING/RESOLVED), `resolution` (DELIVERED/CANCELLED_COURIER/CANCELLED_ALLY), `created_at`, `resolved_at`, `resolved_by`. |
| `recharge_requests` | Solicitudes de recarga de saldo |
| `ledger` | Libro contable de todas las transacciones |
| `settings` | ConfiguraciÃ³n del sistema (clave-valor) |
| `profile_change_requests` | Solicitudes de cambio de perfil |

---

## Flujos de ConversaciÃ³n (Bot de Telegram)

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

### ConvenciÃ³n de `callback_data`

Las reglas obligatorias de callbacks estÃ¡n en `AGENTS.md`.
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
| `config_` | ConfiguraciÃ³n del sistema |
| `cotizar_` | Flujo de cotizaciÃ³n de envÃ­o |
| `courier_` | Acciones de repartidor |
| `cust_` | Acciones de cliente. Incluye: `cust_dir_corregir_coords` (abre flujo para agregar/corregir coords de una direcciÃ³n guardada), `cust_geo_si` / `cust_geo_no` (confirmar geocoding en flujo de direcciÃ³n) |
| `dir_` | GestiÃ³n de direcciones de recogida |
| `guardar_` | Guardar direcciÃ³n de cliente |
| `menu_` | NavegaciÃ³n de menÃº |
| `order_` | Ofertas y entrega de pedidos. Incluye: `order_find_another_{id}` (aliado busca otro courier), `order_call_courier_{id}` (aliado ve telÃ©fono del courier), `order_wait_courier_{id}` (aliado sigue esperando), `order_delivered_confirm_{id}` / `order_delivered_cancel_{id}` (confirmaciÃ³n de entrega en courier â€” requiere GPS activo y radio â‰¤100m), `order_confirm_pickup_{id}` (courier confirma recogida del pedido), `order_pinissue_{id}` (courier reporta pin de entrega mal ubicado), `order_release_reason_{id}_{reason}` / `order_release_confirm_{id}_{reason}` / `order_release_abort_{id}` (liberaciÃ³n responsable con motivo) |
| `admin_pinissue_` | Panel de soporte de pin mal ubicado â€” pedidos. Incluye: `admin_pinissue_fin_{id}` (admin finaliza servicio), `admin_pinissue_cancel_courier_{id}` (admin cancela, falla del courier), `admin_pinissue_cancel_ally_{id}` (admin cancela, falla del aliado) |
| `admin_ruta_pinissue_` | Panel de soporte de pin mal ubicado â€” rutas. Incluye: `admin_ruta_pinissue_fin_{route_id}_{seq}`, `admin_ruta_pinissue_cancel_courier_{route_id}_{seq}`, `admin_ruta_pinissue_cancel_ally_{route_id}_{seq}` |
| `pagos_` | Sistema de pagos |
| `pedido_` | Flujo de creaciÃ³n de pedidos. Incluye: `pedido_nueva_dir` (nueva direcciÃ³n para cliente recurrente â†’ va a `PEDIDO_UBICACION` con geocoding completo, igual que cotizaciÃ³n), `pedido_geo_si` / `pedido_geo_no` (confirmar geocoding de direcciÃ³n de entrega), `pedido_sel_addr_{id}` (seleccionar direcciÃ³n guardada del cliente) |
| `perfil_` | Cambios de perfil |
| `pickup_` | SelecciÃ³n de punto de recogida |
| `preview_` | PrevisualizaciÃ³n de pedido |
| `pricing_` | ConfiguraciÃ³n de tarifas |
| `recargar_` | Sistema de recargas |
| `ref_` | ValidaciÃ³n de referencias |
| `terms_` | AceptaciÃ³n de tÃ©rminos y condiciones |
| `ubicacion_` | SelecciÃ³n de ubicaciÃ³n GPS |
| `ingreso_` | Registro de ingreso externo del Admin de Plataforma |
| `admin_pedido_` | Flujo de creaciÃ³n de pedido especial del admin. Incluye: `admin_nuevo_pedido` (entry point), `admin_pedido_pickup_{id}` (seleccionar pickup guardado), `admin_pedido_nueva_dir` (nueva direcciÃ³n pickup), `admin_pedido_geo_pickup_si/no` (confirmar geo pickup), `admin_pedido_geo_si/no` (confirmar geo entrega), `admin_pedido_sin_instruc` (sin instrucciones), `admin_pedido_inc_{1500|2000|3000}` (incentivos fijos en preview), `admin_pedido_inc_otro` (incentivo libre), `admin_pedido_confirmar` (publicar), `admin_pedido_cancelar` (cancelar) |
| `offer_inc_` | Sugerencia T+5 de incentivo (aliado y admin). Incluye: `offer_inc_{order_id}x{1500|2000|3000}` (incentivos fijos), `offer_inc_otro_{order_id}` (incentivo libre) |

**Antes de agregar un callback nuevo:** `git grep "nuevo_prefijo" -- "*.py"` para verificar que no existe ya.

### Repartidor: Pedidos en curso

En `Backend/main.py:courier_pedidos_en_curso()` existe el botÃ³n "Pedidos en curso" para el repartidor:
- Muestra el pedido activo (`orders.status` en `ACCEPTED`/`PICKED_UP`) y/o la ruta activa (`routes.status` en `ACCEPTED`).
- Botones:
  - Si `orders.status == ACCEPTED`:
    - "Solicitar confirmacion de recogida" â†’ `order_pickup_{id}`.
    - "Liberar pedido" â†’ `order_release_{id}` â†’ requiere motivo y confirmaciÃ³n (`order_release_reason_{id}_{reason}` â†’ `order_release_confirm_{id}_{reason}`).
  - Si `orders.status == PICKED_UP`:
    - "Finalizar pedido" â†’ `order_delivered_confirm_{id}` â†’ pregunta "Ya entregaste?" â†’ `order_delivered_{id}` o `order_delivered_cancel_{id}`.
  - "Entregar siguiente parada" (ruta) â†’ `ruta_entregar_{route_id}_{seq}` (si hay paradas pendientes).
  - "Liberar ruta" â†’ `ruta_liberar_{route_id}` â†’ requiere motivo y confirmaciÃ³n (`ruta_liberar_motivo_{route_id}_{reason}` â†’ `ruta_liberar_confirmar_{route_id}_{reason}`).
- Mientras exista pedido o ruta en curso, el courier no puede aceptar nuevas ofertas (`order_accept_*` / `ruta_aceptar_*`).
  - Al liberar un pedido, se notifica al admin del equipo para revisiÃ³n del motivo.
  - Al liberar pedido o ruta, el servicio se re-oferta a otros repartidores excluyendo al courier que liberÃ³ (no se le vuelve a ofrecer a Ã©l).
  - Solo el aliado puede CANCELAR el servicio; el courier solo puede LIBERAR para re-ofertar (con motivo y revisiÃ³n).

### Helpers de Input Reutilizables (`main.py`)

Cuando 3 o mÃ¡s handlers comparten la misma lÃ³gica de validaciÃ³n, se usan helpers:

```python
_handle_phone_input(update, context, storage_key, current_state, next_state, flow, next_prompt)
# Valida mÃ­nimo 7 dÃ­gitos. Almacena en context.user_data[storage_key].

_handle_text_field_input(update, context, error_msg, storage_key, current_state, next_state, flow, next_prompt)
# Valida que el texto no estÃ© vacÃ­o. Almacena en context.user_data[storage_key].

_OPTIONS_HINT  # Constante de texto para opciones de cancelaciÃ³n. SIEMPRE usar la constante.
```

---

## Reglas de CÃ³digo

### Anti-duplicaciÃ³n (obligatorio antes de escribir)

```bash
# Buscar handlers existentes
git grep "nombre_handler" -- "*.py"

# Buscar callbacks existentes
git grep "callback_prefix_" -- "*.py"

# Buscar funciones
git grep "def nombre_funcion" -- "*.py"
```

### Regla para Mover Funciones a `services.py`

Una funciÃ³n DEBE moverse a `services.py` si:
1. Llama a cualquier funciÃ³n importada de `db.py`
2. Valida roles, permisos o estados de usuario
3. Lee o interpreta configuraciÃ³n desde BD
4. Tiene lÃ³gica condicional basada en datos persistidos

### Crear un Nuevo MÃ³dulo `.py`

Solo cuando:
1. El dominio es claramente independiente del resto.
2. Agrupa mÃ¡s de 5 funciones cohesivas de ese dominio.
3. El usuario lo aprueba explÃ­citamente.

**PROHIBIDO** crear mÃ³dulos por conveniencia o para "desahogar" `main.py`.

### Estilo General

- No usar `parse_mode` ni Markdown en mensajes del bot.
- Una funciÃ³n = una sola responsabilidad clara.
- No crear funciones similares o redundantes.
- No introducir nuevos patrones si ya existe uno funcional.
- No reescribir archivos completos sin autorizaciÃ³n.

---

## Variables de Entorno

Archivo de referencia: `Backend/.env.example`

| Variable | DescripciÃ³n | Requerida en |
|----------|-------------|--------------|
| `ENV` | `DEV` o `PROD` | Siempre |
| `BOT_TOKEN` | Token del bot de Telegram | Siempre (distinto por ambiente) |
| `ADMIN_USER_ID` | Telegram ID del admin de plataforma | Siempre |
| `COURIER_CHAT_ID` | ID del grupo de repartidores en Telegram | DEV y PROD |
| `RESTAURANT_CHAT_ID` | ID del grupo de aliados en Telegram | DEV y PROD |
| `DATABASE_URL` | URL de conexiÃ³n PostgreSQL | DEV y PROD (Railway) |

**Regla de oro:** NUNCA usar el mismo `BOT_TOKEN` en DEV y PROD simultÃ¡neamente.

En PROD: si `DATABASE_URL` no estÃ¡ presente, el sistema debe lanzar error fatal y no arrancar.

---

## Desarrollo y pruebas

> **El bot DEV corre en Railway** (rama `staging`), no en local.
> Para ver cualquier cambio en el bot DEV: **`git push origin staging`**.
> Railway auto-deploya al recibir el push. Ver `Backend/DEPLOY.md`.

### Backend â€” compilaciÃ³n y verificaciÃ³n (sin necesidad de correr local)

```bash
cd Backend/

# Verificar que el cÃ³digo compila antes de hacer push
python -m py_compile main.py services.py db.py order_delivery.py profile_changes.py

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

# Build de producciÃ³n
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

### Tests AutomÃ¡ticos

Los tests estÃ¡n en `tests/` y usan `unittest`:

```bash
cd Backend/
python -m unittest tests/test_recharge_idempotency.py tests/test_status_validation.py

# Output esperado:
# Ran 7 tests in ~2s â†’ OK
```

**Cobertura actual:**
- `test_recharge_idempotency.py`: idempotencia y concurrencia en aprobar/rechazar recargas, carrera approve vs reject.
- `test_status_validation.py`: normalizaciÃ³n de estados vÃ¡lidos, rechazo de estados invÃ¡lidos, protecciÃ³n de `update_recharge_status`.

### VerificaciÃ³n de CompilaciÃ³n (obligatorio tras cambios)

```bash
cd Backend/
python -m py_compile main.py services.py db.py order_delivery.py profile_changes.py
```

### VerificaciÃ³n de Imports HuÃ©rfanos

Tras mover o eliminar funciones:

```bash
git grep "nombre_funcion" -- "*.py"
# Si solo aparece en el bloque import â†’ importaciÃ³n huÃ©rfana, eliminar
```

---

## Despliegue

### Arquitectura: dos servicios Railway permanentes

| Ambiente | Rama git | Trigger de deploy |
|----------|----------|-------------------|
| **DEV** | `staging` | `git push origin staging` |
| **PROD** | `main` | `git push origin main` (o merge stagingâ†’main) |

Para reglas obligatorias de ramas y despliegue, ver `AGENTS.md`.
Este documento solo resume cÃ³mo se reflejan los cambios en DEV y remite a `Backend/DEPLOY.md` para el detalle operativo.

### Railway (ambos servicios)

- **Motor**: `worker: python3 main.py` (Procfile)
- **Variables**: configurar en el dashboard de Railway por servicio (sin `.env`)
- **Base de datos**: PostgreSQL con `DATABASE_URL` (cada servicio tiene la suya)
- DEV y PROD usan **BOT_TOKEN distintos** â€” nunca el mismo token en ambos

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
- `GET /` â€” Health check HTML
- `POST /admin/users/{user_id}/approve` â€” Aprobar usuario (requiere rol admin)
- Endpoints de `/users/` y `/dashboard/`

CORS configurado para permitir `http://localhost:4200` en desarrollo.

---

## Git y Ramas

### Estructura de Ramas

Las reglas normativas de ramas viven en `AGENTS.md`.
AquÃ­ solo se mantiene un resumen explicativo de las ramas que existen hoy en el repositorio:

| Rama/Prefijo | Tipo | Uso actual |
|---|---|---|
| `main` | Permanente | ProducciÃ³n (Railway PROD) |
| `staging` | Permanente | IntegraciÃ³n y trabajo diario |
| `claude/` | Temporal | Ramas temporales de asistentes |
| `verify/` | Temporal | Validaciones acotadas, especialmente de BD |
| `luisa-web` | Permanente | Rama de trabajo de la colaboradora Luisa |

### Flujo de Trabajo

```
staging   â”€â”€(validado)â”€â”€â–º  main
verify/*  â”€â”€mergeâ”€â”€â–º  staging  â”€â”€(validado)â”€â”€â–º  main
                        (entorno DEV:
                         BOT_TOKEN DEV
                         DATABASE_URL separada)
```

Para el flujo obligatorio de trabajo y merge, ver `AGENTS.md`.
AquÃ­ basta con recordar que el entorno DEV se alimenta desde `staging` y que la validaciÃ³n funcional ocurre antes de promover cambios a `main`.

### VerificaciÃ³n de Compatibilidad Estructural (Obligatorio Antes de Merge)

Las validaciones obligatorias antes de merge estÃ¡n definidas en `AGENTS.md`.
Esta secciÃ³n conserva solo los comandos de referencia para inspeccionar compatibilidad estructural cuando haga falta.

```bash
# 1. Verificar que la rama fue creada desde origin/main
git log --oneline origin/main..nombre-rama

# 2. Comparar estructura de archivos
git diff origin/main nombre-rama -- --name-only

# 3. Si los paths difieren â†’ ABORTAR
git merge --abort
```

Si hay incompatibilidad estructural:
1. Abortar el merge.
2. Crear nueva rama desde `origin/main`: `git checkout -b claude/apply-[nombre]-[ID] origin/main`
3. Analizar commits de la rama incompatible uno por uno: `git show [hash]`
4. Aplicar los cambios manualmente sobre los paths correctos de `main`.
5. Compilar y merge normal.

### Checklist Pre-merge a `main`

Obligatorio cuando el cambio afecta BD, migraciones, `init_db()`, flujos crÃ­ticos o sistema de recargas:

1. CompilaciÃ³n sin errores: `python -m py_compile ...`
2. No duplicaciones: `git grep` limpio
3. Arranque sin crash, tablas creadas, inserciones reales funcionan
4. `DATABASE_URL` presente en PROD
5. VerificaciÃ³n funcional: `/start`, `/menu`, registro real, cambio de estado
6. Evidencia documentada antes de merge (cuando afecte BD o flujos crÃ­ticos)

---

## GestiÃ³n de Roles (Panel Web - FastAPI)

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
- `is_admin(user)` â†’ verifica si tiene rol administrativo
- `can_access_system(user)` â†’ verifica si el estado le permite operar
- `is_blocked(user)` â†’ verifica si estÃ¡ bloqueado

---

## Convenciones de CÃ³digo

### Python (Backend)

- Python 3.11+ (segÃºn Dockerfile)
- Sin type hints en cÃ³digo existente (no agregar innecesariamente)
- Sin f-strings de Markdown en mensajes del bot (prohibido `parse_mode`)
- Imports agrupados: stdlib â†’ terceros â†’ locales
- Funciones de BD retornan `dict` (RealDictCursor en Postgres, Row con acceso por clave en SQLite)

### TypeScript/Angular (Frontend)

- Angular 21 con standalone components
- SSR habilitado con `@angular/ssr`
- Prettier configurado: `printWidth: 100`, `singleQuote: true`
- Tests con vitest (no Jest ni Karma)
- SeparaciÃ³n en: `core/` (guards, interceptors, services) y `features/` (vistas)

---

## Sistema de Recargas (Reglas CrÃ­ticas)

El sistema de recargas transfiere saldo del Admin hacia Repartidores/Aliados. Es el componente financiero mÃ¡s crÃ­tico.

### Reglas de Integridad
- Toda aprobaciÃ³n/rechazo es **idempotente**: no se puede procesar dos veces la misma solicitud.
- En concurrencia (approve vs reject simultÃ¡neos), **solo una operaciÃ³n gana**.
- ActualizaciÃ³n de balance + registro en ledger son **atÃ³micos** (misma transacciÃ³n).
- Solo el Admin propietario puede aprobar recargas a su equipo.

### Estados de Recarga

| TransiciÃ³n | Efecto |
|-----------|--------|
| `PENDING` â†’ `APPROVED` | Balance transferido, ledger registrado |
| `PENDING` â†’ `REJECTED` | Sin cambio de balance ni ledger |
| `APPROVED` / `REJECTED` | Estado terminal. **PROHIBIDO** cambiar. |

### VerificaciÃ³n Obligatoria Antes de Aprobar
```python
# Verificar que el estado sigue siendo PENDING (SELECT FOR UPDATE en Postgres)
# Si ya cambiÃ³: retornar (False, "Ya procesado") sin tocar nada
```

Los estados usan `normalize_role_status()` antes de persistir. **PROHIBIDO** modificar balance sin registro en ledger.

### Modelo de Contabilidad de Doble Entrada

El sistema implementa contabilidad de doble entrada. El Admin de Plataforma no tiene saldo ilimitado; debe registrar ingresos externos antes de poder aprobar recargas.

**Flujo de fondos:**

```
Pago externo (transferencia/efectivo)
  â†’ register_platform_income(admin_id, amount, method, note)  [db.py]
  â†’ admins.balance += amount
  â†’ ledger: kind=INCOME | from_type=EXTERNAL | from_id=0 â†’ to_type=PLATFORM/ADMIN

Admin aprueba recarga a repartidor o aliado
  â†’ approve_recharge_request()  [services.py]
  â†’ admins.balance -= amount
  â†’ admin_couriers.balance o admin_allies.balance += amount
  â†’ ledger: kind=RECHARGE | from_type=PLATFORM/ADMIN | from_id=admin_id â†’ to_type=COURIER/ALLY
```

Las restricciones obligatorias de contabilidad y saldo estÃ¡n en `AGENTS.md`.
AquÃ­ se documenta el modelo funcional ya implementado y los puntos donde ese comportamiento vive.

**Flujo de UI â€” Registrar ingreso externo** (`ingreso_conv`, `main.py`):
- Estados: `INGRESO_MONTO=970`, `INGRESO_METODO=971`, `INGRESO_NOTA=972`
- Prefijo callbacks: `ingreso_`
- Claves user_data: `ingreso_monto`, `ingreso_metodo`
- FunciÃ³n en db.py: `register_platform_income(admin_id, amount, method, note)`
- Re-exportada en services.py; importada en main.py desde services.py

### Recarga Directa con Plataforma como Fallback

Un aliado o repartidor puede siempre solicitar recarga directamente al Admin de Plataforma, aunque pertenezca a un equipo de Admin Local. Los casos habilitados son:
1. El Admin Local no tiene saldo suficiente.
2. El Admin Local no responde o no procesa la recarga.

**Regla del interruptor de ganancias:**
El saldo recargado pertenece a quien lo aportÃ³. Las ganancias generadas por ese saldo fluyen hacia el mismo aportante:
- Saldo aportado por Admin Local â†’ ganancias al Admin Local.
- Saldo aportado por Plataforma â†’ ganancias a Plataforma.

Al agotarse el saldo de plataforma y recargar nuevamente con el Admin Local, el flujo de ganancias vuelve al Admin Local. El Admin Local que no recarga a tiempo pierde las ganancias de ese usuario mientras el saldo activo provenga de plataforma.

**ImplementaciÃ³n tÃ©cnica (IMPLEMENTADO 2026-03-03):**
- `main.py â†’ recargar_monto`: muestra "Plataforma" siempre para COURIER/ALLY.
- `main.py â†’ recargar_admin_callback`: permite `platform_id` aunque no estÃ© en `approved_links`. Detecta admin PENDING y redirige a Plataforma.
- `services.py â†’ approve_recharge_request`: cuando Plataforma aprueba para COURIER/ALLY, crea o actualiza un vÃ­nculo directo `admin_couriers`/`admin_allies` con `admin_id = platform_id`. El vÃ­nculo plataforma queda `APPROVED`; todos los otros vÃ­nculos del usuario quedan `INACTIVE`. Ledger registra `PLATFORM â†’ COURIER/ALLY`. Cuando Admin Local re-recarga, el vÃ­nculo local pasa a `APPROVED` y plataforma a `INACTIVE` (interruptor).
- `db.py â†’ _sync_courier_link_status` y `_sync_ally_link_status`: usan `updated_at DESC` (no `created_at`) para determinar el vÃ­nculo activo en cambios de estado. Garantiza que el vÃ­nculo del Ãºltimo financiador siempre sea el activo.

**Restricciones absolutas:**
- PROHIBIDO bloquear la opciÃ³n plataforma por ausencia de vÃ­nculo `admin_couriers`/`admin_allies`.
- PROHIBIDO aprobar si `admins.balance` (plataforma) < monto solicitado.
- Todo movimiento debe registrarse en ledger con el origen correcto.

### Red Cooperativa â€” Todos los Couriers para Todos los Aliados (IMPLEMENTADO 2026-03-03)

La plataforma opera como una **red cooperativa**: cualquier repartidor activo (de cualquier admin) puede tomar pedidos de cualquier aliado (de cualquier admin). No existen equipos aislados.

**Regla de elegibilidad:**
- `get_eligible_couriers_for_order` en `db.py` NO filtra por `admin_id`. Retorna todos los repartidores con `admin_couriers.status = 'APPROVED'` y `couriers.status = 'APPROVED'`.
- El parÃ¡metro `admin_id` existe pero es opcional (`admin_id=None`) y se ignora en la query.

**Modelo de comisiones (simÃ©trico):**
- Aliado crea pedido â†’ fee $300 al aliado al entregar (o al expirar sin courier) â†’ $200 al admin del aliado, $100 a Plataforma.
- Courier entrega pedido â†’ fee $300 al courier â†’ $200 al admin del courier, $100 a Plataforma.
- Cada admin gana $200 por cada servicio de sus propios miembros, sin importar con quiÃ©n interactÃºan.
- Si el admin es Plataforma: gana los $300 completos (no hay split).
- Pedidos creados por admin (admin_pedido): **el admin creador no paga fee**; solo paga el courier que entrega ($200 su admin, $100 a Plataforma).

**Flujo tÃ©cnico post-implementaciÃ³n:**
```
Aliado (Admin A) crea pedido
  â†’ publish_order_to_couriers(admin_id=A)
  â†’ check_service_fee_available(ALLY, ally_id, admin_id=A)   # verifica que aliado tenga $300
  â†’ get_eligible_couriers_for_order(ally_id=X)               # Sin filtro â†’ TODOS los couriers activos
  â†’ Para cada courier: get_approved_admin_id_for_courier(courier_id) â†’ courier_admin_id
    â†’ check_service_fee_available(COURIER, courier_id, courier_admin_id)
    â†’ Solo pasan couriers con saldo en su propio admin ($300 mÃ­nimo)

Courier (Admin B) acepta
  â†’ courier_admin_id_snapshot = B (guardado en orders al aceptar)

Courier entrega
  â†’ apply_service_fee(ALLY, ally_id, admin_id=A)
      admin_allies.balance(aliado) âˆ’$300 | admins.balance(Admin A) +$200 | admins.balance(Plataforma) +$100
  â†’ apply_service_fee(COURIER, courier_id, admin_id=B)
      admin_couriers.balance(courier) âˆ’$300 | admins.balance(Admin B) +$200 | admins.balance(Plataforma) +$100
```

**Archivos modificados:**
- `db.py â†’ get_eligible_couriers_for_order`: sin filtro `AND ac.admin_id = {P}`, `params = []`
- `order_delivery.py â†’ publish_order_to_couriers`: fee check usa `get_approved_admin_id_for_courier(courier_id)` por courier; elimina lÃ³gica de `admin_without_balance` global
- `order_delivery.py â†’ _handle_delivered`: `ally_admin_id` desde `get_approved_admin_link_for_ally`; `courier_admin_id` desde `order["courier_admin_id_snapshot"]` con fallback a `get_approved_admin_link_for_courier`; cada fee usa su propio admin; balance post-fee usa `courier_admin_id`

---

### SincronizaciÃ³n de Estado en Tablas de VÃ­nculo

`admin_allies.status` y `admin_couriers.status` son campos independientes de `allies.status` y `couriers.status`. Ambos **siempre deben estar sincronizados**.

**Bug sÃ­ntoma:** "No hay admins disponibles para procesar recargas" al intentar recargar un aliado/repartidor reciÃ©n aprobado. Ocurre cuando `allies.status = APPROVED` pero `admin_allies.status` sigue en `PENDING`.

**SoluciÃ³n implementada â€” helpers en `db.py`:**
- `_sync_ally_link_status(cur, ally_id, status, now_sql)`: sincroniza `admin_allies.status` al final de cada actualizaciÃ³n de estado de aliado.
- `_sync_courier_link_status(cur, courier_id, status, now_sql)`: Ã­dem para repartidores.
- Ambos se llaman dentro de `update_ally_status()`, `update_ally_status_by_id()`, `update_courier_status()`, `update_courier_status_by_id()`, antes de `conn.commit()`.

**Comportamiento del sync:**
- Si `status == "APPROVED"`: el vÃ­nculo mÃ¡s recientemente actualizado (por `updated_at DESC`) â†’ `APPROVED`; el resto â†’ `INACTIVE`. El `updated_at` se actualiza en cada recarga, por lo que el Ãºltimo financiador es siempre el equipo activo.
- Si `status != "APPROVED"`: todos los vÃ­nculos del usuario â†’ `INACTIVE`.

---

## Sistema de Tracking de Llegada (order_delivery.py)

Implementado en commit `b06fc3e`. Controla el ciclo post-aceptaciÃ³n del courier hasta la confirmaciÃ³n de llegada al punto de recogida.

### Flujo completo

```
Oferta publicada â†’ courier acepta
  â†“ _handle_accept
  - Mensaje SIN datos del cliente (solo barrio destino + tarifa + pickup address)
  - Mensaje incluye instruccion explicita: navegar al pickup (Google Maps/Waze) y liberar si no puede llegar
  - Guarda courier_accepted_lat/lng en orders (base para T+5)
  - Programa 3 jobs:
      arr_inactive_{id}  T+5 min
      arr_warn_{id}      T+15 min
      arr_deadline_{id}  T+20 min

  T+5:  Â¿Movimiento â‰¥50m hacia pickup? No â†’ _release_order_by_timeout
  T+15: Notificar aliado (Buscar otro / Llamar / Seguir esperando) + advertir courier
  T+20: _release_order_by_timeout automÃ¡tico

  (En paralelo, cada live location update llama check_courier_arrival_at_pickup)
  GPS detecta â‰¤100m del pickup:
    â†’ set_courier_arrived (idempotente)
    â†’ _cancel_arrival_jobs (cancela T+5/T+15/T+20)
    â†’ upsert_order_pickup_confirmation(PENDING)
    â†’ _notify_ally_courier_arrived (botones: Confirmar / No ha llegado)

  Aliado confirma (order_pickupconfirm_approve_):
    â†’ _handle_pickup_confirmation_by_ally(approve=True)
    â†’ status = PICKED_UP
    â†’ _notify_courier_pickup_approved â†’ courier recibe customer_name/phone/address exacta (en oferta solo ve mapas + ciudad/barrio)
```

- Para rutas: `order_delivery.py Ã¢â€ â€™ _handle_route_accept` tambiÃƒÂ©n incluye instrucciÃƒÂ³n de navegaciÃƒÂ³n al pickup (Google Maps/Waze) y opciÃƒÂ³n de liberar ruta.

### Constantes (order_delivery.py)

| Constante | Valor | DescripciÃ³n |
|-----------|-------|-------------|
| `ARRIVAL_INACTIVITY_SECONDS` | 300 (5 min) | Timeout de inactividad Rappi-style |
| `ARRIVAL_WARN_SECONDS` | 900 (15 min) | NotificaciÃ³n al aliado |
| `ARRIVAL_DEADLINE_SECONDS` | 1200 (20 min) | Auto-liberaciÃ³n |
| `ARRIVAL_RADIUS_KM` | 0.1 (100 m) | Radio de detecciÃ³n de llegada |
| `ARRIVAL_MOVEMENT_THRESHOLD_KM` | 0.05 (50 m) | Movimiento mÃ­nimo hacia pickup en T+5 |

### Funciones nuevas en order_delivery.py

| FunciÃ³n | DescripciÃ³n |
|---------|-------------|
| `check_courier_arrival_at_pickup(courier_id, lat, lng, context)` | PÃºblica. Llamada desde main.py en cada live location |
| `_cancel_arrival_jobs(context, order_id)` | Cancela los 3 jobs por nombre |
| `_release_order_by_timeout(order_id, courier_id, context, reason)` | LiberaciÃ³n centralizada (T+5 y T+20) |
| `_arrival_inactivity_job(context)` | Job T+5 |
| `_arrival_warn_ally_job(context)` | Job T+15 |
| `_arrival_deadline_job(context)` | Job T+20 |
| `_notify_ally_courier_arrived(context, order, courier_name)` | NotificaciÃ³n al aliado con botones |
| `_handle_find_another_courier(update, context, order_id)` | Callback aliado busca otro |
| `_handle_wait_courier(update, context, order_id)` | Callback aliado sigue esperando |

### Nuevas columnas en `orders`

| Columna | Tipo | DescripciÃ³n |
|---------|------|-------------|
| `courier_arrived_at` | SQLite: TEXT / Postgres: TIMESTAMP | Timestamp cuando GPS detecta llegada (â‰¤100m). NULL = no llegÃ³ aÃºn |
| `courier_accepted_lat` | REAL | Latitud del courier al momento de aceptar (base para T+5) |
| `courier_accepted_lng` | REAL | Longitud del courier al momento de aceptar (base para T+5) |

### Nuevas funciones en db.py

- `set_courier_arrived(order_id)` â€” idempotente, solo actÃºa si `courier_arrived_at IS NULL`
- `set_courier_accepted_location(order_id, lat, lng)` â€” guarda posiciÃ³n al aceptar
- `get_active_order_for_courier(courier_id)` â€” retorna orden activa del courier (`ACCEPTED`/`PICKED_UP`)
- `get_active_route_for_courier(courier_id)` â€” retorna ruta activa del courier (`ACCEPTED`)

Re-exportadas en `services.py`.

### Pendientes (NO implementado aÃºn)

- Cuenta regresiva visible (countdown) en la oferta/estado post-aceptaciÃ³n.
- BotÃ³n explÃ­cito "LleguÃ©" para courier (hoy es detecciÃ³n automÃ¡tica por live location).
- Persistencia fuerte ante reinicios: los jobs T+5/T+15/T+20 y `excluded_couriers` viven en memoria (`context.bot_data`) y se pierden si el proceso se reinicia.

---

## Sistema de Incentivos (order_delivery.py + main.py)

### Incentivo al crear pedido (aliado)

Disponible en el flujo de creaciÃ³n de pedido (`nuevo_pedido_conv`). Antes de confirmar, el aliado puede agregar un incentivo adicional con botones fijos (+$1.000, +$1.500, +$2.000, +$3.000) o monto libre.

- Estado: `PEDIDO_INCENTIVO_MONTO = 60`
- ConversationHandler: `pedido_incentivo_conv` (entry point: `pedido_add_incentivo_{id}`)
- DB: `add_order_incentive(order_id, delta)` en `db.py`, re-exportada en `services.py`
- `ally_increment_order_incentive(telegram_id, order_id, delta)` en `services.py`

### Ciclo de pedido actualizado (IMPLEMENTADO 2026-03-09)

**Ciclo de pedido**

0 min â†’ pedido publicado  
5 min â†’ sugerencia de incentivo adicional  
10 min â†’ expiraciÃ³n automÃ¡tica  

**CancelaciÃ³n del aliado**

â‰¤60 segundos desde creaciÃ³n â†’ cancelaciÃ³n sin costo  
>60 segundos desde creaciÃ³n â†’ cobro de $300  
ExpiraciÃ³n automÃ¡tica â†’ cobro de $300  
Pedidos creados por administrador (ally_id = None) â†’ nunca se cobra comisiÃ³n  

### Sugerencia T+5 â€” "Nadie ha tomado el pedido" (IMPLEMENTADO 2026-03-06)

Aplica a **todos los pedidos** (aliado y admin). 5 minutos despuÃ©s de publicar el pedido, si sigue en status `PUBLISHED` (ningÃºn courier lo aceptÃ³), se envÃ­a un mensaje al creador sugiriendo agregar incentivo.

**Constante:** `OFFER_NO_RESPONSE_SECONDS = 300` (order_delivery.py)

**Flujo:**
1. `publish_order_to_couriers()` programa job `offer_no_response_{order_id}` con T+5.
2. Al dispararse: `_offer_no_response_job(context)` â€” verifica que el pedido siga en `PUBLISHED`, obtiene `telegram_id` del creador (aliado o admin), envÃ­a mensaje con botones.
3. Si courier acepta antes del T+5: `_cancel_no_response_job(context, order_id)` cancela el job.
4. Si aliado/admin cancela el pedido: tambiÃ©n se cancela el job.
5. La sugerencia es Ãºnica (no se repite si el admin no agrega incentivo).

**Botones de la sugerencia:** `offer_inc_{id}x1500`, `offer_inc_{id}x2000`, `offer_inc_{id}x3000`, `offer_inc_otro_{id}`

**Al agregar incentivo desde la sugerencia:**
- `offer_suggest_inc_fixed_callback` (patrÃ³n `^offer_inc_\d+x(1500|2000|3000)$`)
- `offer_suggest_inc_otro_start` â†’ estado `OFFER_SUGGEST_INC_MONTO = 915` â†’ `offer_suggest_inc_monto_handler`
- Llama `ally_increment_order_incentive` o `admin_increment_order_incentive` segÃºn tipo de pedido
- Llama `repost_order_to_couriers(order_id, context)` â†’ re-oferta a todos los couriers activos + reinicia T+5

**Re-oferta (`repost_order_to_couriers`):**
- Limpia `excluded_couriers` del `bot_data` para ese pedido
- Llama `clear_offer_queue(order_id)` (borra queue en BD)
- Llama `publish_order_to_couriers(order_id, ally_id, context, skip_fee_check=True, ...)`
- `skip_fee_check=True` omite verificaciÃ³n de saldo (ya verificada al crear el pedido)

**Funciones clave:**
- `order_delivery.py`: `_cancel_no_response_job`, `_offer_no_response_job`, `repost_order_to_couriers`
- `main.py`: `offer_suggest_inc_fixed_callback`, `offer_suggest_inc_otro_start`, `offer_suggest_inc_monto_handler`, `offer_suggest_inc_conv`
- `services.py`: `admin_get_order_for_incentive(telegram_id, order_id)`, `admin_increment_order_incentive(telegram_id, order_id, delta)`
- `db.py`: `clear_offer_queue(order_id)`

---

## Pedido Especial del Admin (IMPLEMENTADO 2026-03-06)

Permite a un Admin Local o Admin de Plataforma crear pedidos directamente, con tarifa libre (sin cÃ¡lculo automÃ¡tico) y sin dÃ©bito de saldo.

### CaracterÃ­sticas

- **Sin fee al admin creador**: el admin no paga comisiÃ³n por crear el pedido. El courier que lo entrega sÃ­ paga su fee normal ($300).
- **Sin fee check del aliado**: no hay aliado, `ally_id=NULL`, `skip_fee_check=True` omite la verificaciÃ³n de saldo.
- **Tarifa manual**: el admin ingresa el monto que pagarÃ¡ al courier.
- **Sin dÃ©bito de saldo al admin**: el pago de la tarifa al courier se maneja fuera del sistema.
- **`creator_admin_id`**: nueva columna en `orders` que identifica al admin creador (NULL = pedido de aliado).
- **`ally_id = NULL`**: los pedidos especiales de admin no tienen `ally_id`.
- **Direcciones de recogida**: el admin gestiona sus propias ubicaciones de pickup en `admin_locations`.
- **Incentivos opcionales**: se pueden agregar incentivos (+$1.500/+$2.000/+$3.000/libre) antes de publicar.
- **T+5 aplica igual**: si nadie acepta en 5 min, recibe la sugerencia de incentivo.

### Tabla `admin_locations`

| Columna | Tipo | DescripciÃ³n |
|---------|------|-------------|
| `id` | BIGSERIAL/INTEGER | PK |
| `admin_id` | BIGINT | FK â†’ admins.id |
| `label` | TEXT | Nombre/etiqueta de la ubicaciÃ³n |
| `address` | TEXT | DirecciÃ³n completa |
| `city` | TEXT | Ciudad |
| `barrio` | TEXT | Barrio |
| `phone` | TEXT | TelÃ©fono del punto (opcional) |
| `lat` | REAL | Latitud |
| `lng` | REAL | Longitud |
| `is_default` | INTEGER | 1 = default del admin |
| `use_count` | INTEGER | Contador de usos |
| `is_frequent` | INTEGER | 1 = direcciÃ³n frecuente |
| `last_used_at` | TIMESTAMP | Ãšltima vez usada |
| `created_at` | TIMESTAMP | Fecha de creaciÃ³n |

### Funciones en `db.py`

- `create_admin_location(admin_id, label, address, city, barrio, phone=None, lat=None, lng=None) â†’ int`
- `get_admin_locations(admin_id) â†’ list`
- `get_admin_location_by_id(location_id, admin_id) â†’ dict`
- `get_default_admin_location(admin_id) â†’ dict`
- `set_default_admin_location(location_id, admin_id)`
- `increment_admin_location_usage(location_id, admin_id)`

Todas re-exportadas en `services.py`.

### Flujo de creaciÃ³n (`admin_pedido_conv` en `main.py`)

```
Entry: callback admin_nuevo_pedido
  â†’ admin_nuevo_pedido_start()
  â†’ Estado ADMIN_PEDIDO_PICKUP (908)

ADMIN_PEDIDO_PICKUP:
  admin_pedido_pickup_callback  â†’ selecciona ubicaciÃ³n guardada â†’ ADMIN_PEDIDO_CUST_NAME
  admin_pedido_nueva_dir_start  â†’ pide texto â†’ ADMIN_PEDIDO_PICKUP
  admin_pedido_pickup_text_handler â†’ geocodifica â†’ muestra confirmaciÃ³n
  admin_pedido_geo_pickup_callback (si/no) â†’ confirma pickup â†’ ADMIN_PEDIDO_CUST_NAME
  admin_pedido_pickup_gps_handler â†’ guarda GPS â†’ ADMIN_PEDIDO_CUST_NAME

ADMIN_PEDIDO_CUST_NAME (909): admin_pedido_cust_name_handler â†’ ADMIN_PEDIDO_CUST_PHONE
ADMIN_PEDIDO_CUST_PHONE (910): admin_pedido_cust_phone_handler â†’ ADMIN_PEDIDO_CUST_ADDR

ADMIN_PEDIDO_CUST_ADDR (911):
  admin_pedido_cust_addr_handler â†’ geocodifica â†’ muestra confirmaciÃ³n
  admin_pedido_geo_callback (si/no) â†’ confirma â†’ ADMIN_PEDIDO_TARIFA
  admin_pedido_cust_gps_handler â†’ guarda GPS â†’ ADMIN_PEDIDO_TARIFA

ADMIN_PEDIDO_TARIFA (912): admin_pedido_tarifa_handler â†’ ADMIN_PEDIDO_INSTRUC

ADMIN_PEDIDO_INSTRUC (913):
  admin_pedido_instruc_handler / admin_pedido_sin_instruc_callback â†’ preview
  admin_pedido_inc_fijo_callback (1500/2000/3000) â†’ actualiza preview
  admin_pedido_inc_otro_callback â†’ ADMIN_PEDIDO_INC_MONTO
  admin_pedido_confirmar_callback â†’ crea pedido â†’ publica â†’ END

ADMIN_PEDIDO_INC_MONTO (916): admin_pedido_inc_monto_handler â†’ preview â†’ ADMIN_PEDIDO_INSTRUC
```

### Estados

| Constante | Valor | DescripciÃ³n |
|-----------|-------|-------------|
| `ADMIN_PEDIDO_PICKUP` | 908 | SelecciÃ³n de punto de recogida |
| `ADMIN_PEDIDO_CUST_NAME` | 909 | Nombre del cliente |
| `ADMIN_PEDIDO_CUST_PHONE` | 910 | TelÃ©fono del cliente |
| `ADMIN_PEDIDO_CUST_ADDR` | 911 | DirecciÃ³n de entrega (con geocoding) |
| `ADMIN_PEDIDO_TARIFA` | 912 | Tarifa manual al courier |
| `ADMIN_PEDIDO_INSTRUC` | 913 | Instrucciones + preview final |
| `OFFER_SUGGEST_INC_MONTO` | 915 | Monto libre en sugerencia T+5 |
| `ADMIN_PEDIDO_INC_MONTO` | 916 | Monto libre de incentivo en creaciÃ³n admin |

### User data keys del flujo (prefijo `admin_ped_`)

| Clave | Contenido |
|-------|-----------|
| `admin_ped_admin_id` | ID interno del admin en DB |
| `admin_ped_pickup_id` | ID de admin_location (None si GPS/nueva) |
| `admin_ped_pickup_addr` | DirecciÃ³n de recogida (texto) |
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

### PublicaciÃ³n del pedido admin

En `admin_pedido_confirmar_callback`:
1. `create_order(ally_id=None, creator_admin_id=admin_id, ...)` â€” crea el pedido
2. `publish_order_to_couriers(order_id, None, context, admin_id_override=admin_id, skip_fee_check=True)` â€” publica a todos los couriers activos
3. `increment_admin_location_usage(pickup_location_id, admin_id)` â€” si ubicaciÃ³n guardada

**Nota:** `skip_fee_check=True` omite la verificaciÃ³n previa de saldo del aliado (no hay aliado). El courier que acepta el pedido sÃ­ paga su fee normal al entregar ($300 â†’ $200 a su admin, $100 a Plataforma). El admin creador no paga ninguna comisiÃ³n.

---

## Cotizador y Uso de APIs (Control de Costos)

El cotizador usa **Google Maps API** (Distance Matrix / Places). Tiene cuota diaria limitada.

### Regla de Cuota
- **PROHIBIDO** llamar a la API sin verificar `api_usage_daily` primero.
- Si `api_usage_daily >= lÃ­mite`: retornar error informativo, **no llamar** a la API.
- Toda llamada debe incrementar `api_usage_daily` de forma atÃ³mica.

<<<<<<< HEAD
### Costeo por OperaciÃ³n (Google Maps) â€” IMPLEMENTADO

AdemÃ¡s del fusible diario (`api_usage_daily`), existe tracking por evento para estimar costo promedio por tipo de operaciÃ³n:

- Tabla: `api_usage_events` (SQLite y PostgreSQL).
- InserciÃ³n oficial: `Backend/db.py:record_api_usage_event()` (INSERT en `api_usage_events` + incrementa `api_usage_daily` en la misma transacciÃ³n).
- InstrumentaciÃ³n centralizada: `Backend/services.py` registra eventos en:
  - `google_place_details()` â†’ `place_details`
  - `google_geocode_forward()` â†’ `geocode_forward`
  - `google_places_text_search()` â†’ `places_text_search`
  - `get_distance_from_api_coords()` â†’ `distance_matrix_coords`
  - `get_distance_from_api()` â†’ `distance_matrix_text`
- EstimaciÃ³n de costo por variables de entorno (valores en USD por llamada):
=======
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
- Estimación de costo por variables de entorno (valores en USD por llamada; ajustar según precios actuales de Google):
>>>>>>> verify/google-maps-usage-cost-20260302
  - `GOOGLE_COST_USD_PLACE_DETAILS`
  - `GOOGLE_COST_USD_GEOCODE_FORWARD`
  - `GOOGLE_COST_USD_PLACES_TEXT_SEARCH`
  - `GOOGLE_COST_USD_DISTANCE_MATRIX_COORDS`
  - `GOOGLE_COST_USD_DISTANCE_MATRIX_TEXT`
- Privacidad: **PROHIBIDO** guardar direcciones/coords o cualquier PII en `api_usage_events.meta_json`. Solo metadata no sensible (status, provider, mode).
<<<<<<< HEAD
- Helper de consulta rÃ¡pida: `Backend/services.py:get_google_maps_cost_summary(days=7)`.

### Regla de CachÃ©
=======

Helper disponible para consulta rápida desde Python: `Backend/services.py:get_google_maps_cost_summary(days=7)`.

### Regla de Caché
>>>>>>> verify/google-maps-usage-cost-20260302
- Distancias entre pares de coordenadas **deben cachearse** en base de datos.
- **PROHIBIDO** recalcular una distancia ya cacheada para la misma consulta.

### Regla de GeocodificaciÃ³n
- Coordenadas (lat/lng) se capturan vÃ­a Telegram (ubicaciÃ³n GPS). La API solo se usa para geocodificaciÃ³n inversa o bÃºsqueda de direcciones escritas.
- **PROHIBIDO** usar la API para validar ubicaciones que ya tienen GPS vÃ¡lido.
- Todo flujo que reciba direcciones por texto (cotizar, pedido, pickup, ruta) debe reutilizar el pipeline de resoluciÃ³n de cotizaciÃ³n: `resolve_location(texto)` + confirmaciÃ³n de candidato geocodificado (si/no) + fallback con `resolve_location_next(...)` antes de exigir GPS.

### Manejo de Errores de API
- Si la API falla: retornar error claro al usuario. **PROHIBIDO** propagar excepciones sin capturar ni reintentar automÃ¡ticamente.

---

## Flujo de Trabajo con IA

### Donde documentar

Regla de routing â€” tabla completa en **AGENTS.md SecciÃ³n 16**.

Regla de cambios estructurales â€” tabla completa en **AGENTS.md SecciÃ³n 17**:
todo cambio estructural (nueva tabla, mÃ³dulo, variable de entorno, callback, flow)
debe documentarse en la secciÃ³n correspondiente de este archivo **en el mismo commit**.
El `git log` es el historial cronolÃ³gico. CLAUDE.md es la referencia de estado actual.

Regla de routing â€” tabla completa en **AGENTS.md SecciÃ³n 16**:

| Contenido | Destino |
|-----------|--------|
| Regla, restricciÃ³n, protocolo obligatorio | `AGENTS.md` |
| Arquitectura, flujo, convenciÃ³n operativa | `CLAUDE.md` |
| SesiÃ³n activa o cierre de agente | `WORKLOG.md` |
| Regla + detalle operativo | `AGENTS.md` (regla) + `CLAUDE.md` (detalle) |

Si el contenido ya estÃ¡ cubierto en AGENTS.md: CLAUDE.md solo agrega referencia o comandos, nunca repite.

### ColaboraciÃ³n entre Agentes IA (Claude Code y Codex)

Luis Felipe trabaja en VS Code con mÃºltiples agentes activos simultÃ¡neamente: **Claude Code** y **Codex**.
En ocasiones ambos agentes trabajan al mismo tiempo sobre la misma rama (`staging`).
Las reglas completas estÃ¡n en `AGENTS.md`.
AquÃ­ solo se conserva un resumen operativo y las referencias a comandos que ayudan a coordinar el trabajo.

#### WORKLOG.md â€” Registro de sesiones

Archivo en la raÃ­z del repo que cada agente actualiza al iniciar y cerrar sesiÃ³n.

**Al iniciar:**
```bash
git pull origin staging
git log --oneline -15 origin/staging   # ver quÃ© hizo el otro agente
cat WORKLOG.md                          # ver sesiones activas
# Agregar entrada en "Sesiones activas" y hacer commit+push:
git commit -m "[claude] worklog: inicio â€” <tarea breve>"
git push origin staging
```

**Al cerrar:**
```bash
# Mover entrada a "Historial" con estado COMPLETADO/PENDIENTE y hacer commit del WORKLOG
git commit -m "[claude] worklog: cierre â€” <tarea breve>"

# PROTOCOLO PRE-PUSH OBLIGATORIO:
git fetch origin staging
git log --oneline HEAD..origin/staging    # hay commits nuevos del otro agente?
git diff --name-only HEAD origin/staging  # solapan con tus archivos?

# Sin solapamiento -> push normal
git push origin staging

# Con solapamiento en mismos archivos -> PAUSAR
# Reportar a Luis Felipe antes de pushear
```

> Si hay solapamiento real con commits nuevos del otro agente, revisar `AGENTS.md` y escalar la decisiÃ³n a Luis Felipe.

#### Prefijo obligatorio en commits

| Agente | Formato |
|--------|---------|
| Claude Code | `[claude] feat: descripciÃ³n` |
| Codex | `[codex] feat: descripciÃ³n` |

Para filtrar por agente: `git log --oneline --grep="[claude]"`

#### Pautas de no-interferencia

- No modificar o revertir trabajo del otro agente sin autorizaciÃ³n de Luis Felipe.
- Si se detecta un error del otro agente: reportarlo con evidencia y esperar instrucciÃ³n.
- Si se detecta solapamiento en `WORKLOG.md` o `git log`: pausar y notificar a Luis Felipe.
- Si `git push` es rechazado por fast-forward: revisar estado remoto y seguir el protocolo de `AGENTS.md`.

#### Archivos de alto riesgo

Verificar WORKLOG.md y `git log --follow -5 <archivo>` antes de editar cualquiera de estos:
`Backend/main.py` Â· `Backend/services.py` Â· `Backend/db.py` Â· `Backend/order_delivery.py` Â· `AGENTS.md` Â· `CLAUDE.md`

La coordinaciÃ³n entre agentes pasa por Luis Felipe.

### Antes de Cambiar CÃ³digo
1. Mostrar el **bloque exacto** que se va a modificar.
2. Explicar brevemente **quÃ©** se cambia y **por quÃ©**.
3. Confirmar: rama activa + archivo exacto.

### Durante el Trabajo
- No asumir errores solo por ver diffs.
- No repetir pasos ya completados.
- No reescribir archivos completos sin autorizaciÃ³n.
- Trabajar **solo** en el objetivo indicado. **PROHIBIDO** ampliar alcance sin aprobaciÃ³n.
- Cambios mÃ­nimos: un solo objetivo por instrucciÃ³n.

### Cuando el tool Edit no persiste los cambios

**Sintoma:** Edit reporta exito pero `git diff` no muestra el cambio, o el archivo vuelve a su estado previo.  
**Causa:** linter del IDE o servidor de lenguaje revierte el archivo inmediatamente al guardarlo.

**Procedimiento:**
1. Detectar con `git diff --name-only` que el cambio no persiste.
2. Cambiar de estrategia al tercer intento fallido â€” no seguir reintentando Edit.
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

### DespuÃ©s de los Cambios

Ejecutar siempre:
```bash
cd Backend/
python -m py_compile main.py services.py db.py order_delivery.py profile_changes.py
```

Verificar imports huÃ©rfanos tras mover o eliminar funciones:
```bash
git grep "nombre_funcion" -- "*.py"
# Si solo aparece en el bloque import y en ningÃºn otro lugar â†’ importaciÃ³n huÃ©rfana, eliminar
```

Reportar claramente: quÃ© cambiÃ³, quÃ© se eliminÃ³, por quÃ©.

### Veracidad TÃ©cnica

Siempre separar entre:
- **IMPLEMENTADO**: existe en el cÃ³digo hoy. Indicar `archivo:funciÃ³n`.
- **PROPUESTA / FUTURO**: no existe aÃºn. Indicarlo explÃ­citamente.

**PROHIBIDO** afirmar que algo existe sin verificarlo primero.

### Protocolo de Decisiones

```
Exponer opciones â†’ preguntar â†’ esperar confirmaciÃ³n â†’ ejecutar
```

**PROHIBIDO** cerrar decisiones de cambio por iniciativa propia.

### Estilo de ColaboraciÃ³n

- Priorizar **estabilidad** sobre velocidad.
- Preguntar antes de decidir. No improvisar soluciones.
- Asumir que el usuario es tÃ©cnico, detallista y quiere **control total** del sistema.

---

## Contexto de Negocio Relevante

- El sistema opera en **Colombia** (moneda: COP, telÃ©fonos: +57XXXXXXXXXX).
- El cotizador usa la API de Google Maps para calcular distancias. Hay un lÃ­mite diario de llamadas (`api_usage_daily`) para controlar costos.
- El sistema de recargas transfiere saldo del Admin a Repartidores/Aliados. Es crÃ­tico que sea idempotente ante concurrencia.
- Los pedidos siguen el ciclo: `PENDING` â†’ publicado a repartidores â†’ aceptado â†’ recogida confirmada â†’ entregado (o cancelado en cualquier paso).
- La plataforma opera como **red cooperativa**: cualquier repartidor activo puede tomar pedidos de cualquier aliado, sin importar a quÃ© admin pertenece cada uno. No existen equipos aislados para el despacho de pedidos.
- Un Admin Local gestiona su equipo (aprueba/inactiva repartidores y aliados) y gana comisiones de sus propios miembros. Puede aprobar/rechazar miembros pendientes, inactivar activos y reactivar inactivos; el rechazo definitivo (`REJECTED`) es exclusivo del Admin de Plataforma.
- La referencia de versiÃ³n financiera estable es el tag `v0.1-admin-saldos` (ledger confiable desde ese punto).
- El sistema usa **contabilidad de doble entrada**: el Admin de Plataforma debe registrar ingresos externos (`register_platform_income`) para tener saldo y poder aprobar recargas. PROHIBIDO crear saldo sin origen contable.
- Las tablas `admin_allies` y `admin_couriers` tienen su propio campo `status` que debe mantenerse sincronizado con `allies.status` / `couriers.status`. Los helpers `_sync_ally_link_status` y `_sync_courier_link_status` en `db.py` garantizan esta sincronÃ­a automÃ¡ticamente en cada actualizaciÃ³n de estado.

---

## Agendas del Admin (IMPLEMENTADO 2026-03-07)

El Admin Local y el Admin de Plataforma tienen dos agendas propias:

1. **Agenda de clientes de entrega** (`admin_customers` + `admin_customer_addresses`): registrar clientes recurrentes que solicitan domicilios, con sus datos de entrega. Espejo exacto de la agenda `ally_customers`.
2. **Mis Direcciones** (`admin_locations`): gestiÃ³n CRUD completa de los puntos de recogida del admin. Antes solo se podÃ­an agregar durante el pedido; ahora tiene UI de gestiÃ³n independiente.

### Flujo `admin_clientes_conv`

Entry: callback `admin_mis_clientes` (botÃ³n en menÃº admin)

| Estado | Constante | DescripciÃ³n |
|--------|-----------|-------------|
| `ADMIN_CUST_MENU` | 925 | MenÃº principal |
| `ADMIN_CUST_NUEVO_NOMBRE` | 926 | Nombre del nuevo cliente |
| `ADMIN_CUST_NUEVO_TELEFONO` | 927 | TelÃ©fono del nuevo cliente |
| `ADMIN_CUST_NUEVO_NOTAS` | 928 | Notas internas del cliente |
| `ADMIN_CUST_NUEVO_DIR_LABEL` | 929 | Etiqueta de la primera direcciÃ³n |
| `ADMIN_CUST_NUEVO_DIR_TEXT` | 930 | DirecciÃ³n (con geocoding) |
| `ADMIN_CUST_BUSCAR` | 931 | BÃºsqueda por nombre/telÃ©fono |
| `ADMIN_CUST_VER` | 932 | Detalle del cliente |
| `ADMIN_CUST_EDITAR_NOMBRE` | 933 | Editar nombre |
| `ADMIN_CUST_EDITAR_TELEFONO` | 934 | Editar telÃ©fono |
| `ADMIN_CUST_EDITAR_NOTAS` | 935 | Editar notas |
| `ADMIN_CUST_DIR_NUEVA_LABEL` | 936 | Etiqueta de nueva direcciÃ³n |
| `ADMIN_CUST_DIR_NUEVA_TEXT` | 937 | Nueva direcciÃ³n (geocoding) |
| `ADMIN_CUST_DIR_EDITAR_LABEL` | 938 | Editar etiqueta de direcciÃ³n |
| `ADMIN_CUST_DIR_EDITAR_TEXT` | 939 | Editar direcciÃ³n |
| `ADMIN_CUST_DIR_EDITAR_NOTA` | 940 | Editar nota de entrega |
| `ADMIN_CUST_DIR_CIUDAD` | 941 | Ciudad de la direcciÃ³n |
| `ADMIN_CUST_DIR_BARRIO` | 942 | Barrio (punto de persistencia) |
| `ADMIN_CUST_DIR_CORREGIR` | 943 | Corregir/agregar coordenadas |

**Prefijo callbacks**: `acust_`
**Prefijo user_data**: `acust_`
**Funciones DB**: `create_admin_customer`, `list_admin_customers`, `search_admin_customers`, `update_admin_customer`, `archive_admin_customer`, `restore_admin_customer`, `get_admin_customer_by_id`, `create_admin_customer_address`, `list_admin_customer_addresses`, `update_admin_customer_address`, `archive_admin_customer_address`, `get_admin_customer_address_by_id`

### Flujo `admin_dirs_conv`

Entry: callback `admin_mis_dirs` (botÃ³n en menÃº admin)

| Estado | Constante | DescripciÃ³n |
|--------|-----------|-------------|
| `ADMIN_DIRS_MENU` | 945 | Lista de ubicaciones de recogida |
| `ADMIN_DIRS_NUEVA_LABEL` | 946 | Nombre del lugar (etiqueta) |
| `ADMIN_DIRS_NUEVA_TEXT` | 947 | DirecciÃ³n (con geocoding) |
| `ADMIN_DIRS_NUEVA_TEL` | 948 | TelÃ©fono del punto (opcional) |
| `ADMIN_DIRS_VER` | 949 | Detalle de una ubicaciÃ³n |

**Prefijo callbacks**: `adirs_`
**Prefijo user_data**: `adirs_`
**Funciones DB**: `get_admin_locations`, `get_admin_location_by_id`, `create_admin_location`, `update_admin_location`, `archive_admin_location`

### IntegraciÃ³n en `admin_pedido_conv`

Al avanzar al paso `ADMIN_PEDIDO_CUST_NAME`, se muestra un botÃ³n "Seleccionar de mis clientes". El admin puede:
- Escribir el nombre directamente (flujo manual existente)
- Seleccionar de su agenda â†’ ver sus direcciones guardadas â†’ seleccionar una (salta a `ADMIN_PEDIDO_TARIFA`) o ingresar nueva (va a `ADMIN_PEDIDO_CUST_ADDR`)

| Estado | Constante | DescripciÃ³n |
|--------|-----------|-------------|
| `ADMIN_PEDIDO_SEL_CUST` | 917 | Lista de clientes para seleccionar |
| `ADMIN_PEDIDO_SEL_CUST_ADDR` | 918 | Seleccionar direcciÃ³n del cliente |

**Callbacks nuevos en `admin_pedido_conv`**:
- `admin_pedido_sel_cust` â†’ `admin_pedido_sel_cust_handler`
- `acust_pedido_sel_{id}` â†’ `admin_pedido_cust_selected`
- `acust_pedido_addr_{id}` â†’ `admin_pedido_addr_selected`
- `acust_pedido_addr_nueva` â†’ `admin_pedido_addr_nueva`

---

## Flujo de Entrega con ValidaciÃ³n GPS (IMPLEMENTADO 2026-03-12)

### Nuevo ciclo de entrega

```
Aliado confirma llegada del courier al pickup
  â†’ courier recibe botÃ³n "Confirmar recogida" (sin GPS requerido)
  â†’ courier confirma â†’ PICKED_UP + datos del cliente revelados + jobs T+30/T+60

Courier intenta finalizar el servicio:
  â†’ GPS inactivo (con pedido activo) â†’ BLOQUEADO â€” instrucciones para reactivar
  â†’ GPS activo + courier a â‰¤100m de dropoff_lat/lng â†’ confirmaciÃ³n normal
  â†’ GPS activo + courier a >100m â†’ explicaciÃ³n + botÃ³n "Estoy aquÃ­ pero el pin estÃ¡ mal"
```

**Aplica igual a rutas multi-parada**: cada parada valida GPS + distancia a `route_destinations.dropoff_lat/lng`.

### Constantes en `order_delivery.py`

| Constante | Valor | DescripciÃ³n |
|-----------|-------|-------------|
| `DELIVERY_RADIUS_KM` | 0.1 (100 m) | Radio mÃ¡ximo para finalizar entrega |
| `DELIVERY_REMINDER_SECONDS` | 1800 (30 min) | Job recordatorio al courier en PICKED_UP |
| `DELIVERY_ADMIN_ALERT_SECONDS` | 3600 (60 min) | Job alerta al admin si courier no finaliza |
| `GPS_INACTIVE_MSG` | (constante texto) | Mensaje estÃ¡ndar cuando GPS estÃ¡ inactivo |

### Helper GPS

```python
_is_courier_gps_active(courier) â†’ bool
# Retorna True si live_location_active == 1 y live_lat/live_lng no son None
```

### GPS bloqueante (con servicio activo)

- `mi_repartidor()` en `main.py`: si el courier tiene pedido o ruta activa (`ACCEPTED`/`PICKED_UP`) y GPS inactivo â†’ muestra aviso con instrucciones antes del menÃº.
- Las funciones `_handle_delivered_confirm`, `_handle_pin_issue_report`, `_handle_route_deliver_stop`, `_handle_route_pin_issue` tambiÃ©n verifican GPS y bloquean si estÃ¡ inactivo.
- **NO aplica** cuando el courier no tiene servicios activos.

---

## Flujo de Soporte por Pin Mal Ubicado (IMPLEMENTADO 2026-03-12)

### Flujo completo â€” Pedido normal

```
Courier reporta "Estoy aquÃ­ pero el pin estÃ¡ mal" (order_pinissue_{id})
  â†’ Crea order_support_requests (idempotente: no crea duplicados)
  â†’ Notifica al admin del equipo en Telegram:
      - Datos del pedido y cliente
      - Link Google Maps al pin de entrega guardado (dropoff_lat/lng)
      - Link Google Maps a ubicaciÃ³n actual del courier (live_lat/lng)
      - Link Telegram directo al courier (para chat)
      - Botones: Finalizar / Cancelar falla courier / Cancelar falla aliado
  â†’ Courier: "Solicitud enviada. Permanece en el lugar."

Admin toca Finalizar:
  â†’ resolve_support_request(DELIVERED) + apply_service_fee(ALLY) + apply_service_fee(COURIER)
  â†’ set_order_status(DELIVERED)
  â†’ Courier notificado: "Admin finalizÃ³ el servicio"

Admin toca Cancelar falla courier:
  â†’ resolve_support_request(CANCELLED_COURIER) + apply_service_fee(COURIER solo)
  â†’ cancel_order(ADMIN)
  â†’ Courier notificado: "Pedido cancelado. Falla atribuida a ti. Devuelve el producto."

Admin toca Cancelar falla aliado:
  â†’ resolve_support_request(CANCELLED_ALLY) + apply_service_fee(ALLY) + apply_service_fee(COURIER)
  â†’ cancel_order(ADMIN)
  â†’ Courier notificado: "Pedido cancelado. Falla del aliado. Devuelve el producto."
```

### Flujo completo â€” Ruta multi-parada

```
Courier reporta pin malo en parada (ruta_pinissue_{route_id}_{seq})
  â†’ Misma lÃ³gica de notificaciÃ³n al admin, con datos de la parada
  â†’ Admin puede: Finalizar parada / Cancelar parada (courier) / Cancelar parada (aliado)
  â†’ Al resolver: courier continÃºa con las demÃ¡s paradas pendientes
  â†’ Al finalizar la ruta: si hay paradas canceladas â†’ resumen de devoluciones al courier
```

### Tabla de fees por resoluciÃ³n

| AcciÃ³n admin | Aliado | Courier | Estado orden |
|---|:---:|:---:|---|
| Finalizar | $300 | $300 | DELIVERED |
| Cancelar falla courier | $0 | $300 | CANCELLED |
| Cancelar falla aliado | $300 | $300 | CANCELLED |

### Funciones nuevas en `order_delivery.py`

| FunciÃ³n | DescripciÃ³n |
|---------|-------------|
| `_notify_courier_awaiting_pickup_confirm(context, order)` | EnvÃ­a botÃ³n "Confirmar recogida" al courier tras aprobaciÃ³n del aliado |
| `_handle_confirm_pickup(update, context, order_id)` | Courier confirma recogida â†’ PICKED_UP + revela datos |
| `_handle_delivered_confirm(update, context, order_id)` | Valida GPS + distancia antes de la confirmaciÃ³n de entrega |
| `_handle_pin_issue_report(update, context, order_id)` | Courier reporta pin malo; crea solicitud y notifica admin |
| `_notify_admin_pin_issue(context, order, courier, admin_id, support_id)` | EnvÃ­a alerta al admin con datos y botones |
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

| FunciÃ³n | DescripciÃ³n |
|---------|-------------|
| `create_order_support_request(courier_id, admin_id, order_id, route_id, route_seq)` | Crea solicitud; retorna id generado |
| `get_pending_support_request(order_id, route_id, route_seq)` | Retorna solicitud PENDING del pedido o parada |
| `resolve_support_request(support_id, resolution, resolved_by)` | Marca como RESOLVED; retorna bool |
| `cancel_route_stop(route_id, seq, resolution)` | Marca parada con CANCELLED_COURIER o CANCELLED_ALLY |
| `get_all_pending_support_requests()` | Lista todos los PENDING con datos de courier y pedido (para panel web) |
| `get_support_request_full(support_id)` | Retorna solicitud con todos los datos JOIN para el panel web |

Todas re-exportadas en `services.py`.

### Panel web â€” Solicitudes de ayuda (`/superadmin/soporte`)

El panel web del Platform Admin expone:

| Endpoint | DescripciÃ³n |
|----------|-------------|
| `GET /admin/support-requests` | Lista todas las solicitudes (PENDING y recientes RESOLVED) |
| `GET /admin/support-requests/{id}` | Detalle completo con datos de courier, pedido, mapas |
| `POST /admin/support-requests/{id}/resolve` | Resuelve la solicitud (mismo modelo de fees que el bot) |

El componente Angular (`SoporteComponent`) muestra:
- Tabla de solicitudes con estado y datos del courier
- Panel de detalle con link al pin de entrega y ubicaciÃ³n del courier (Google Maps)
- Link Telegram directo al courier para comunicaciÃ³n
- Botones de acciÃ³n: Finalizar / Cancelar falla courier / Cancelar falla aliado
- **Nota:** la resoluciÃ³n desde el panel web aplica los fees en BD pero NO envÃ­a notificaciones Telegram al courier (el courier solo recibe notificaciÃ³n cuando el admin actÃºa desde el bot).

---

*Ãšltima actualizaciÃ³n: 2026-03-12*

