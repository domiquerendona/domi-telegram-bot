# Guía de Despliegue — DEV y PROD en Railway

Fuente de verdad de despliegue del proyecto.

## Procesos del sistema

El proyecto tiene dos entry points distintos:

- Bot Telegram
  - Archivo: `Backend/main.py`
  - Arranque local: `python main.py`

- Web FastAPI
  - Archivo: `Backend/web_app.py`
  - Arranque local: `uvicorn web_app:app --reload --port 8000`

Diferencia:

- El bot Telegram registra handlers, jobs y hace polling.
- La app web expone la API FastAPI para el panel web.

Nota:

Actualmente el despliegue en Railway ejecuta solo el bot Telegram.
La aplicacion web puede ejecutarse localmente o desplegarse en un proceso separado si se habilita un panel web en produccion.

## Arquitectura de Ambientes

Hay **dos bots corriendo en Railway** de forma permanente:

| Ambiente | Rama git | Bot de Telegram | Base de datos |
|----------|----------|-----------------|---------------|
| **DEV** | `staging` | Bot de desarrollo | PostgreSQL DEV (separada) |
| **PROD** | `main` | Bot de producción | PostgreSQL PROD |

> **Regla de Oro:** DEV y PROD usan tokens de Telegram **distintos**. NUNCA el mismo `BOT_TOKEN` en ambos servicios al mismo tiempo.

---

## Flujo de trabajo para ver cambios

```
Implementar en local
  → git push origin staging
      ↓
  Railway auto-deploya el servicio DEV (rama staging)
      ↓
  Probar en el bot DEV de Telegram
      ↓ (validado)
  Mergear staging → main
      ↓
  Railway auto-deploya el servicio PROD (rama main)
```

**En resumen: para ver cualquier cambio en el bot DEV, hay que hacer `git push origin staging`.**
El push ya activa el deploy en Railway automáticamente — no hay paso manual adicional.

---

## Variables de Entorno

Cada servicio Railway tiene sus propias variables. Configurar en el dashboard de Railway:

### Servicio DEV (rama `staging`)

```
ENV=DEV
BOT_TOKEN=<token_bot_desarrollo>
ADMIN_USER_ID=<telegram_id_admin_dev>
DATABASE_URL=<postgresql_dev_url>
COURIER_CHAT_ID=<grupo_repartidores_dev>
RESTAURANT_CHAT_ID=<grupo_restaurantes_dev>
```

### Servicio PROD (rama `main`)

```
ENV=PROD
BOT_TOKEN=<token_bot_produccion>
ADMIN_USER_ID=<telegram_id_admin_prod>
DATABASE_URL=<postgresql_prod_url>
COURIER_CHAT_ID=<grupo_repartidores_prod>
RESTAURANT_CHAT_ID=<grupo_restaurantes_prod>
```

> **IMPORTANTE:** Railway toma las variables de su configuración. **NUNCA** agregar `.env` al repositorio.

---

## Verificar que el deploy fue exitoso

En los logs de Railway tras el deploy:

```
[ENV] Ambiente: DEV (o PROD)
[BOT] TOKEN fingerprint: hash=XXXXXXXX suffix=...XXXXX
[BOOT] Iniciando polling...
```

Los fingerprints del token deben ser **distintos** en DEV y PROD.

---

## Troubleshooting

### No veo mis cambios en el bot DEV

1. ¿Hiciste `git push origin staging`? → Verifica con `git log --oneline origin/staging`
2. ¿Railway deployó? → Revisar logs del servicio DEV en el dashboard de Railway
3. ¿El deploy falló? → Revisar si hay errores de compilación en los logs

### Error: "Conflict: terminated by other getUpdates request"

DEV y PROD están usando el **mismo token**. Verifica que cada servicio Railway tenga su propio `BOT_TOKEN`.

### Inicializar base de datos DEV desde cero

```bash
python3 -c "from db import init_db, force_platform_admin; init_db(); force_platform_admin()"
```

---

## Despliegue a Producción

Solo cuando los cambios estén **validados en DEV**:

```bash
git checkout main
git merge staging
git push origin main
```

Railway auto-deploya PROD al detectar el push en `main`.
