# CLAUDE.md — Guía para AI Assistants en Domiquerendona

Este archivo describe la estructura del proyecto, flujos de trabajo y convenciones técnicas que todos los asistentes de IA deben seguir. Es un complemento operativo a `AGENTS.md`, que define las reglas obligatorias.

> **IMPORTANTE:** Las reglas de `AGENTS.md` tienen prioridad absoluta. Este documento explica el "qué" y el "cómo" del sistema; `AGENTS.md` define el "no harás".

---

## Visión General del Proyecto

**Domiquerendona** es una plataforma de domicilios (delivery) que opera en Colombia. El sistema consta de:

1. **Bot de Telegram** (Backend/): bot conversacional que gestiona pedidos, registros y operaciones de todos los actores del sistema.
2. **API Web** (Backend/web/): API REST con FastAPI que expone endpoints para el panel administrativo.
3. **Panel Web** (Frontend/): aplicación Angular 21 con SSR para el superadministrador.

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
│   ├── main.py                   # Orquestador: handlers, wiring, UI
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
│   ├── TESTING.md                # Guía de testing manual y automatizado
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
│   ├── HITOS.md                  # Hitos y versiones del proyecto
│   └── reglas_operativas.md      # Matriz de estados y botones UI
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
main.py  ──importa──►  services.py  ──importa──►  db.py
    │                       │                        │
    │  (handlers, wiring,   │  (lógica de negocio,  │  (SQL, queries,
    │   UI, estado de flujo) │   re-exports de db)   │   conexiones)
    │                       │                        │
    └── order_delivery.py ──┘                        │
    └── profile_changes.py ─────────────────────────►┘
```

### `db.py` — Capa de Datos
- **Único responsable** de toda interacción con la base de datos.
- Detecta motor en tiempo de arranque: `DATABASE_URL` presente → PostgreSQL; ausente → SQLite.
- Usa el placeholder global `P` (`%s` para Postgres, `?` para SQLite) en todas las queries.
- Usa `get_connection()` para todas las conexiones. **PROHIBIDO** `sqlite3.connect()` directo.
- Helpers multi-motor: `_insert_returning_id()`, `_row_value()`.

### `services.py` — Capa de Negocio
- Contiene toda la lógica de negocio que no es específica de un módulo grande.
- Importa desde `db.py` y re-exporta funciones para que `main.py` no acceda a `db.py` directamente.
- El bloque de re-exports está marcado con el comentario: `# Re-exports para que main.py no acceda a db directamente`.
- Si `main.py` necesita una función de `db.py` que aún no está en `services.py`: agregarla al bloque de re-exports, luego importarla en `main.py` desde `services.py`. **PROHIBIDO** importarla directamente desde `db.py`.

### `main.py` — Orquestador
- Solo contiene: registro de handlers, funciones handler (validar → llamar services → retornar estado), helpers de UI, gestión de estado de flujo, constantes de UI.
- **PROHIBIDO** en `main.py`: llamadas directas a `db.py`, validaciones de rol, lectores de configuración de BD, lógica condicional basada en datos persistidos.
- **Excepciones permitidas** en `main.py` (solo estas 3):
  ```python
  from db import init_db
  from db import force_platform_admin
  from db import ensure_pricing_defaults
  ```

### Módulos Especializados
- **`order_delivery.py`**: flujo completo de publicación, ofertas y entrega de pedidos.
- **`profile_changes.py`**: flujo de solicitudes de cambio de perfil de usuarios.

### Regla Anti-Importación Circular

Si un módulo secundario (`profile_changes.py`, `order_delivery.py`, etc.) necesita una función de `main.py`:
- **PROHIBIDO** importar desde `main` en el encabezado del módulo.
- **Solución**: mover la función a `services.py` y que ambos importen desde `services.py`.
- Solo se permite el import lazy (dentro del cuerpo de la función) si la dependencia circular está confirmada y es inevitable. En ese caso, documentar el motivo con un comentario inline.

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

- No destructivas, idempotentes, compatibles con datos existentes.
- **PROHIBIDO**: `DROP TABLE`, `TRUNCATE`, migraciones que borren datos en producción.
- Toda migración debe verificar existencia antes de agregar columnas (con `information_schema` en Postgres, `PRAGMA table_info` en SQLite).
- Cambios estructurales de BD **deben implementarse en ramas `verify/*`** y validarse antes de merge a `main`.

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
| `orders` | Pedidos con todo su ciclo de vida. Columnas de tracking: `courier_arrived_at` (timestamp GPS), `courier_accepted_lat/lng` (posición al aceptar, base T+5) |
| `recharge_requests` | Solicitudes de recarga de saldo |
| `ledger` | Libro contable de todas las transacciones |
| `settings` | Configuración del sistema (clave-valor) |
| `profile_change_requests` | Solicitudes de cambio de perfil |

