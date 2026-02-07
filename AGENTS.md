# Reglas obligatorias del proyecto Domiquerendona

Este archivo define las reglas técnicas, operativas y de flujo de trabajo
que TODOS los agentes (Claude, Codex u otros) deben obedecer estrictamente.
No seguir estas reglas se considera un error grave.

---

## 1. Restricciones críticas (NO negociables)

- PROHIBIDO usar parse_mode o Markdown en cualquier mensaje del bot.
- PROHIBIDO duplicar handlers, estados de ConversationHandler o funciones.
  Si algo se reemplaza, el código anterior DEBE eliminarse.
- PROHIBIDO borrar bloques grandes sin mostrar primero el bloque exacto existente.
- PROHIBIDO ampliar el alcance sin autorización explícita del usuario.
- Cambios mínimos: un solo objetivo por instrucción.

---

## 2. Arquitectura y código

- main.py contiene solo orquestación y flujo.
  La lógica de negocio debe vivir en services.py u otros módulos.
- No crear funciones “similares” o redundantes.
  Una función = una responsabilidad clara.
- Respetar nombres, estructuras y funciones existentes.
- No introducir nuevos patrones si ya existe uno funcional.

---

## 3. Base de datos (reglas estrictas)

- Usar EXCLUSIVAMENTE get_connection() para acceso a base de datos.
  Está prohibido usar sqlite3.connect directo.
- Estados estándar únicos para TODOS los roles:
  PENDING, APPROVED, REJECTED, INACTIVE.
- Desde la interfaz nunca se elimina información.
  No DELETE desde UI: solo cambio de status.
- Permitir nuevo registro solo si el registro previo está en estado INACTIVE.
  Bloquear acciones si está en PENDING o APPROVED.
- Separación estricta de identificadores:
  - telegram_id es solo para mensajería
  - users.id es el ID interno principal
  - admins.id / couriers.id / allies.id son IDs de rol
  Nunca mezclar estos conceptos.

---

## 4. Flujos y estados

- Los estados son globales y coherentes entre roles.
- No crear estados nuevos sin validación explícita.
- No romper flujos existentes que ya funcionan.
- Cualquier ajuste debe ser compatible con el flujo actual del bot.

---

## 5. Flujo de trabajo con IA (obligatorio)

Antes de proponer o realizar cualquier cambio de código, el agente DEBE:

1. Localizar y mostrar el bloque exacto que será modificado.
2. Explicar brevemente qué se va a cambiar y por qué.
3. Confirmar la rama activa y el archivo exacto a tocar.

Durante el trabajo:
- No asumir errores solo por ver diffs (otros agentes usan colores visuales).
- No repetir pasos ya completados.
- No borrar ni reescribir archivos completos sin autorización.

Después de los cambios:
- Verificar compilación con:
  `python -m py_compile main.py`
- Reportar claramente qué cambió y qué se eliminó.

---

## 6. Git y ramas

- Nunca trabajar directamente sobre la rama main.
- Confirmar siempre la rama activa antes de modificar código.
- Si un bloque es reemplazado, el código anterior debe eliminarse
  (no dejar versiones muertas).
- Mantener el código limpio, sin duplicaciones ocultas.

---

## 7. Estilo de colaboración

- Priorizar estabilidad sobre velocidad.
- Preguntar antes de tomar decisiones ambiguas.
- No improvisar soluciones.
- Asumir que el usuario es técnico, detallista y quiere control total
  sobre los cambios.

---

Estas reglas representan el estándar real del proyecto Domiquerendona
y deben respetarse en todas las sesiones actuales y futuras.
