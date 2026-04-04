# Gobernanza de callback_data

Fecha base: 2026-03-12
Rama verificada: staging
Objetivo: alinear documentacion operativa con la realidad actual del codigo, sin migracion masiva todavia.

## 1. Criterio de clasificacion

- `Documentado`: el prefijo ya existe en `AGENTS.md`.
- `No documentado`: existe en codigo, pero no en `AGENTS.md`.
- `Fuera de estandar`: usa separador distinto de `_` o formato no cubierto por la regla oficial.
- `Duplicado`: cubre el mismo dominio funcional que otro prefijo activo.

Decision operativa:

- `Mantener tal como esta`: no requiere cambio ni migracion.
- `Documentar tal como esta`: agregarlo al estandar operativo y mantenerlo.
- `Deprecar`: no crear nuevos callbacks con ese prefijo; conservar compatibilidad actual.
- `Migrar despues`: requiere Fase 3B, pero no se toca en esta fase.

## 2. Inventario definitivo por prefijo

| Prefijo | Formato real observado | Archivo consumidor | Handler o zona donde se interpreta | Estado | Decision |
|---|---|---|---|---|---|
| `acust_` | `acust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_{id}|restaurar_{id}|dirs|editar|dir_ver_{id}|...)` | `Backend/main.py` | `admin_clientes_*` | No documentado | Documentar tal como esta |
| `adirs_` | `adirs_(nueva|volver_menu|cerrar|ver_{id}|archivar_{id}|editar_{id})` | `Backend/main.py` | `admin_dirs_*` | No documentado | Documentar tal como esta |
| `admin_` | `admin_*`, `admin_pinissue_*`, `admin_ruta_pinissue_*`, `admin_support_(open|list_{offset}|view_{support_id}_{offset})` | `Backend/main.py`, `Backend/order_delivery.py`, `Backend/profile_changes.py`, `Backend/handlers/admin_panel.py` | `admin_menu_callback`, `order_courier_callback`, `handle_route_callback` | Documentado, pero muy amplio | Mantener tal como esta |
| `admpedidos_` | `admpedidos_(list|detail|cancel|cancel_confirm|cancel_abort|stats|statsdetail)_...` | `Backend/main.py`, `Backend/order_delivery.py` | `admin_orders_callback` | Documentado | Mantener tal como esta |
| `agenda_` | `agenda_(pickups|clientes|cerrar|volver|pickup_...)` | `Backend/main.py` | `agenda_menu_callback`, `agenda_pickups_*` | Documentado | Mantener tal como esta |
| `ally_` | `ally_(approve|reject)_{id}`, `ally_block_(block|unblock)_{id}` | `Backend/main.py` | `ally_approval_callback`, `ally_block_callback` | Documentado | Mantener tal como esta |
| `ally_team` | Estandar nuevo: `ally_team_{team_code}`. Legacy soportado: `ally_team:{team_code}` | `Backend/main.py` | `ally_team_callback` | Fuera de estandar legacy; compatibilidad dual activa | Migrar despues |
| `allycust_` | `allycust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_{id}|restaurar_{id}|dirs|editar|dir_ver_{id}|...)` | `Backend/main.py` | `ally_clientes_*` | No documentado | Documentar tal como esta |
| `chgreq_` | `chgreq_(view|approve|reject)_{id}` | `Backend/main.py`, `Backend/profile_changes.py` | `admin_change_requests_callback` | Documentado | Mantener tal como esta |
| `config_` | `config_(ver_ally|ver_courier|ally_enable|ally_disable|courier_enable|courier_disable|...)` | `Backend/main.py` | `admin_config_callback` | Documentado | Mantener tal como esta |
| `cotizar_` | `cotizar_(modo|pickup|recogida_geo|entrega_geo|crear_pedido|crear_ruta|cerrar|cust_...)` | `Backend/main.py` | `cotizar_*` y entrada a pedido/ruta | Documentado | Mantener tal como esta |
| `courier_` | `courier_(approve|reject)_{id}`, `courier_(activate|deactivate)`, `courier_earn_*`, `courier_pick_admin_*` | `Backend/main.py` | `courier_approval_callback`, `courier_*` | Documentado | Mantener tal como esta |
| `courier_team` | Estandar nuevo: `courier_team_{team_code}`. Legacy soportado: `courier_team:{team_code}` | `Backend/main.py` | `courier_team_callback` | Fuera de estandar legacy; compatibilidad dual activa | Migrar despues |
| `cust_` | `cust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_{id}|restaurar_{id}|dirs|editar|dir_ver_{id}|geo_(si|no)|...)` | `Backend/main.py` | `clientes_*` | Documentado | Mantener tal como esta |
| `dir_` | `dir_pickup_guardar_*` | `Backend/main.py` | `direcciones_pickup_guardar_callback` | Documentado | Mantener tal como esta |
| `guardar_` | `guardar_dir_cliente_(si|no)` | `Backend/main.py` | `pedido_guardar_cliente_callback` | Documentado | Mantener tal como esta |
| `ingreso_` | `ingreso_(iniciar|metodo_...|cancelar)` | `Backend/main.py` | `ingreso_*` | Documentado | Mantener tal como esta |
| `local_` | `local_(check|status|couriers_pending|courier_approve|courier_block|allies_pending|team_...|recargas_pending)_...` | `Backend/main.py` | `admin_local_callback`, `local_recargas_pending_callback` | No documentado | Documentar tal como esta |
| `menu_` | `menu_*` | `Backend/main.py` | `pendientes_callback` y navegacion principal | Documentado | Mantener tal como esta |
| `offer_` | `offer_inc_{order_id}x{monto}`, `offer_inc_otro_{order_id}` | `Backend/main.py`, `Backend/order_delivery.py` | `offer_suggest_inc_*` | No documentado | Documentar tal como esta |
| `order_` | `order_(accept|reject|busy|pickup|delivered|release|cancel|cancel_confirm|cancel_abort|find_another|find_another_confirm|find_another_abort|wait_courier|call_courier|confirm_pickup|pinissue|pickupconfirm_...)_...` | `Backend/main.py`, `Backend/order_delivery.py` | `order_courier_callback` | Documentado | Mantener tal como esta |
| `pagos_` | `pagos_(agregar|gestionar|cerrar|volver|ver_{id}|toggle_{id}_{flag}|delete_{id})` | `Backend/main.py` | `pagos_callback` | Documentado | Mantener tal como esta |
| `pedido_` | `pedido_(cliente_*|sel_*|instr_*|tipo_*|base_(si|no|20000|50000|100000|200000|otro)|retry_quote|inc_*|confirmar|cancelar|guardar_...)` | `Backend/main.py`, `Backend/order_delivery.py` | flujo de pedido y edicion de incentivo | Documentado | Mantener tal como esta |
| `perfil_` | `perfil_change_*` | `Backend/main.py`, `Backend/profile_changes.py` | `perfil_change_*` | Documentado | Mantener tal como esta |
| `pickup_` | `pickup_(select_*|list_*|geo_*|guardar_*)` | `Backend/main.py` | `pedido_pickup_*` | Documentado | Mantener tal como esta |
| `plat_` | `plat_rec_(menu|pending|history|alerts|notify_{id})` | `Backend/main.py` | `plat_recargas_callback` | No documentado | Documentar tal como esta |
| `preview_` | `preview_*` | `Backend/main.py` | `preview_callback` | Documentado | Mantener tal como esta |
| `pricing_` | `pricing_(menu_*|edit_*|volver|exit)` | `Backend/main.py` | `tarifas_edit_callback` | Documentado | Mantener tal como esta |
| `rating_` | `rating_(star|block|skip)_...` | `Backend/main.py`, `Backend/order_delivery.py` | `handle_rating_callback` | No documentado | Documentar tal como esta |
| `recargar_` | `recargar_(role|admin|cancel)_...` | `Backend/main.py` | `recargar_rol_callback`, `recargar_admin_callback` | Documentado | Mantener tal como esta |
| `recharge_` | `recharge_(approve|reject|proof)_{id}` | `Backend/main.py` | `recharge_callback`, `recharge_proof_callback` | Duplicado funcional de recargas; no documentado | Deprecar |
| `ref_` | `ref_(list|view|approve|reject|setloc)_...` | `Backend/main.py` | `reference_validation_callback` | Documentado | Mantener tal como esta |
| `ruta_` | `ruta_(aceptar|rechazar|ocupado|entregar|liberar|liberar_motivo|liberar_confirmar|liberar_abort|arrival_*|find_another|find_another_confirm|find_another_abort|wait_courier|cancelar_aliado|cancelar_aliado_confirm|cancelar_aliado_abort|pinissue|pickup_*|sel_*|confirmar|cancelar|guardar_clientes_...)` | `Backend/main.py`, `Backend/order_delivery.py` | `handle_route_callback` y flujo de creacion de ruta | Documentado | Mantener tal como esta |
| `solequipo_` | `solequipo_(start|courier_sel_{id}|ally_sel_{id})` | `Backend/main.py` | `solequipo_*` | No documentado | Documentar tal como esta |
| `terms_` | `terms_(accept|decline)_{role}` | `Backend/main.py` | `terms_callback` | Documentado | Mantener tal como esta |
| `ubicacion_` | `ubicacion_copiar_msg_cliente` | `Backend/main.py` | `pedido_ubicacion_copiar_msg_callback` | Documentado | Mantener tal como esta |