---

## Flujos de Conversación (Bot de Telegram)

### Convenciones de Estado (`context.user_data`)

Cada flujo usa prefijos exclusivos en sus claves. **PROHIBIDO** compartir claves entre flujos:

| Flujo | Prefijos de claves |
|-------|-------------------|
| Registro aliado | `ally_phone`, `ally_name`, `ally_owner`, `ally_document`, `city`, `barrio`, `address`, `ally_lat`, `ally_lng` |
| Registro repartidor | `phone`, `courier_fullname`, `courier_idnumber`, `city`, `barrio`, `residence_address`, `courier_lat`, `courier_lng` |
| Registro admin | `phone`, `admin_city`, `admin_barrio`, `admin_residence_address`, `admin_lat`, `admin_lng` |
| Pedido | `pickup_*`, `customer_*`, `instructions`, `requires_cash`, `cash_required_amount` |
| Recarga | `recargar_target_type`, `recargar_target_id`, `recargar_admin_id` |
| Ingreso externo (plataforma) | `ingreso_monto`, `ingreso_metodo` |

### Convención de `callback_data`

Formato: `{dominio}_{accion}` o `{dominio}_{accion}_{id}`

Separador: siempre guion bajo (`_`). **PROHIBIDO** guion, punto o slash.

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
| `cust_` | Acciones de cliente |
| `dir_` | Gestión de direcciones de recogida |
| `guardar_` | Guardar dirección de cliente |
| `menu_` | Navegación de menú |
| `order_` | Ofertas y entrega de pedidos. Incluye: `order_find_another_{id}` (aliado busca otro courier), `order_call_courier_{id}` (aliado ve teléfono del courier), `order_wait_courier_{id}` (aliado sigue esperando), `order_delivered_confirm_{id}` / `order_delivered_cancel_{id}` (confirmación de entrega en courier), `order_release_reason_{id}_{reason}` / `order_release_confirm_{id}_{reason}` / `order_release_abort_{id}` (liberación responsable con motivo) |
| `pagos_` | Sistema de pagos |
| `pedido_` | Flujo de creación de pedidos |
| `perfil_` | Cambios de perfil |
| `pickup_` | Selección de punto de recogida |
| `preview_` | Previsualización de pedido |
| `pricing_` | Configuración de tarifas |
| `recargar_` | Sistema de recargas |
| `ref_` | Validación de referencias |
| `terms_` | Aceptación de términos y condiciones |
| `ubicacion_` | Selección de ubicación GPS |
| `ingreso_` | Registro de ingreso externo del Admin de Plataforma |

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
| `ENV` | `LOCAL` o `PROD` | Siempre |
| `BOT_TOKEN` | Token del bot de Telegram | Siempre |
| `ADMIN_USER_ID` | Telegram ID del admin de plataforma | Siempre |
| `COURIER_CHAT_ID` | ID del grupo de repartidores en Telegram | PROD |
| `RESTAURANT_CHAT_ID` | ID del grupo de aliados en Telegram | PROD |
| `DB_PATH` | Ruta del archivo SQLite | LOCAL |
| `DATABASE_URL` | URL de conexión PostgreSQL | PROD |

**Regla de oro:** NUNCA usar el mismo `BOT_TOKEN` en DEV y PROD simultáneamente.

En PROD: si `DATABASE_URL` no está presente, el sistema debe lanzar error fatal y no arrancar.

---

## Desarrollo Local

### Backend (Bot + API)

```bash
cd Backend/

# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env con: ENV=LOCAL, BOT_TOKEN=<token_dev>, ADMIN_USER_ID=<tu_id>

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el bot
python main.py

# Logs esperados:
# [ENV] Ambiente: LOCAL - .env cargado
# [BOT] TOKEN fingerprint: hash=... suffix=...
# [BOOT] Iniciando polling...
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

### Railway (PROD)

- **Motor**: `worker: python3 main.py` (Procfile)
- **Variables**: configurar en el dashboard de Railway (sin `.env`)
- **Base de datos**: PostgreSQL con `DATABASE_URL`
- **Rama de producción**: `main`

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
uvicorn main:app --reload --port 8000
```

Endpoints principales:
- `GET /` — Health check HTML
- `POST /admin/users/{user_id}/approve` — Aprobar usuario (requiere rol admin)
- Endpoints de `/users/` y `/dashboard/`

CORS configurado para permitir `http://localhost:4200` en desarrollo.

---

## Git y Ramas

### Estructura de Ramas

