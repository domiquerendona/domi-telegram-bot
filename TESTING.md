# 🧪 GUÍA DE TESTING - FASE 1: MIGRACIÓN WHATSAPP

**Proyecto**: Domiquerendona Telegram Bot
**Versión**: FASE 1 - Post-Migración WhatsApp
**Branch**: `claude/fix-project-errors-PpBQS`
**Commit**: `9064bd4`
**Fecha**: 2026-01-19

---

## 📑 ÍNDICE

1. [⚡ Checklist Express (10 minutos)](#-checklist-express-10-minutos)
2. [Prerequisitos](#prerequisitos)
3. [Configuración de Entorno de Testing](#configuración-de-entorno-de-testing)
4. [Prueba 1: Admin PENDING Visible](#prueba-1-admin-pending-visible)
5. [Prueba 2: Vinculación Repartidor + Notificación](#prueba-2-vinculación-repartidor--notificación)
6. [Prueba 3: Panel /mi_admin Sin Bloqueo](#prueba-3-panel-mi_admin-sin-bloqueo)
7. [Prueba 4: Aprobación de Repartidor](#prueba-4-aprobación-de-repartidor)
8. [Evidencias Requeridas](#evidencias-requeridas)
9. [Checklist de Troubleshooting](#checklist-de-troubleshooting)
10. [Queries SQL de Verificación](#queries-sql-de-verificación)

---

## ⚡ CHECKLIST EXPRESS (10 MINUTOS)

**Para validación rápida de FASE 1 sin leer todo el documento.**

### 1️⃣ Crear Admin PENDING (2 min)

```
Telegram: /soy_admin
Completar registro → Admin queda status=PENDING con TEAM_CODE (ej: TEAM5)
```

**Verificar**:
```bash
sqlite3 domi.db "SELECT team_code, status FROM admins ORDER BY id DESC LIMIT 1;"
# Output: TEAM5|PENDING
```

### 2️⃣ Admin PENDING Aparece en Lista (1 min)

```
Telegram (otro usuario): /soy_aliado
Completar registro → Ver lista de equipos
```

**✅ DEBE MOSTRAR**: `[Equipo X (TEAM5) [Pendiente]]`

### 3️⃣ Repartidor se Vincula + Notificación (3 min)

```
Telegram (nuevo usuario): /soy_repartidor
Completar registro → Ingresar: TEAM5
```

**✅ CRÍTICO - Verificar que ADMIN recibe notificación**:
```
📥 Nueva solicitud de repartidor para tu equipo.
Repartidor ID: X
Equipo: [nombre]
Código: TEAM5

Entra a /mi_admin para aprobar o rechazar.
```

**⚠️ Si NO llega notificación**: Admin debe hacer `/start` con el bot primero (Telegram no permite enviar a usuarios que no iniciaron conversación).

### 4️⃣ Panel /mi_admin Sin Bloqueo (2 min)

```
Telegram (admin): /mi_admin
```

**✅ DEBE MOSTRAR**:
```
📊 Estado del equipo:
• Repartidores vinculados: 1
• Con saldo >= 5000: 0

Panel de administración habilitado.  ← NO debe decir "No cumple mínimo"

[⏳ Repartidores pendientes (mi equipo)]  ← 3 botones, no 1
[📋 Ver mi estado]
[🔄 Verificar requisitos]
```

### 5️⃣ Aprobar Repartidor (2 min)

```
/mi_admin → [⏳ Repartidores pendientes]
Ver repartidor → [✅ Aprobar]
```

**Verificar**:
```bash
sqlite3 domi.db "SELECT status FROM admin_couriers WHERE admin_id = 5 LIMIT 1;"
# Output: APPROVED
```

---

### ✅ Si los 5 pasos funcionan: FASE 1 OK

**Siguiente**: Leer documento completo para testing exhaustivo y evidencias formales.

---

## PREREQUISITOS

### Software Necesario

- ✅ Python 3.8+
- ✅ SQLite3
- ✅ Cuenta de Telegram (para testing)
- ✅ Bot de Telegram creado con @BotFather (token LOCAL)
- ✅ Acceso a cuenta de Admin de Plataforma (configurado en .env)

### Archivos Requeridos

```bash
# Verificar existencia de archivos críticos
ls -la main.py db.py services.py .env domi.db
```

### Variables de Entorno (.env)

```bash
# .env debe contener:
BOT_TOKEN=<tu_token_de_testing_local>
ADMIN_USER_ID=<tu_telegram_id_de_admin_plataforma>
```

**⚠️ IMPORTANTE**: Usar token de bot de TESTING, NO de PROD.

---

## CONFIGURACIÓN DE ENTORNO DE TESTING

### 1. Clonar Base de Datos (Opcional - Seguridad)

```bash
# Backup de DB producción (si aplica)
cp domi.db domi.db.backup

# Crear DB limpia para testing
rm domi.db  # Solo si quieres empezar limpio
python3 -c "from db import init_db; init_db()"
```

### 2. Verificar Compilación

```bash
python3 -m py_compile main.py db.py services.py
echo "Compilación OK"
```

### 3. Iniciar Bot en Modo Debug

```bash
# Ejecutar con logs visibles
python3 main.py 2>&1 | tee testing.log
```

**Logs esperados al inicio**:
```
INFO - Bot iniciado
INFO - Polling iniciado
```

### 4. Obtener Tu telegram_id

```bash
# Enviar /start al bot
# Luego ejecutar:
sqlite3 domi.db "SELECT telegram_id FROM users ORDER BY id DESC LIMIT 1;"
```

Guardar este ID para configurar como ADMIN_USER_ID.

---

## PRUEBA 1: ADMIN PENDING VISIBLE

### 🎯 Objetivo

Verificar que un admin recién registrado (status=PENDING) aparece en la lista de equipos disponibles para aliados y repartidores.

### 📋 Pasos de Ejecución

#### 1.1 Crear Admin Local Nuevo

```
Telegram Bot:
┌────────────────────────────────────┐
│ Usuario: @testing_user             │
└────────────────────────────────────┘

/soy_admin

┌────────────────────────────────────┐
│ Registro de Administrador Local.   │
│ Escribe tu nombre completo:        │
└────────────────────────────────────┘
```

**Ingresar datos**:
```
Nombre completo: Admin Test WhatsApp
Documento: 12345678
Nombre del equipo: Equipo WhatsApp Migracion
Teléfono: +573001234567
Ciudad: Bogotá
Barrio: Chapinero
¿Es correcto? SI
```

**Resultado esperado**:
```
✅ Listo. Tu registro quedó en estado PENDING.
Cuando el Admin de Plataforma lo apruebe, podrás operar.
```

#### 1.2 Verificar en Base de Datos

```bash
sqlite3 domi.db "SELECT id, team_name, team_code, status FROM admins WHERE team_name LIKE '%WhatsApp%';"
```

**Output esperado**:
```
5|Equipo WhatsApp Migracion|TEAM5|PENDING
```

✅ **CHECKPOINT 1**: Admin creado con status=PENDING

#### 1.3 Crear Aliado y Verificar Visibilidad

```
Telegram Bot (nueva cuenta o mismo usuario):
/soy_aliado

[Completar registro de aliado]
Nombre del negocio: Tienda Test
Nombre del dueño: Juan Pérez
Dirección: Calle 10 #20-30
Ciudad: Bogotá
Teléfono: +573009876543
Barrio: Chapinero
¿Es correcto? SI
```

**Pantalla de selección de equipo**:
```
¿A qué equipo (Administrador) quieres pertenecer?

[Equipo WhatsApp Migracion (TEAM5) [Pendiente]]  ← DEBE APARECER
[Ninguno (Admin de Plataforma)]
```

✅ **CHECKPOINT 2**: Admin PENDING visible con etiqueta "[Pendiente]"

#### 1.4 Seleccionar Equipo PENDING

```
Presionar: [Equipo WhatsApp Migracion (TEAM5) [Pendiente]]

Resultado esperado:
┌────────────────────────────────────┐
│ Listo. Elegiste el equipo:         │
│ Equipo WhatsApp Migracion (TEAM5)  │
│                                    │
│ Tu vínculo quedó en estado PENDING │
│ hasta aprobación.                  │
└────────────────────────────────────┘
```

#### 1.5 Verificar Vínculo en Base de Datos

```bash
sqlite3 domi.db "SELECT admin_id, ally_id, status FROM admin_allies WHERE admin_id = 5;"
```

**Output esperado**:
```
5|1|PENDING
```

✅ **CHECKPOINT 3**: Vínculo admin_allies creado correctamente

---

### ✅ CRITERIOS DE ÉXITO - PRUEBA 1

| Criterio | Verificación | Estado |
|----------|--------------|--------|
| Admin creado con PENDING | `SELECT status FROM admins WHERE id = 5;` → PENDING | ⬜ |
| Admin aparece en lista | Screenshot mostrando "[Pendiente]" | ⬜ |
| Vínculo creado | `SELECT * FROM admin_allies WHERE admin_id = 5;` | ⬜ |
| No hay errores en log | `grep ERROR testing.log` → vacío | ⬜ |

---

## PRUEBA 2: VINCULACIÓN REPARTIDOR + NOTIFICACIÓN

### 🎯 Objetivo

Verificar que:
1. Un repartidor puede vincularse a un admin PENDING ingresando TEAM_CODE manualmente
2. El admin recibe notificación en Telegram (usando telegram_id correcto)

### 📋 Pasos de Ejecución

#### 2.1 Obtener telegram_id del Admin

```bash
# Identificar telegram_id del admin creado en PRUEBA 1
sqlite3 domi.db "
SELECT u.telegram_id, a.team_code, a.full_name
FROM admins a
JOIN users u ON u.id = a.user_id
WHERE a.team_code = 'TEAM5';
"
```

**Output esperado**:
```
123456789|TEAM5|Admin Test WhatsApp
```

**⚠️ IMPORTANTE**: Guardar este telegram_id (debe ser número grande de 9-10 dígitos, NO 1-5).

✅ **CHECKPOINT 1**: telegram_id obtenido correctamente

#### 2.2 Crear Repartidor

```
Telegram Bot (nueva cuenta de testing):
/soy_repartidor

[Completar registro]
Nombre completo: Repartidor Test
Cédula: 87654321
Teléfono: +573005551234
Ciudad: Bogotá
Barrio: Chapinero
Placa: ABC123
Tipo de moto: 150cc
¿Es correcto? SI
```

**Resultado esperado**:
```
✅ Perfecto. Tu registro quedó en estado PENDING.

Código interno asignado: COUR-20250119-0001

Ahora, si deseas unirte a un Administrador Local,
escribe el CÓDIGO DE EQUIPO (ej: TEAM1).
Si no tienes código, escribe: NO
```

#### 2.3 Ingresar TEAM_CODE del Admin PENDING

```
Escribir: TEAM5
```

**Resultado esperado** (repartidor):
```
✅ Perfecto. Solicitaste unirte al equipo:
Equipo WhatsApp Migracion (TEAM5)

Tu solicitud quedó en estado PENDING.
Espera aprobación del administrador.
```

✅ **CHECKPOINT 2**: Repartidor vinculado exitosamente

#### 2.4 VERIFICAR NOTIFICACIÓN AL ADMIN (CRÍTICO)

**En la cuenta de Telegram del admin** (telegram_id del CHECKPOINT 1):

```
Debe recibir mensaje:
┌────────────────────────────────────┐
│ 📥 Nueva solicitud de repartidor   │
│    para tu equipo.                 │
│                                    │
│ Repartidor ID: 1                   │
│ Equipo: Equipo WhatsApp Migracion  │
│ Código: TEAM5                      │
│                                    │
│ Entra a /mi_admin para aprobar o  │
│ rechazar.                          │
└────────────────────────────────────┘
```

**🔴 SI NO RECIBE NOTIFICACIÓN**: Ver [Checklist de Troubleshooting](#checklist-de-troubleshooting-notificación-fallida)

✅ **CHECKPOINT 3**: Notificación recibida correctamente

#### 2.5 Verificar Vínculo en Base de Datos

```bash
sqlite3 domi.db "
SELECT ac.admin_id, ac.courier_id, ac.status, c.full_name, c.code
FROM admin_couriers ac
JOIN couriers c ON c.id = ac.courier_id
WHERE ac.admin_id = 5;
"
```

**Output esperado**:
```
5|1|PENDING|Repartidor Test|COUR-20250119-0001
```

✅ **CHECKPOINT 4**: Vínculo admin_couriers creado

#### 2.6 Verificar Log del Bot

```bash
grep "admin_telegram_id" testing.log | tail -5
```

**Output esperado** (debe mostrar número grande, NO pequeño):
```
[DEBUG] admin_telegram_id = 123456789  ← CORRECTO (9 dígitos)
```

**❌ Output INCORRECTO** (bug pre-FASE 1):
```
[DEBUG] admin_telegram_id = 5  ← INCORRECTO (users.id)
```

✅ **CHECKPOINT 5**: telegram_id correcto en logs

---

### ✅ CRITERIOS DE ÉXITO - PRUEBA 2

| Criterio | Verificación | Estado |
|----------|--------------|--------|
| Repartidor creado | `SELECT id, code FROM couriers WHERE full_name = 'Repartidor Test';` | ⬜ |
| Vínculo creado | `SELECT * FROM admin_couriers WHERE admin_id = 5 AND courier_id = 1;` | ⬜ |
| **Notificación recibida** | Screenshot de mensaje en Telegram del admin | ⬜ |
| telegram_id correcto en log | `grep admin_telegram_id testing.log` → número grande | ⬜ |
| Sin errores de send_message | `grep "No se pudo notificar" testing.log` → vacío | ⬜ |

---

## PRUEBA 3: PANEL /mi_admin SIN BLOQUEO

### 🎯 Objetivo

Verificar que un admin con 0 repartidores aprobados puede acceder al panel `/mi_admin` sin bloqueos (FASE 1).

### 📋 Pasos de Ejecución

#### 3.1 Estado Inicial

**Verificar que admin tiene 0 repartidores aprobados**:

```bash
sqlite3 domi.db "
SELECT COUNT(*)
FROM admin_couriers
WHERE admin_id = 5 AND status = 'APPROVED';
"
```

**Output esperado**:
```
0
```

✅ **CHECKPOINT 1**: Admin con 0 repartidores aprobados

#### 3.2 Ejecutar /mi_admin

```
Telegram Bot (cuenta del admin):
/mi_admin
```

**Resultado esperado** (FASE 1 - SIN BLOQUEO):
```
┌────────────────────────────────────┐
│ Panel Administrador Local          │
│                                    │
│ Equipo: Equipo WhatsApp Migracion  │
│        (TEAM5)                     │
│                                    │
│ 📊 Estado del equipo:              │
│ • Repartidores vinculados: 1       │
│ • Con saldo >= 5000: 0             │
│                                    │
│ Panel de administración habilitado.│
│ Selecciona una opción:             │
│                                    │
│ [⏳ Repartidores pendientes (mi equipo)]│
│ [📋 Ver mi estado]                 │
│ [🔄 Verificar requisitos]          │
└────────────────────────────────────┘
```

**❌ Output INCORRECTO** (comportamiento pre-FASE 1):
```
┌────────────────────────────────────┐
│ Panel Administrador Local          │
│                                    │
│ No cumple mínimo de repartidores:  │
│ 0/10.                              │
│                                    │
│ [🔄 Verificar de nuevo]            │
└────────────────────────────────────┘
```

✅ **CHECKPOINT 2**: Panel completo mostrado (3 botones, no 1)

#### 3.3 Verificar Contadores

```
Presionar: [🔄 Verificar requisitos]

Resultado esperado:
┌────────────────────────────────────┐
│ Panel Administrador Local          │
│                                    │
│ Estado: PENDING                    │
│                                    │
│ 📊 Estado del equipo:              │
│ • Repartidores vinculados: 1       │
│ • Con saldo >= 5000: 0             │
│                                    │
│ Panel habilitado. Selecciona...    │
│                                    │
│ [⏳ Repartidores pendientes]       │
│ [📋 Ver mi estado]                 │
│ [🔄 Verificar de nuevo]            │
└────────────────────────────────────┘
```

✅ **CHECKPOINT 3**: Requisitos mostrados como información, NO como bloqueo

#### 3.4 Verificar Log de admin_puede_operar

```bash
grep "admin_puede_operar" testing.log | tail -3
```

**Output esperado**:
```
[DEBUG] admin_puede_operar(admin_id=5) → ok=False, total=1, okb=0
[INFO] FASE 1: Mostrando requisitos como info, no como bloqueo
```

✅ **CHECKPOINT 4**: Función ejecutada pero no bloquea

---

### ✅ CRITERIOS DE ÉXITO - PRUEBA 3

| Criterio | Verificación | Estado |
|----------|--------------|--------|
| Panel se abre sin bloqueo | Screenshot mostrando 3 botones | ⬜ |
| Contadores correctos | Repartidores vinculados: 1, Con saldo: 0 | ⬜ |
| Mensaje "habilitado" | No dice "No cumple mínimo" | ⬜ |
| Botones accesibles | Puede presionar "Repartidores pendientes" | ⬜ |

---

## PRUEBA 4: APROBACIÓN DE REPARTIDOR

### 🎯 Objetivo

Verificar que el admin local puede aprobar repartidores desde su panel.

### 📋 Pasos de Ejecución

#### 4.1 Ver Repartidores Pendientes

```
Telegram Bot (cuenta del admin):
/mi_admin
Presionar: [⏳ Repartidores pendientes (mi equipo)]
```

**Resultado esperado**:
```
┌────────────────────────────────────┐
│ Repartidores pendientes (TEAM5):   │
│                                    │
│ [COUR-20250119-0001: Repartidor Test]│
└────────────────────────────────────┘
```

✅ **CHECKPOINT 1**: Lista de repartidores pendientes visible

#### 4.2 Ver Detalles del Repartidor

```
Presionar: [COUR-20250119-0001: Repartidor Test]

Resultado esperado:
┌────────────────────────────────────┐
│ Repartidor COUR-20250119-0001      │
│                                    │
│ Nombre: Repartidor Test            │
│ Cédula: 87654321                   │
│ Teléfono: +573005551234            │
│ Ciudad: Bogotá                     │
│ Barrio: Chapinero                  │
│ Placa: ABC123                      │
│ Tipo de moto: 150cc                │
│                                    │
│ [✅ Aprobar]                        │
│ [❌ Rechazar]                       │
│ [⛔ Bloquear]                       │
└────────────────────────────────────┘
```

✅ **CHECKPOINT 2**: Detalles completos mostrados

#### 4.3 Aprobar Repartidor

```
Presionar: [✅ Aprobar]

Resultado esperado:
┌────────────────────────────────────┐
│ ✅ Aprobado.                        │
│                                    │
│ Repartidor COUR-20250119-0001      │
│ fue aprobado en tu equipo TEAM5.   │
└────────────────────────────────────┘
```

#### 4.4 Verificar en Base de Datos

```bash
sqlite3 domi.db "
SELECT status, accepted_at
FROM admin_couriers
WHERE admin_id = 5 AND courier_id = 1;
"
```

**Output esperado**:
```
APPROVED|2025-01-19 15:30:45
```

✅ **CHECKPOINT 3**: Status cambiado a APPROVED con timestamp

#### 4.5 Verificar Contadores Actualizados

```
/mi_admin
[🔄 Verificar requisitos]

Resultado esperado:
┌────────────────────────────────────┐
│ 📊 Estado del equipo:              │
│ • Repartidores vinculados: 1       │
│ • Con saldo >= 5000: 0             │
│                                    │
│ (sin cambios, saldo sigue en 0)    │
└────────────────────────────────────┘
```

✅ **CHECKPOINT 4**: Contadores consistentes

---

### ✅ CRITERIOS DE ÉXITO - PRUEBA 4

| Criterio | Verificación | Estado |
|----------|--------------|--------|
| Repartidor visible en lista | Screenshot de lista pendientes | ⬜ |
| Detalles completos | Screenshot mostrando todos los campos | ⬜ |
| Aprobación exitosa | `SELECT status FROM admin_couriers...` → APPROVED | ⬜ |
| Timestamp registrado | accepted_at tiene fecha/hora | ⬜ |

---

## EVIDENCIAS REQUERIDAS

### 📸 Screenshots Obligatorios

| Prueba | Screenshot | Qué debe mostrar |
|--------|------------|------------------|
| **Prueba 1** | `01-admin-pending-visible.png` | Lista de equipos con "Equipo WhatsApp (TEAM5) [Pendiente]" |
| **Prueba 2** | `02-notificacion-admin.png` | Mensaje de notificación recibido por admin |
| **Prueba 3** | `03-panel-sin-bloqueo.png` | Panel /mi_admin con 3 botones (no bloqueado) |
| **Prueba 4** | `04-repartidor-aprobado.png` | Confirmación de aprobación exitosa |

### 📊 Queries SQL de Verificación

#### Query 1: Verificar Admin PENDING

```sql
-- Ejecutar DESPUÉS de PRUEBA 1
SELECT
    a.id,
    a.team_name,
    a.team_code,
    a.status,
    u.telegram_id,
    COUNT(ac.courier_id) as total_couriers
FROM admins a
JOIN users u ON u.id = a.user_id
LEFT JOIN admin_couriers ac ON ac.admin_id = a.id
WHERE a.team_code = 'TEAM5'
GROUP BY a.id;
```

**Output esperado**:
```
id | team_name                  | team_code | status  | telegram_id | total_couriers
5  | Equipo WhatsApp Migracion  | TEAM5     | PENDING | 123456789   | 1
```

#### Query 2: Verificar Vínculos y Estados

```sql
-- Ejecutar DESPUÉS de PRUEBA 4
SELECT
    'ADMIN' as tipo,
    a.full_name as nombre,
    a.status,
    a.team_code
FROM admins a WHERE a.id = 5

UNION ALL

SELECT
    'COURIER' as tipo,
    c.full_name as nombre,
    c.status,
    c.code as team_code
FROM couriers c
JOIN admin_couriers ac ON ac.courier_id = c.id
WHERE ac.admin_id = 5

UNION ALL

SELECT
    'VÍNCULO COURIER' as tipo,
    'Admin ' || ac.admin_id || ' → Courier ' || ac.courier_id as nombre,
    ac.status,
    ac.accepted_at as team_code
FROM admin_couriers ac
WHERE ac.admin_id = 5;
```

**Output esperado**:
```
tipo            | nombre                  | status   | team_code
ADMIN           | Admin Test WhatsApp     | PENDING  | TEAM5
COURIER         | Repartidor Test         | PENDING  | COUR-20250119-0001
VÍNCULO COURIER | Admin 5 → Courier 1     | APPROVED | 2025-01-19 15:30:45
```

### 📝 Logs a Guardar

```bash
# Guardar logs completos de la sesión de testing
cat testing.log > evidencias/testing-fase1-$(date +%Y%m%d-%H%M%S).log

# Extraer solo errores (debe estar vacío)
grep -i "error\|exception\|traceback" testing.log > evidencias/errors.log
```

---

## CHECKLIST DE TROUBLESHOOTING

### 🔴 SI FALLA PRUEBA 1: Admin PENDING No Aparece

#### Verificar 1: Función get_available_admin_teams()

```bash
# Verificar que incluye PENDING
grep -A 5 "WHERE a.status" db.py | grep -n "PENDING"
```

**Debe contener**:
```python
WHERE a.status IN ('PENDING', 'APPROVED')
```

#### Verificar 2: Admin realmente creado

```bash
sqlite3 domi.db "SELECT id, status, team_code FROM admins ORDER BY id DESC LIMIT 1;"
```

**Si status != PENDING**: Revisar función `create_admin()` en db.py.

#### Verificar 3: team_code no NULL

```bash
sqlite3 domi.db "SELECT team_code FROM admins WHERE id = 5;"
```

**Si es NULL**: Admin no tiene team_code asignado.

**Solución**:
```sql
UPDATE admins SET team_code = 'TEAM5' WHERE id = 5;
```

---

### 🔴 SI FALLA PRUEBA 2: Notificación No Llega

#### Verificar 1: telegram_id correcto en get_admin_by_team_code()

```bash
# Verificar qué retorna la función
sqlite3 domi.db "
SELECT
    a.id,
    a.user_id,
    a.full_name,
    a.status,
    a.team_name,
    a.team_code,
    u.telegram_id
FROM admins a
JOIN users u ON u.id = a.user_id
WHERE a.team_code = 'TEAM5';
"
```

**Posición esperada**:
```
0: admin_id
1: user_id (NO telegram_id)
2: full_name
3: status
4: team_name
5: team_code
6: telegram_id ← ESTE es el correcto para notificaciones
```

#### Verificar 2: Código usa admin[6]

```bash
# Verificar línea crítica en main.py
grep -n "admin_telegram_id = admin\[" main.py
```

**Debe mostrar**:
```
900:    admin_telegram_id = admin[6]  # telegram_id REAL para notificaciones
```

**❌ Si muestra**:
```
admin_telegram_id = admin[1]  # ← INCORRECTO (es users.id)
```

**Solución**: Aplicar commit `9064bd4` (ya debería estar aplicado).

#### Verificar 3: Bot tiene permisos para enviar mensaje

```bash
# Revisar log de error al enviar
grep "No se pudo notificar\|send_message.*Exception" testing.log
```

**Errores comunes**:
- `Chat not found` → telegram_id incorrecto
- `Bot was blocked by the user` → Admin bloqueó el bot
- `Unauthorized` → Token de bot inválido

#### Verificar 4: Admin ejecutó /start con el bot

El admin debe haber iniciado conversación con el bot al menos una vez.

**Solución**: Admin debe enviar `/start` al bot antes de que le lleguen notificaciones.

---

### 🔴 SI FALLA PRUEBA 3: Panel Sigue Bloqueado

#### Verificar 1: Cambio aplicado en mi_admin()

```bash
# Verificar que NO tiene bloqueo por ok=False
grep -A 10 "admin_puede_operar(admin_id)" main.py | grep -n "if not ok"
```

**NO debe contener** (esto sería código viejo):
```python
if not ok:
    return  # ← BLOQUEA el panel
```

**DEBE contener** (FASE 1):
```python
ok, msg, total, okb = admin_puede_operar(admin_id)

estado_msg = (
    f"📊 Estado del equipo:\n"
    f"• Repartidores vinculados: {total}\n"
    # ...siempre muestra panel
)
```

#### Verificar 2: Función admin_puede_operar retorna 4 valores

```bash
grep -A 20 "def admin_puede_operar" services.py | grep "return"
```

**Debe retornar**:
```python
return True, "OK", total, ok
# o
return False, f"No cumple...", total, ok
```

**NO debe retornar solo 2 valores**:
```python
return False, "mensaje"  # ← Versión antigua
```

#### Verificar 3: Log de ejecución

```bash
grep "admin_puede_operar" testing.log | tail -5
```

**Debe mostrar**:
```
[DEBUG] admin_puede_operar(5) → (False, 'No cumple...', 1, 0)
[INFO] FASE 1: Mostrando como info, NO bloqueando
```

---

### 🔴 SI FALLA PRUEBA 4: No Puede Aprobar Repartidor

#### Verificar 1: Vínculo existe en admin_couriers

```bash
sqlite3 domi.db "SELECT * FROM admin_couriers WHERE admin_id = 5 AND courier_id = 1;"
```

**Si está vacío**: Repartidor no se vinculó correctamente en PRUEBA 2.

**Solución**: Repetir PRUEBA 2.

#### Verificar 2: Función update_admin_courier_status existe

```bash
grep -n "def update_admin_courier_status" db.py
```

**Debe existir** en db.py.

#### Verificar 3: Callback registrado

```bash
grep -n "local_courier_approve" main.py
```

**Debe aparecer** en:
- Definición de callback: `if data.startswith("local_courier_approve_"):`
- Botón en UI: `InlineKeyboardButton("✅ Aprobar", callback_data=f"local_courier_approve_{courier_id}")`

---

## QUERIES SQL DE VERIFICACIÓN

### Query: Estado Completo del Sistema

```sql
-- Vista general de todo el sistema
SELECT
    'TOTAL USERS' as entidad,
    COUNT(*) as cantidad,
    '-' as status
FROM users

UNION ALL

SELECT
    'ADMINS',
    COUNT(*),
    status
FROM admins
WHERE is_deleted = 0
GROUP BY status

UNION ALL

SELECT
    'COURIERS',
    COUNT(*),
    status
FROM couriers
WHERE is_deleted = 0
GROUP BY status

UNION ALL

SELECT
    'ALLIES',
    COUNT(*),
    status
FROM allies
WHERE is_deleted = 0
GROUP BY status

UNION ALL

SELECT
    'VÍNCULOS ADMIN-COURIER',
    COUNT(*),
    status
FROM admin_couriers
GROUP BY status;
```

### Query: Detalles de TEAM5 (Testing)

```sql
-- Información completa del admin de testing
SELECT
    a.id as admin_id,
    a.full_name as admin_name,
    a.team_code,
    a.status as admin_status,
    u.telegram_id,
    (SELECT COUNT(*) FROM admin_couriers WHERE admin_id = a.id) as total_couriers,
    (SELECT COUNT(*) FROM admin_couriers WHERE admin_id = a.id AND status = 'APPROVED') as approved_couriers,
    (SELECT COUNT(*) FROM admin_allies WHERE admin_id = a.id) as total_allies
FROM admins a
JOIN users u ON u.id = a.user_id
WHERE a.team_code = 'TEAM5';
```

### Query: Historial de Cambios de Estado

```sql
-- Ver todos los cambios (si existen logs)
-- Nota: Esta query asume que guardas historial, ajustar si no aplica

SELECT
    'admin_couriers' as tabla,
    admin_id,
    courier_id as entity_id,
    status,
    accepted_at as changed_at
FROM admin_couriers
WHERE admin_id = 5

UNION ALL

SELECT
    'admins' as tabla,
    id as admin_id,
    id as entity_id,
    status,
    created_at as changed_at
FROM admins
WHERE id = 5;
```

---

## 📋 CHECKLIST FINAL DE TESTING

### Antes de Marcar como "TESTING COMPLETO"

- [ ] **PRUEBA 1**: Admin PENDING aparece en lista con etiqueta "[Pendiente]"
- [ ] **PRUEBA 2**: Repartidor vinculado exitosamente
- [ ] **PRUEBA 2**: Admin recibió notificación en Telegram
- [ ] **PRUEBA 2**: telegram_id correcto en logs (9-10 dígitos)
- [ ] **PRUEBA 3**: Panel /mi_admin se abre sin bloqueo
- [ ] **PRUEBA 3**: Muestra 3 botones (no solo 1)
- [ ] **PRUEBA 3**: Mensaje dice "habilitado", no "No cumple mínimo"
- [ ] **PRUEBA 4**: Repartidor aprobado exitosamente
- [ ] **PRUEBA 4**: Status en DB cambió a APPROVED
- [ ] **PRUEBA 4**: accepted_at tiene timestamp

### Evidencias Recolectadas

- [ ] 4 screenshots guardados (01-admin-pending-visible.png, etc.)
- [ ] Query 1 ejecutada y resultado guardado
- [ ] Query 2 ejecutada y resultado guardado
- [ ] testing.log guardado en evidencias/
- [ ] errors.log revisado (debe estar vacío o sin errores críticos)

### Regresiones a Verificar

- [ ] Admin APPROVED sigue apareciendo en lista (no se rompió)
- [ ] Admin con 10+ repartidores sigue viendo panel completo
- [ ] ConversationHandlers de ally/courier siguen funcionando
- [ ] /cancel y /menu funcionan en flujos de registro

---

## 📊 FORMATO DE REPORTE DE TESTING

```markdown
# REPORTE DE TESTING - FASE 1

**Tester**: [Nombre]
**Fecha**: [YYYY-MM-DD HH:MM]
**Commit**: 9064bd4
**Entorno**: LOCAL / STAGING / PROD

## Resultados

| Prueba | Estado | Tiempo | Observaciones |
|--------|--------|--------|---------------|
| Prueba 1: Admin PENDING visible | ✅ PASS | 5 min | Sin issues |
| Prueba 2: Notificación funcionando | ✅ PASS | 3 min | Notificación recibida correctamente |
| Prueba 3: Panel sin bloqueo | ✅ PASS | 2 min | Panel completo visible |
| Prueba 4: Aprobación repartidor | ✅ PASS | 3 min | Aprobado exitosamente |

## Evidencias

- Screenshots: 4/4 ✅
- Queries SQL: 2/2 ✅
- Logs: Sin errores críticos ✅

## Issues Encontrados

[Ninguno / Describir aquí]

## Recomendación

☐ Aprobar para PROD
☐ Requiere correcciones
☐ Bloquear (issues críticos)

---
Firma: [Nombre]
```

---

## 🚀 PRÓXIMOS PASOS DESPUÉS DE TESTING

### Si Testing EXITOSO

1. **Marcar branch como tested**:
   ```bash
   git tag -a "v1.0-fase1-tested" -m "FASE 1 testing completado exitosamente"
   git push origin v1.0-fase1-tested
   ```

2. **Preparar merge a main**:
   - Crear PR desde `claude/fix-project-errors-PpBQS` a `main`
   - Adjuntar evidencias de testing
   - Esperar code review

3. **Deploy a PROD** (solo después de aprobación):
   ```bash
   # Backup DB producción
   ssh prod "cp /path/to/domi.db /path/to/domi.db.backup-$(date +%Y%m%d)"

   # Deploy
   git checkout main
   git pull
   # ... proceso de deploy según infraestructura
   ```

### Si Testing con Issues

1. **Documentar issues encontrados**
2. **Crear tickets para correcciones**
3. **Repetir testing después de fixes**

---

**FIN DE GUÍA DE TESTING**