## 3. Hallazgos clave

### 3.1. Prefijos reales no contemplados hoy en AGENTS.md

- `acust_`
- `adirs_`
- `allycust_`
- `local_`
- `offer_`
- `plat_`
- `rating_`
- `solequipo_`

### 3.2. Formatos fuera de estandar

- `ally_team:{team_code}` -> deprecado pero soportado temporalmente
- `courier_team:{team_code}` -> deprecado pero soportado temporalmente

Problema:

- El estandar actual exige `_` como separador unico.
- Estos callbacks no son ambiguos hoy, pero si contradicen la regla oficial.

Decision:

- Desde 3B el formato emitido por defecto es `ally_team_{team_code}` y `courier_team_{team_code}`.
- Se mantiene soporte temporal para `ally_team:{team_code}` y `courier_team:{team_code}`.
- No se deben crear nuevos callbacks con `:`.

### 3.3. Duplicidad funcional real

Duplicidad confirmada:

- `recargar_` y `recharge_` conviven para el mismo dominio funcional de recargas.

Lectura operativa:

- `recargar_` gobierna la solicitud.
- `recharge_` gobierna la revision/aprobacion.

Decision:

- No romper compatibilidad hoy.
- Marcar `recharge_` como candidato a deprecacion en 3B si se decide unificar el dominio bajo `recargar_`.

