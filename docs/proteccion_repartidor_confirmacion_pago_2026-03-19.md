# Protección al repartidor: confirmación profesional del medio de pago

**Fecha de apertura:** 2026-03-19
**Estado:** FASES 1 Y 2 IMPLEMENTADAS — 2026-03-19
**Tipo:** Línea de proyecto — diseño y auditoría

---

## 1. Problema operativo

Hoy un aliado atiende clientes por WhatsApp antes de crear el pedido en el sistema.
Cuando llega el momento de despachar, el aliado suele preguntar al cliente si pagará
en efectivo o por transferencia. Sin embargo, esa confirmación es informal y no queda
registrada en ningún sistema.

### Caso típico problemático

1. El cliente dice "pagaré en efectivo".
2. El aliado crea el pedido con `requires_cash = True` y un monto (ej. $30.000).
3. El sistema filtra couriers con base suficiente (`available_cash >= 30.000`).
4. El courier acepta, recoge el pedido en la tienda, y el aliado le cobra $30.000.
5. El courier llega al punto de entrega y el cliente dice "yo ya pagué por transferencia".
6. El courier tiene $30.000 del aliado en su bolsillo que no puede cobrar al cliente.
7. Empieza la fricción: llamadas al aliado, devolución en tienda, pérdida de tiempo.

### Caso sin confirmación

1. El aliado no confirmó a tiempo con el cliente.
2. Crea el pedido con `requires_cash = True` como suposición.
3. El courier adelanta la base, pero el cliente pagó online antes del despacho.

---

## 2. Impacto en actores

| Actor | Impacto |
|-------|---------|
| **Repartidor** | Adelanta dinero innecesariamente, queda expuesto al riesgo de no recuperarlo si la info es incorrecta |
| **Aliado** | Pierde confianza del repartidor, queda mal con el equipo |
| **Operación** | Llamadas, retrasos, conflictos entre actores |
| **Plataforma** | Desgaste de red cooperativa; riesgo de abandono por couriers |

---

## 3. Objetivo del proyecto

Profesionalizar el flujo para que ningún pedido salga con ambigüedad sobre el medio de pago.

Específicamente:
- El pedido debe tener un **estado claro de confirmación de pago**.
- El repartidor **no debe adelantar dinero** si el pago no está confirmado.
- Si el cliente cambia el medio de pago **después del despacho**, el riesgo no debe recaer sobre el repartidor.
- Debe existir **trazabilidad** de quién confirmó, cuándo y bajo qué condición salió el pedido.

---

## 4. Reglas de negocio deseadas

1. Todo pedido con cobro al cliente debe tener un estado explícito de confirmación de pago antes del despacho.
2. Los estados conceptuales mínimos son:
   - `TRANSFERENCIA_CONFIRMADA` — el cliente ya pagó a la tienda; el courier no cobra nada.
   - `EFECTIVO_CONFIRMADO` — el cliente pagará en efectivo al recibir; el courier cobra y devuelve al aliado.
   - `PAGO_NO_CONFIRMADO` — no se sabe cómo pagará; el courier **no debe adelantar la base**.
3. Cuando el estado es `PAGO_NO_CONFIRMADO`, el courier no recibe el monto de la base; el campo `requires_cash` debe quedar en `False` y `cash_required_amount` en 0.
4. Solo se activa `requires_cash = True` cuando el efectivo está **explícitamente confirmado** por el aliado.
5. Si el cliente cambia el medio de pago después del despacho, el error no recae sobre el courier: el aliado es responsable de la confirmación que hizo al crear el pedido.
6. Toda confirmación debe tener trazabilidad: campo `payment_method_confirmed_by` + `payment_method_confirmed_at` en la orden.
7. Diseñado primero para operación asistida (aliado crea el pedido desde el bot), con visión de integración al formulario web (`/form/:token`).

---

## 5. Auditoría técnica del estado actual

### 5.1 Campos existentes relacionados con pago

**Tabla `orders` — columnas actuales relevantes:**

| Columna | Tipo | Valor por defecto | Descripción |
|---------|------|-------------------|-------------|
| `requires_cash` | INTEGER | 0 | Flag: el courier debe cobrar en efectivo al cliente |
| `cash_required_amount` | INTEGER | 0 | Monto en COP que debe cobrar |
| `total_fee` | INTEGER | 0 | Comisión de servicio del courier (siempre $300 base) |
| `customer_delivery_fee` | INTEGER | NULL | Lo que paga el cliente por el domicilio (después del subsidio) |
| `delivery_subsidy_applied` | INTEGER | 0 | Subsidio del aliado deducido del precio al cliente |
| `purchase_amount` | INTEGER | NULL | Valor de compra confirmado por el aliado (base para subsidio) |

