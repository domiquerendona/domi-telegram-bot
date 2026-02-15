# AGENTS.md — Reglas obligatorias del proyecto Domiquerendona

Este archivo define las **reglas técnicas, operativas y de flujo de trabajo**
que **TODOS los agentes** (Claude, Codex u otros) deben obedecer **estrictamente**.

⚠️ No seguir estas reglas se considera un **error grave**.  
⚠️ Estas reglas tienen **prioridad absoluta** sobre cualquier sugerencia del agente.

---

## 1. Restricciones críticas (NO negociables)

- PROHIBIDO usar `parse_mode` o Markdown en cualquier mensaje del bot.
- PROHIBIDO duplicar:
  - handlers,
  - estados de `ConversationHandler`,
  - funciones,
  - callbacks,
  - imports.
- Si algo se reemplaza, el código anterior **DEBE eliminarse en el mismo commit**.
- PROHIBIDO borrar bloques grandes sin mostrar primero el bloque exacto existente.
- PROHIBIDO ampliar el alcance sin autorización explícita del usuario.
- Cambios mínimos obligatorios:
  - **un solo objetivo por instrucción**.

---

## 2. Arquitectura y código

- `main.py` contiene **solo**:
  - orquestación,
  - flujo,
  - handlers.
- Toda la lógica de negocio debe vivir en:
  - `services.py`
  - u otros módulos dedicados.
- No crear funciones “similares” o redundantes.
  - Una función = **una sola responsabilidad clara**.
- Respetar nombres, estructuras y funciones existentes.
- No introducir nuevos patrones si ya existe uno funcional.

---

## 3. Base de datos (reglas estrictas)

- Usar **EXCLUSIVAMENTE** `get_connection()` para acceso a BD.
  - PROHIBIDO `sqlite3.connect()` directo.
- Estados estándar **únicos** para TODOS los roles:
PENDING, APPROVED, REJECTED, INACTIVE

- Desde la interfaz **NUNCA** se elimina información.
- No DELETE desde UI.
- Solo cambio de `status`.
- Permitir nuevo registro **solo** si el registro previo está en `INACTIVE`.
- Bloquear acciones si está en `PENDING` o `APPROVED`.
- Separación estricta de identificadores:
- `telegram_id` → solo mensajería
- `users.id` → ID interno principal
- `admins.id`, `couriers.id`, `allies.id` → IDs de rol
- **Nunca mezclar estos conceptos**.

---

## 4. Flujos y estados

- Los estados son globales y coherentes entre roles.
- No crear estados nuevos sin validación explícita.
- No romper flujos existentes que ya funcionan.
- Cualquier ajuste debe ser compatible con el flujo actual del bot.

---

## 5. Regla anti-duplicación (OBLIGATORIA)

Antes de escribir código, el agente DEBE:

- Buscar explícitamente con:
git grep

handlers, callbacks, estados, funciones e imports.
- Si un bloque se reemplaza:
- eliminar el bloque anterior en el mismo commit.
- PROHIBIDO dejar:
- versiones muertas,
- funciones no usadas,
- handlers registrados dos veces,
- callbacks duplicados con distinto patrón.

---

## 6. Flujo de trabajo con IA (OBLIGATORIO)

### Antes de cambiar código
El agente DEBE:

1. Mostrar el bloque exacto que va a modificar.
2. Explicar brevemente qué se va a cambiar y por qué.
3. Confirmar:
 - rama activa,
 - archivo exacto a tocar.

### Durante el trabajo
- No asumir errores solo por ver diffs.
- No repetir pasos ya completados.
- No reescribir archivos completos sin autorización.

### Después de los cambios
- Ejecutar obligatoriamente:
python -m py_compile main.py services.py db.py

- Reportar claramente:
- qué cambió,
- qué se eliminó,
- por qué.

---

## 7. Git y ramas

