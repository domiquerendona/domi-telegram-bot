# DOCUMENTO HISTÓRICO
#
# Este archivo describe el estado del sistema en una auditoría pasada.
# No debe usarse como fuente normativa del proyecto.

# Alineacion codigo vs documentacion

Fecha base: 2026-03-12
Rama verificada: staging
Objetivo: fijar la realidad actual del codigo antes de refactorizar.

## 1. Estado real del cobro de comision al courier

Conclusion: el cobro al courier no falta. Ya existe implementado por rutas operativas distintas al TODO historico que habia en `Backend/services.py`.

Evidencia principal:

- Entrega normal de pedido: `apply_service_fee(target_type="COURIER", ...)` en [Backend/order_delivery.py](../Backend/order_delivery.py) funcion `_handle_delivered`.
- Resolucion admin de soporte/pin mal ubicado en bot: cobro al courier en [Backend/order_delivery.py](../Backend/order_delivery.py).
- Resolucion de soporte desde panel web: cobro al courier en [Backend/web/api/admin.py](../Backend/web/api/admin.py) endpoint `resolve_support_request_endpoint`.
- Implementacion central del fee: [Backend/services.py](../Backend/services.py) funcion `apply_service_fee`.

Veredicto operativo:

- No clasificar esta capacidad como "faltante".
- El TODO anterior en `Backend/services.py` era enganoso y quedo reemplazado por una nota de alineacion.

## 2. Inventario oficial de callback_data reales

Prefijos detectados hoy en codigo:

- `acust` -> `Backend/main.py`
- `adirs` -> `Backend/main.py`
- `admin` -> `Backend/main.py`, `Backend/order_delivery.py`, `Backend/profile_changes.py`
- `admpedidos` -> `Backend/main.py`, `Backend/order_delivery.py`
- `agenda` -> `Backend/main.py`
- `ally` -> `Backend/main.py`
- `allycust` -> `Backend/main.py`
- `chgreq` -> `Backend/main.py`, `Backend/profile_changes.py`
- `config` -> `Backend/main.py`
- `cotizar` -> `Backend/main.py`
- `courier` -> `Backend/main.py`
- `cust` -> `Backend/main.py`
- `dir` -> `Backend/main.py`
- `guardar` -> `Backend/main.py`
- `ingreso` -> `Backend/main.py`
- `local` -> `Backend/main.py`
- `menu` -> `Backend/main.py`
- `offer` -> `Backend/main.py`, `Backend/order_delivery.py`
- `order` -> `Backend/main.py`, `Backend/order_delivery.py`
- `pagos` -> `Backend/main.py`
- `pedido` -> `Backend/main.py`, `Backend/order_delivery.py`
- `perfil` -> `Backend/main.py`, `Backend/profile_changes.py`
- `pickup` -> `Backend/main.py`
- `plat` -> `Backend/main.py`
- `preview` -> `Backend/main.py`
- `pricing` -> `Backend/main.py`
- `rating` -> `Backend/main.py`, `Backend/order_delivery.py`
- `recargar` -> `Backend/main.py`
- `recharge` -> `Backend/main.py`
- `ref` -> `Backend/main.py`
- `ruta` -> `Backend/main.py`, `Backend/order_delivery.py`
- `solequipo` -> `Backend/main.py`
- `terms` -> `Backend/main.py`
- `ubicacion` -> `Backend/main.py`

Notas de alineacion:

- Este inventario describe la realidad actual del codigo, no el ideal arquitectonico.
- Hay prefijos en uso no documentados hoy en `AGENTS.md`: `acust`, `adirs`, `allycust`, `local`, `offer`, `plat`, `rating`, `solequipo`.
- Los callbacks historicos `ally_team:{team_code}` y `courier_team:{team_code}` quedaron deprecados; desde 3B se emiten como `ally_team_{team_code}` y `courier_team_{team_code}`, con compatibilidad temporal para ambos formatos.
- Conviven `recargar_` y `recharge_` para el mismo dominio funcional de recargas.
- Inventario definitivo, clasificacion y propuesta de gobernanza: ver [docs/callback_governance_2026-03-12.md](callback_governance_2026-03-12.md).

## 3. Mapa oficial de accesos directos a BD fuera de db.py

### 3.1. SQL o conexion directa

- `Backend/main.py`
  - Importa desde `db.py`.
  - Abre conexion con `get_connection()`.
  - Ejecuta `SELECT` manual para obtener `telegram_id` al notificar aprobaciones.

- `Backend/profile_changes.py`
  - Importa desde `db.py`.
  - Abre conexion con `get_connection()`.
  - Ejecuta `UPDATE` e `INSERT` directos sobre `admins`, `couriers`, `allies` y `ally_locations`.

- `Backend/services.py`
  - Usa SQL directo para flujos criticos de recargas/idempotencia.
  - Este acceso hoy es estructural, no accidental.

- `Backend/web/api/admin.py`
  - Importa desde `db.py`.
  - Abre conexion con `get_connection()`.
  - Ejecuta SQL directo para saldos, reportes, cancelacion de pedidos y lectura/escritura de settings.
  - Desde el commit `1896e3d` tambien expone resolucion de solicitudes de soporte desde panel web.

- `Backend/web/api/dashboard.py`
  - Importa desde `db.py`.
  - Abre conexion con `get_connection()`.
  - Ejecuta `SELECT COUNT` y `SUM` directos para estadisticas del panel.

### 3.2. Dependencia directa de db.py sin SQL inline local

- `Backend/order_delivery.py`
  - Importa masivamente funciones desde `db.py`.
  - Hace import lazy de `_row_value`.
  - No concentra `cur.execute(...)` visible en este archivo, pero sigue acoplado directamente a `db.py`.

### 3.3. Sin acceso directo a BD detectado en esta revision

- `Backend/web/api/users.py`
- `Backend/web/auth/dependencies.py`
- `Backend/web/admin/services.py`
- `Backend/web/users/repository.py`

Nota:

- `Backend/web/users/repository.py` no toca BD, pero sigue siendo un mock en memoria.

## 4. Conclusion de fase

Antes de refactorizar, la realidad fijada es esta:

- El cobro al courier existe y esta activo.
- La documentacion de callbacks esta incompleta respecto al codigo real.
- Siguen existiendo multiples accesos directos a BD fuera de `db.py`.
- El panel web reciente amplia esa superficie; no la reduce.

## 5. Actualizacion posterior a fases 2A-2D y 3A

Estado posterior verificado:

- `Backend/web/api/admin.py`, `Backend/web/api/dashboard.py` y `Backend/profile_changes.py` ya no concentran SQL inline ni `get_connection()` local.
- Los accesos puntuales inventariados en `Backend/main.py` para notificaciones de aprobacion tambien ya fueron extraidos.
- La brecha principal que sigue abierta en callbacks ya no es de inventario, sino de gobernanza:
  - prefijos reales no documentados en `AGENTS.md`
  - dos excepciones activas con `:`
  - duplicidad funcional `recargar_` vs `recharge_`

Referencia operativa actualizada:

- [docs/callback_governance_2026-03-12.md](callback_governance_2026-03-12.md)

## 6. Entry points separados

Estado actual posterior a la separacion minima bot/web:

- `Backend/main.py` -> arranque del bot Telegram (`main()` y wiring del dispatcher).
- `Backend/web_app.py` -> bootstrap web/FastAPI (`app`, routers, CORS y endpoint `/`).

Objetivo de este corte:

- Reducir mezcla conceptual en `Backend/main.py` sin abrir una reestructuracion mayor del bot.
- Mantener las mismas rutas web y el mismo comportamiento observable del bot.