**Evidencia:** `Backend/db.py:1206-1209` (migración SQLite), `Backend/migrations/postgres_schema.sql` líneas 358-381.

**Tabla `allies` — columnas de pago del aliado:**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `payment_phone` | TEXT | Nequi/Daviplata del aliado |
| `payment_bank` | TEXT | Banco del aliado |
| `payment_holder` | TEXT | Titular de la cuenta |
| `payment_instructions` | TEXT | Instrucciones de pago a clientes |

Estas columnas son informativas; no controlan el flujo del pedido.

### 5.2 Flujo actual de `requires_cash`

**Paso 1 — Aliado selecciona si requiere base (main.py:4305-4324)**

```
mostrar_pregunta_base() → muestra botones:
  "Si, requiere base" → pedido_base_si
  "No requiere base"  → pedido_base_no
```

El texto que ve el aliado es `BASE REQUERIDA`, no `MEDIO DE PAGO`. El concepto que
maneja el sistema hoy es la "base" (dinero físico que el courier lleva encima), **no
la confirmación de cómo pagará el cliente.**

**Paso 2 — Se selecciona monto (main.py:4342-4385)**

Opciones fijas: $5.000 / $10.000 / $20.000 / $50.000 / Otro valor.

**Paso 3 — Se guarda en `context.user_data` (main.py:4334, 4340, 4378, 4397)**

```python
context.user_data["requires_cash"] = True/False
context.user_data["cash_required_amount"] = valor_entero
```

**Paso 4 — Se filtra couriers elegibles (db.py:3015-3017)**

```python
if requires_cash and cash_required_amount > 0:
    query += f" AND c.available_cash >= {P}"
    params.append(cash_required_amount)
```

Solo se envía la oferta a couriers que **declaran tener esa base**. Esto protege
parcialmente al courier (no le llega si no tiene el dinero), pero no resuelve el
problema si el cliente cambia de medio de pago después del despacho.

**Paso 5 — La oferta muestra advertencia al courier (order_delivery.py:2612-2615)**

```python
if order["requires_cash"] and cash_amount > 0:
    text += "Base requerida: ${:,}\n".format(int(cash_amount))
    text += "\nADVERTENCIA: Si no tienes base suficiente, NO tomes este servicio.\n"
```

**Paso 6 — La orden se guarda con esos valores (main.py:7400-7401)**

```python
requires_cash=requires_cash,
cash_required_amount=cash_required_amount,
```

**Paso 7 — Al crear pedido de admin (main.py:7143-7144)**

```python
requires_cash=False,
cash_required_amount=0,
```

Los pedidos especiales de admin siempre salen sin cobro en efectivo. Correcto.

### 5.3 Qué hay y qué falta

| Aspecto | ¿Existe hoy? | Evidencia |
|---------|:---:|-----------|
| Flag binario efectivo sí/no (`requires_cash`) | ✅ | `db.py:1206`, `main.py:4334` |
| Monto a cobrar al cliente (`cash_required_amount`) | ✅ | `db.py:1209`, `main.py:4378` |
| Filtro de couriers por base disponible | ✅ | `db.py:3015-3017` |
| Advertencia al courier en la oferta | ✅ | `order_delivery.py:2612-2615` |
| Estado "transferencia confirmada" | ❌ | No existe ningún campo |
| Estado "pago no confirmado" | ❌ | No existe; el aliado **debe elegir** sí o no |
| Trazabilidad de quién confirmó el pago | ❌ | No hay campo `confirmed_by` ni `confirmed_at` |
| Mecanismo para cambiar medio de pago post-despacho | ❌ | No existe |
| Validación que bloquee al courier si pago es incierto | ❌ | El aliado puede poner cualquier valor sin confirmación real |
| Registro en ledger del cobro en efectivo | ❌ | El cobro en efectivo es completamente off-system |

### 5.4 Punto exacto donde se genera la ambigüedad

**`Backend/main.py:4305-4324` — función `mostrar_pregunta_base()`**

El sistema pregunta "¿requiere base?" como si fuera una decisión logística del courier,
no como una confirmación del medio de pago del cliente. El aliado puede responder "Sí"
sin haber hablado con el cliente, o con una respuesta ambigua del cliente.

No existe ningún paso que diga: "¿Confirmaste con el cliente que pagará en efectivo?"

