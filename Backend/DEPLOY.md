# Guía de Despliegue - Separación DEV/PROD

## Problema Resuelto

**Error:** `telegram.error.Conflict: terminated by other getUpdates request`

**Causa:** DEV (PC local) y PROD (Railway) usaban el mismo `BOT_TOKEN`, causando conflicto cuando ambos intentaban obtener actualizaciones de Telegram simultáneamente.

**Solución:** Separación completa de tokens y ambientes mediante variable `ENV`.

---

## Configuración DEV (Local)

### 1. Crear Bot de Desarrollo

1. Abre Telegram y habla con [@BotFather](https://t.me/BotFather)
2. Crea un nuevo bot: `/newbot`
3. Sigue las instrucciones y guarda el token (será tu `BOT_TOKEN` de DEV)
4. **IMPORTANTE:** Este bot es SOLO para desarrollo, NO es el bot de producción

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env
nano .env
```

Configurar:
```bash
ENV=LOCAL
BOT_TOKEN=<tu_token_de_bot_de_desarrollo>
ADMIN_USER_ID=<tu_telegram_user_id>
DB_PATH=domiquerendona_dev.db  # Base de datos separada para DEV
```

### 3. Instalar Dependencias

```bash
pip install python-dotenv
pip install -r requirements.txt
```

### 4. Ejecutar en Local

```bash
python main.py
```

**Logs esperados:**
```
[ENV] Ambiente: LOCAL - .env cargado
[BOT] TOKEN fingerprint: hash=a1b2c3d4 suffix=...XYZ123
[BOT] Ambiente: LOCAL
[BOOT] Iniciando polling...
```

---

## Configuración PROD (Railway)

### 1. Variables de Entorno en Railway

En el dashboard de Railway, configura:

```
ENV=PROD
BOT_TOKEN=<tu_token_de_bot_de_producción>
ADMIN_USER_ID=<admin_telegram_id>
COURIER_CHAT_ID=<id_grupo_repartidores>
RESTAURANT_CHAT_ID=<id_grupo_restaurantes>
```

**IMPORTANTE:**
- NO agregues archivo `.env` al repositorio
- Railway tomará las variables de su configuración
- El código NO cargará `.env` cuando `ENV=PROD`

### 2. Verificar Logs en Railway

Después del despliegue, verifica los logs:

```
[ENV] Ambiente: PROD - usando variables de entorno del sistema (Railway/PROD)
[BOT] TOKEN fingerprint: hash=x9y8z7w6 suffix=...ABC789
[BOT] Ambiente: PROD
[BOOT] Iniciando polling...
```

**Verificación:** El fingerprint del token debe ser DIFERENTE al de DEV.

---

## Verificación de Separación

### ✅ Configuración Correcta

**DEV:**
```
[ENV] Ambiente: LOCAL
[BOT] TOKEN fingerprint: hash=a1b2c3d4 suffix=...XYZ123
```

**PROD:**
```
[ENV] Ambiente: PROD
[BOT] TOKEN fingerprint: hash=x9y8z7w6 suffix=...ABC789
```

Los fingerprints son DIFERENTES → ✅ OK

### ❌ Configuración Incorrecta

Si los fingerprints son IGUALES:
```
DEV:  hash=a1b2c3d4 suffix=...XYZ123
PROD: hash=a1b2c3d4 suffix=...XYZ123  ← ❌ MISMO TOKEN
```

Resultado: Error `Conflict: terminated by other getUpdates request`

---

## Troubleshooting

### Error: "Conflict: terminated by other getUpdates request"

**Solución:**
1. Verifica que DEV y PROD usen tokens diferentes
2. Revisa logs y compara fingerprints
3. Asegúrate que Railway tiene `ENV=PROD`
4. Verifica que `.env` local tenga `ENV=LOCAL`

### Error: "Falta BOT_TOKEN en variables de entorno"

**En LOCAL:**
- Verifica que `.env` existe y contiene `BOT_TOKEN`
- Verifica que `python-dotenv` está instalado

**En PROD (Railway):**
- Verifica que configuraste `BOT_TOKEN` en variables de Railway
- Asegúrate que no esté vacío

---

## Seguridad

- `.env` está en `.gitignore` y NUNCA debe subirse al repositorio
- Los tokens nunca se imprimen completos en logs (solo fingerprints)
- Cada ambiente (DEV/PROD) usa su propio token y base de datos

---

## Resumen

| Ambiente | ENV | BOT_TOKEN | .env | DB |
|----------|-----|-----------|------|-----|
| DEV (Local) | LOCAL | Token DEV | ✅ Carga | domiquerendona_dev.db |
| PROD (Railway) | PROD | Token PROD | ❌ NO carga | domiquerendona.db |

**Regla de Oro:** NUNCA uses el mismo `BOT_TOKEN` en DEV y PROD al mismo tiempo.