- Nunca trabajar directamente sobre `main`.
- Confirmar siempre la rama activa antes de modificar código.
- Si un bloque se reemplaza:
- el código anterior **DEBE desaparecer**.
- Mantener el repositorio:
- limpio,
- sin duplicaciones ocultas,
- sin código zombie.

---

## 8. Reglas específicas para agentes tipo Codex

Codex **NO improvisa**.

Codex DEBE:

- Preguntar cuando haya ambigüedad.
- No asumir reglas implícitas.
- Trabajar solo en el objetivo indicado.
- Actuar como:
- asistente de parches, o
- ejecutor controlado, según permisos.

Si Codex puede editar y ejecutar:
- Debe mostrar evidencia:
- comandos ejecutados,
- outputs relevantes,
- pruebas mínimas en BD/servicios.

Si Codex NO puede ejecutar:
- Debe entregar:
- bloques exactos ANTES / DESPUÉS,
- listos para pegar,
- sin ampliar alcance.

---

## 9. Reglas del sistema de recargas (CRÍTICAS)

### Definición oficial
- **“Mi admin”** =
vínculo con `status='APPROVED'` más reciente  
(`ORDER BY created_at DESC`).

### Plataforma vs Admin Local
- Admin Local:
- debe tener saldo para aprobar recargas.
- Admin Plataforma:
- puede aprobar sin validar saldo propio.

### Acreditación de saldo
- El saldo **SIEMPRE** se acredita en:
admin_couriers / admin_allies

usando el `admin_id` de la solicitud.
- No existe balance global del courier/ally.

### Vínculos
- No se puede aprobar una recarga
si **no existe vínculo APPROVED** con ese admin.
- Plataforma **NO** acredita si no hay vínculo APPROVED previo.

### Integridad
- Toda aprobación:
- actualiza saldos,
- registra movimiento en `ledger`.
- PROHIBIDO:
- doble aprobación,
- aprobación cruzada,
- forjar `admin_id` por callback.

---

## 10. Veracidad técnica y evidencia (OBLIGATORIA)

- Separar SIEMPRE entre:
  - IMPLEMENTADO (existe en el código actual)
  - DISEÑO FUTURO (idea/plan aún no implementado)
- PROHIBIDO afirmar que algo “existe” si no se puede señalar evidencia objetiva.
  - Para decir IMPLEMENTADO, el agente debe indicar: archivo + función/bloque
    (ej: `main.py: soy_repartidor()`, `services.py: quote_order_by_coords()`).
  - Si no hay evidencia, debe marcarlo como: PROPUESTA / FUTURO.
- No mezclar decisiones de diseño guardadas (p.ej. live location para ONLINE)
  como si estuvieran ya en producción.
- Si se está verificando una afirmación previa:
  - el agente debe contrastar con el código y declarar el veredicto
    (CORRECTO / PARCIAL / INCORRECTO) con evidencia.

---

## 11. Regla de decisiones y veredictos (OBLIGATORIA)

Antes de proponer **cambios** (refactors, migraciones, nuevos flujos o reglas),
el agente DEBE:

1. Exponer opciones concretas.
2. Preguntar primero.
3. Esperar confirmación explícita del usuario.
4. Solo después:
 - proponer plan final,
 - ejecutar cambios,
 - cerrar decisión.

NOTA: Esta regla aplica a **decisiones de cambio**.  
Para **verificación técnica** (auditoría / comprobación), el agente puede dar veredicto
directamente, siempre cumpliendo la sección 10 (evidencia).

PROHIBIDO cerrar decisiones de cambio por iniciativa propia.

---

## 12. Estilo de colaboración

- Priorizar estabilidad sobre velocidad.
- Preguntar antes de decidir.
- No improvisar soluciones.
- Asumir que el usuario:
- es técnico,
- es detallista,
- quiere control total del sistema.

---

Estas reglas representan el **estándar definitivo** del proyecto **Domiquerendona**
y deben respetarse en **todas las sesiones presentes y futuras**, sin excepción.