## 4. Estandar operativo corregido para 3A

Hasta nueva migracion explicita, el estandar operativo queda asi:

1. El formato preferido sigue siendo `{dominio}_{accion}` o `{dominio}_{accion}_{id}`.
2. Se aceptan formatos compuestos con mas segmentos cuando el flujo lo necesita, por ejemplo `pedido_inc_{order_id}x{monto}` o `ruta_entregar_{route_id}_{seq}`.
3. Existen dos formatos legacy deprecados que siguen soportados temporalmente:
   - `ally_team:{team_code}`
   - `courier_team:{team_code}`
4. El formato estandar vigente para esos flujos es:
   - `ally_team_{team_code}`
   - `courier_team_{team_code}`
5. No se deben crear nuevos prefijos sin aprobacion explicita del usuario.
6. No se deben crear nuevos callbacks con `:`.
7. Para recargas, el dominio preferido para cambios futuros debe ser `recargar_`; `recharge_` queda congelado.

## 5. Propuesta breve para Fase 3B

Solo deberia abrirse si se aprueba una migracion minima y compatible.

Candidatos reales:

1. Retirar el soporte legacy con `:` cuando se confirme estabilidad del formato nuevo con `_`.
2. Unificar `recharge_` bajo `recargar_`, si se define una convencion unica para solicitud y revision.

No recomendados para 3B inmediata:

- Renombrar prefijos validos pero no documentados como `acust_`, `adirs_`, `allycust_`, `local_`, `offer_`, `plat_`, `rating_`, `solequipo_`.
- Reordenar handlers o regex que hoy funcionan.
