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
- **Admin Local**: administra un equipo de repartidores y aliados en una zona.
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
| `orders` | Pedidos con todo su ciclo de vida |
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
| `order_` | Ofertas y entrega de pedidos |
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

**Antes de agregar un callback nuevo:** `git grep "nuevo_prefijo" -- "*.py"` para verificar que no existe ya.

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

| Prefijo | Uso |
|---------|-----|
| `main` | Producción. **Nunca trabajar directamente aquí.** |
| `claude/` | Ramas de trabajo de agentes IA |
| `verify/` | Ramas para validar cambios estructurales de BD antes de merge a main |
| `luisa-web` | Rama permanente de la colaboradora Luisa. **NUNCA borrar.** |

### Flujo de Trabajo

```bash
# 1. Siempre crear ramas desde origin/main actualizado
git fetch origin
git checkout -b claude/nombre-tarea-ID origin/main

# 2. Verificar rama activa antes de cualquier cambio
git branch --show-current

# 3. Antes de merge a main, verificar compatibilidad estructural
git diff origin/main nombre-rama -- --name-only
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

---

## Cotizador y Uso de APIs (Control de Costos)

El cotizador usa **Google Maps API** (Distance Matrix / Places). Tiene cuota diaria limitada.

### Regla de Cuota
- **PROHIBIDO** llamar a la API sin verificar `api_usage_daily` primero.
- Si `api_usage_daily >= límite`: retornar error informativo, **no llamar** a la API.
- Toda llamada debe incrementar `api_usage_daily` de forma atómica.

### Regla de Caché
- Distancias entre pares de coordenadas **deben cachearse** en base de datos.
- **PROHIBIDO** recalcular una distancia ya cacheada para la misma consulta.

### Regla de Geocodificación
- Coordenadas (lat/lng) se capturan vía Telegram (ubicación GPS). La API solo se usa para geocodificación inversa o búsqueda de direcciones escritas.
- **PROHIBIDO** usar la API para validar ubicaciones que ya tienen GPS válido.

### Manejo de Errores de API
- Si la API falla: retornar error claro al usuario. **PROHIBIDO** propagar excepciones sin capturar ni reintentar automáticamente.

---

## Flujo de Trabajo con IA

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
- Un Admin Local debe tener repartidores vinculados (status `APPROVED` en `admin_couriers`) para que su equipo funcione correctamente.
- La referencia de versión financiera estable es el tag `v0.1-admin-saldos` (ledger confiable desde ese punto).

---

*Última actualización: 2026-02-22*