### 5.5 Riesgos actuales

1. **Sin confirmación real:** el aliado puede marcar `requires_cash = True` sin que el
   cliente haya confirmado. El courier adelanta dinero sobre una suposición.

2. **Sin reversibilidad:** una vez publicado el pedido, no existe mecanismo para cambiar
   `requires_cash` o `cash_required_amount`. Si el cliente cambia de opinión después del
   despacho, no hay flujo para manejarlo.

3. **Sin trazabilidad:** no queda registro de si el aliado confirmó el pago antes de crear
   el pedido, ni cuándo lo hizo.

4. **Semántica confusa:** el campo se llama "base requerida" (concepto del courier) en lugar
   de "medio de pago confirmado" (concepto del cliente). Esto genera confusión semántica.

5. **Sin impacto financiero visible:** el cobro en efectivo es completamente off-system.
   No hay ledger entry, no hay flag en el pedido de que el cobro fue exitoso o fallido.

---

## 6. Propuesta técnica de implementación

> Esta sección es una propuesta de diseño. **No hay código implementado.**

### 6.1 Modelo conceptual recomendado

Agregar un campo `payment_method` a la tabla `orders` con los siguientes valores:

| Valor | Significado | Efecto en courier |
|-------|-------------|-------------------|
| `CASH_CONFIRMED` | Efectivo confirmado por el cliente | Courier recibe `requires_cash=True` + monto |
| `TRANSFER_CONFIRMED` | Transferencia confirmada; cliente ya pagó | `requires_cash=False`; courier no cobra nada |
| `UNCONFIRMED` | El aliado no ha confirmado el medio de pago con el cliente | `requires_cash=False`; courier no adelanta dinero |

Este campo **reemplaza semánticamente** a `requires_cash` (que seguiría existiendo como
campo técnico derivado), y agrega el estado intermedio `UNCONFIRMED` que hoy no existe.

### 6.2 Campos recomendados en tabla `orders`

| Campo nuevo | Tipo | Default | Descripción |
|-------------|------|---------|-------------|
| `payment_method` | TEXT | `'UNCONFIRMED'` | Estado del medio de pago del cliente |
| `payment_confirmed_at` | TIMESTAMP | NULL | Cuándo se marcó como confirmado |
| `payment_confirmed_by` | TEXT | NULL | `'ALLY'` o `'PLATFORM'` (expansible) |

`requires_cash` se derivaría de `payment_method == 'CASH_CONFIRMED'` al momento de
publicar la oferta. No es necesario eliminar el campo existente; se puede mantener
como campo técnico que se setea automáticamente.

### 6.3 Responsabilidades por capa

| Responsabilidad | Capa |
|-----------------|------|
| Preguntar al aliado el medio de pago | UI Bot (`main.py`) |
| Validar que el estado sea `CASH_CONFIRMED` para activar `requires_cash` | Servicio (`services.py`) |
| Persistir `payment_method`, `payment_confirmed_at`, `payment_confirmed_by` | DB (`db.py`) |
| Mostrar el medio de pago en la oferta al courier | `order_delivery.py` |
| Bloquear creación de pedido si pago es `UNCONFIRMED` y el aliado no acepta el riesgo | Servicio o UI Bot |
| Exponer `payment_method` en formulario web | `web/api/form.py` |

### 6.4 Validaciones que deben bloquear al courier de adelantar dinero

1. Si `payment_method == 'UNCONFIRMED'` → `requires_cash = False`, `cash_required_amount = 0`.
   El courier nunca recibe la oferta con advertencia de base requerida si el pago no está confirmado.

2. Si `payment_method == 'TRANSFER_CONFIRMED'` → misma consecuencia: el courier no adelanta nada.

3. Solo con `payment_method == 'CASH_CONFIRMED'` se activa `requires_cash = True` y el filtro de base.

### 6.5 Qué ocurre si el cliente cambia el medio de pago después del despacho

El aliado es el responsable de la confirmación que hizo al crear el pedido. El sistema
**no tiene que resolver el problema financiero en tiempo real**, sino:

1. Tener trazabilidad: el pedido muestra `payment_method = 'CASH_CONFIRMED'` + `confirmed_at`.
2. Si el courier llega y el cliente ya pagó: el aliado debe devolver el efectivo al courier
   directamente. El sistema registra la incidencia pero no la resuelve automáticamente en fase 1.
3. En fase 2, podría construirse un flujo de "cambio de medio de pago post-despacho" con
   notificación al admin para mediación.