| Rama/Prefijo | Tipo | Uso |
|---|---|---|
| `main` | Permanente | Producción (Railway PROD). **Nunca trabajar directamente aquí.** |
| `staging` | Permanente | **Rama de trabajo e integración.** Aquí se desarrolla, se hace commit y se hace push. **Nunca borrar.** |
| `claude/` | Temporal | Opcional. Solo si se necesita aislar experimentos; luego se mergea a staging. |
| `verify/` | Temporal | **Obligatoria** para cambios estructurales de BD; luego se mergea a staging. |
| `luisa-web` | Permanente | Rama de la colaboradora Luisa. **NUNCA borrar.** |

### Flujo de Trabajo

```
staging   ──(validado)──►  main
verify/*  ──merge──►  staging  ──(validado)──►  main
                        (entorno DEV:
                         BOT_TOKEN DEV
                         DATABASE_URL separada)
```

```bash
# 1. Trabajar SIEMPRE en staging
git checkout staging
git pull --ff-only origin staging

# 2. Implementar cambios, validar, commit y push
python -m py_compile Backend/main.py Backend/services.py Backend/db.py Backend/order_delivery.py Backend/profile_changes.py
git add -A
git commit -m "feat: descripción"
git push origin staging

# 3. Validar funcionalmente en staging

# 4. Solo cuando esté validado, mergear staging a main
# (Proceso de release según políticas del equipo)
```

### Verificación de Compatibilidad Estructural (Obligatorio Antes de Merge)

**PROHIBIDO** hacer merge si la rama tiene paths de archivos incompatibles con `main`.

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

**Reglas absolutas:**
- **PROHIBIDO** eximir al Admin de Plataforma de la verificación de saldo.
- **PROHIBIDO** aprobar una recarga si `admins.balance < amount`, sin importar el rol del admin.
- **PROHIBIDO** modificar cualquier balance sin registro simultáneo en ledger.

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
- Aliado crea pedido → fee al aliado → comisión va al **admin del aliado**.
- Courier acepta pedido → fee al courier → comisión va al **admin del courier**.
- Cada admin gana solo de sus propios miembros, sin importar con quién interactúan.

**Flujo técnico post-implementación:**
```
Aliado (Admin A) crea pedido
  → publish_order_to_couriers(admin_id=A)
  → check_service_fee_available(ALLY, ally_id, admin_id=A)   # A debe tener saldo
  → get_eligible_couriers_for_order(ally_id=X)               # Sin filtro → TODOS los couriers activos
  → Para cada courier: get_approved_admin_id_for_courier(courier_id) → courier_admin_id
    → check_service_fee_available(COURIER, courier_id, courier_admin_id)
    → Solo pasan couriers con saldo en su propio admin

Courier (Admin B) acepta
  → courier_admin_id_snapshot = B (guardado en orders al aceptar)

Courier entrega
  → apply_service_fee(ALLY, ally_id, admin_id=A)              → Admin A cobra comisión
  → apply_service_fee(COURIER, courier_id, admin_id=B)        → Admin B cobra comisión
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
Las reglas completas están en AGENTS.md Sección 15. Aquí el resumen operativo:

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

> Si `git log HEAD..origin/staging` muestra commits del otro agente en los mismos archivos
> que tocaste: **PROHIBIDO pushear**. Reportar a Luis Felipe y esperar instruccion.
> **PROHIBIDO `git push --force`** en cualquier circunstancia.

#### Prefijo obligatorio en commits

| Agente | Formato |
|--------|---------|
| Claude Code | `[claude] feat: descripción` |
| Codex | `[codex] feat: descripción` |

Para filtrar por agente: `git log --oneline --grep="[claude]"`

#### Reglas de no-interferencia

- **PROHIBIDO** modificar o revertir trabajo del otro agente sin autorización de Luis Felipe.
- Si se detecta un error del otro agente: reportar a Luis Felipe (archivo, función, commit) y **esperar instrucción**.
- Si se detecta solapamiento en WORKLOG.md o `git log`: **pausar** y notificar a Luis Felipe.
- Si `git push` es rechazado por fast-forward: **PROHIBIDO** `--force`. Hacer pull, revisar, reportar.

#### Archivos de alto riesgo

Verificar WORKLOG.md y `git log --follow -5 <archivo>` antes de editar cualquiera de estos:
`Backend/main.py` · `Backend/services.py` · `Backend/db.py` · `Backend/order_delivery.py` · `AGENTS.md` · `CLAUDE.md`

La coordinación entre agentes pasa **siempre** por Luis Felipe.

Estas reglas aplican a cualquier agente que trabaje en este repositorio.

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

*Última actualización: 2026-03-03*