### 6.6 Fases de implementación

#### Fase 1 — Mínimo viable protector (recomendado primero)

Alcance:
- Agregar `payment_method TEXT DEFAULT 'UNCONFIRMED'` en tabla `orders`.
- Cambiar la pregunta de creación de pedido de "¿requiere base?" a "¿Cómo pagará el cliente?".
- Opciones: "Efectivo (confirmado)", "Transferencia (ya pagó)", "No confirmado aún".
- Si elige "No confirmado": `requires_cash=False`, advertencia al aliado en el preview.
- Agregar campos `payment_confirmed_at` y `payment_confirmed_by` en `orders`.
- Mostrar el medio de pago en la oferta al courier de forma clara.
- No requiere cambios en el ledger ni en `apply_service_fee`.

Archivos afectados:
- `Backend/db.py` — migración + `create_order()` + `get_order_*` para exponer el campo
- `Backend/main.py` — reemplazar `mostrar_pregunta_base()` con nueva función
- `Backend/order_delivery.py` — ajustar `_build_offer_text()` para mostrar medio de pago

#### Fase 2 — Trazabilidad y cambio post-despacho

Alcance:
- Flujo de "cambio de medio de pago post-despacho" iniciado por el aliado.
- Notificación al courier y al admin si el medio de pago cambia después de PICKED_UP.
- Exposición del campo `payment_method` en el panel web (vista de pedido).
- Posible ledger entry para casos de cobro en efectivo exitoso.

Archivos adicionales:
- `Backend/web/api/admin.py` — exponer `payment_method` en detalle de pedido
- `Frontend` — mostrar estado de pago en vista de pedidos

#### Fase 3 — Integración con formulario web

Alcance:
- El formulario web (`/form/:token`) permite al cliente declarar su medio de pago.
- El aliado recibe la solicitud con el medio de pago declarado por el cliente.
- El aliado confirma o corrige antes de crear el pedido.

Archivos adicionales:
- `Backend/web/api/form.py` — agregar campo `payment_method` en submit
- `Frontend/src/app/features/public/form-pedido.ts` — UI para selección de pago

### 6.7 Riesgos de implementación

| Riesgo | Mitigación |
|--------|------------|
| Romper el flujo existente de `requires_cash` | Mantener `requires_cash` como campo técnico; `payment_method` es la nueva fuente semántica |
| Aliados no entienden la nueva pregunta | Redactar opciones en lenguaje operativo, no técnico |
| Couriers confundidos por nueva información en oferta | Agregar gradualmente; la oferta existente ya muestra "Base requerida" |
| Migración dual SQLite/PostgreSQL | Seguir el patrón existente en `init_db()`: `ALTER TABLE IF NOT EXISTS` + PRAGMA table_info |
| Compatibilidad con pedidos existentes | `payment_method DEFAULT 'UNCONFIRMED'`; no afecta pedidos históricos |

---

## 7. Partes del flujo actual reutilizables

| Componente actual | Reutilizable | Ajuste necesario |
|-------------------|:---:|------------------|
| `requires_cash` flag en `orders` | ✅ | Se convierte en campo derivado de `payment_method` |
| `cash_required_amount` en `orders` | ✅ | Sin cambio |
| Filtro de couriers por `available_cash` en `db.py:3015-3017` | ✅ | Condición ya correcta; sigue funcionando |
| Advertencia en oferta (`order_delivery.py:2612-2615`) | ✅ | Expandir para mostrar también "Transferencia" o "No confirmado" |
| Preview de oferta en `construir_preview_oferta()` (`main.py:7542`) | ✅ | Agregar `payment_method` al preview |
| Estado `PEDIDO_REQUIERE_BASE` y handlers asociados | Parcial | Renombrar/reemplazar con nueva lógica; los callbacks `pedido_base_*` deberían cambiar a `pedido_pago_*` |
| `create_order()` en `db.py` | ✅ | Agregar `payment_method`, `payment_confirmed_at`, `payment_confirmed_by` |

---

## 8. Decisiones abiertas

1. **¿Permitir pedido con `UNCONFIRMED`?**
   Opción A: bloquear — el aliado debe confirmar antes de crear el pedido.
   Opción B: permitir con advertencia — el pedido sale sin cobro en efectivo, el aliado asume el riesgo.
   *Recomendación: opción B para fase 1. Menos fricción, misma protección al courier.*

2. **¿Quién puede cambiar el `payment_method` post-despacho?**
   Solo el aliado (quien creó el pedido). El admin puede mediar.

3. **¿El cambio post-despacho afecta el ledger?**
   En fase 1: no. El cobro en efectivo sigue siendo off-system.
   En fase 2: podría registrarse como memo entry.

4. **¿Renombrar `requires_cash` en la BD?**
   No en fase 1. Mantener compatibilidad. Solo agregar `payment_method` encima.

5. **¿Exponer `payment_method` en el panel web desde fase 1?**
   Bajo costo. Recomendado hacerlo junto con el endpoint de detalle de pedido.

---

## 9. Recomendación final

**Implementar fase 1 antes de escalar la red cooperativa.**

El crecimiento de la red cooperativa multiplica el problema: más couriers, más aliados,
más pedidos con ambigüedad de pago. La fase 1 es un cambio pequeño (una pregunta
diferente en el bot + un campo nuevo en la BD) que resuelve el caso más común.

La clave es cambiar la semántica de "¿requiere base?" a "¿cómo paga el cliente?".
Eso solo requiere modificar `mostrar_pregunta_base()` en `main.py` y agregar la migración
en `db.py`. El resto del sistema (`requires_cash`, filtros, oferta al courier) ya está
preparado para recibir el cambio.

---

*Documento generado: 2026-03-19. Última actualización: 2026-03-19.*
*Estado: Fases 1 y 2 implementadas. Fase 3 pendiente (formulario público).*

---

## 10. Estado de implementacion

**Fecha:** 2026-03-19

### Fase 1: completada

**Archivos modificados:**

- `db.py`
  - Migración idempotente: columnas `payment_method`, `payment_confirmed_at`, `payment_confirmed_by` agregadas a `orders` (SQLite y PostgreSQL).
  - Firma de `create_order` extendida con los tres parámetros nuevos.
  - INSERT de `create_order` actualizado: columnas, placeholders y tupla de valores alineados (36 cada uno).

- `main.py`
  - `mostrar_pregunta_base`: reemplazada — ahora muestra tres opciones de medio de pago ("Efectivo confirmado", "Transferencia confirmada", "Pago no confirmado").
  - `pedido_requiere_base_callback`: reemplazada — maneja `CASH_CONFIRMED`, `TRANSFER_CONFIRMED` y `UNCONFIRMED`; solo activa `requires_cash=True` cuando el efectivo está confirmado.
  - Patrón del handler `PEDIDO_REQUIERE_BASE` corregido a `^pedido_pago_(efectivo|transferencia|sin_confirmar)$`.
  - Llamada a `create_order` en flujo aliado (`pedido_confirmacion_callback`): pasa los tres campos nuevos.
  - Llamada a `create_order` en flujo admin (`admin_pedido_confirmar_callback`): pasa los tres campos nuevos.

- `order_delivery.py`
  - `_build_offer_text`: oferta al courier muestra el estado de pago confirmado en lugar de la advertencia genérica; "Base requerida" queda exclusivamente dentro del bloque `CASH_CONFIRMED`.

### Fase 2: completada

**Fecha:** 2026-03-19

**Archivos modificados:**

- `db.py`
  - Migración idempotente: columnas `payment_changed_at`, `payment_changed_by`, `payment_prev_method` agregadas a `orders`.
  - Nueva función `update_order_payment(order_id, payment_method, cash_required_amount, changed_by)`: actualiza medio de pago, mantiene snapshot del método anterior en `payment_prev_method`, actualiza `requires_cash` y `cash_required_amount` de forma consistente.

- `main.py`
  - `_ally_bandeja_mostrar_pedido`: muestra línea con el medio de pago actual del pedido; agrega botón "Cambiar medio de pago" solo si el pedido está en `PUBLISHED` o `ACCEPTED`.
  - `ally_cambio_pago_conv` (ConversationHandler, estados `ALLY_CAMBIO_PAGO_METODO=966` / `ALLY_CAMBIO_PAGO_MONTO=967`): flujo completo de selección de método nuevo, ingreso de monto si aplica (`CASH_CONFIRMED`), y confirmación de cambio.
  - `_notificar_courier_cambio_pago`: envía mensaje informativo al courier cuando el pedido ya está en `ACCEPTED` (el courier ya tomó el servicio); no aplica para `PUBLISHED`.

- `services.py`
  - `update_order_payment` re-exportada al bloque de re-exports para que `main.py` la consuma sin importar `db.py` directamente.

### Pendiente fase 3

Integración con formulario público `/form/:token`: el cliente declara su medio de pago al enviar la solicitud; el aliado confirma o corrige antes de crear el pedido.
