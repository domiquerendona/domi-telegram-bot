# Estrategia de Testing Vigente

Fuente de referencia vigente para pruebas del proyecto.

## 1. Cómo correr los tests actuales

Ejecutar desde la raíz del repositorio:

```bash
python -m unittest \
tests.test_web_admin_services \
tests.test_dashboard_services \
tests.test_profile_change_services \
tests.test_main_notification_services \
tests.test_callback_compatibility
```

Compilación mínima recomendada de backend:

```bash
python -m py_compile Backend/main.py Backend/web_app.py Backend/services.py Backend/db.py Backend/order_delivery.py Backend/profile_changes.py
```

## 2. Qué cubren los tests actuales

- `tests.test_web_admin_services`
  - Servicios extraídos del panel web administrativo
  - balances, pricing, cancelación y resolución de soporte

- `tests.test_dashboard_services`
  - métricas agregadas del dashboard web

- `tests.test_profile_change_services`
  - aplicación de cambios de perfil movidos a `services.py` y `db.py`

- `tests.test_main_notification_services`
  - helpers de notificación usados por `Backend/main.py`

- `tests.test_callback_compatibility`
  - compatibilidad temporal entre callbacks legacy con `:` y estándar con `_`

## 3. Cómo agregar nuevos tests

Reglas:

- Los tests nuevos deben vivir en `tests/`.
- Cada archivo debe cubrir un dominio o cambio concreto, no una mezcla amplia de flujos.
- Si un cambio extrae lógica desde `main.py`, `profile_changes.py` o `web/api/*`, debe acompañarse de al menos una prueba mínima de regresión sobre el helper o servicio nuevo.
- Preferir pruebas pequeñas y verificables sobre servicios/helpers antes que depender de flujos gigantes del bot.

## 4. Regla de testing para cambios estructurales

Si el cambio modifica cualquiera de estos temas:

- arquitectura
- callbacks
- entrypoints
- persistencia
- despliegue
- rutas del panel web

debe incluir:

1. compilación de los archivos tocados
2. actualización documental si cambia la estructura o reglas
3. pruebas mínimas de regresión cuando el cambio altere comportamiento verificable

## 5. Alcance y límites

- Esta estrategia describe el estado actual de testing automatizado.
- No reemplaza validación manual en Telegram o panel web cuando el cambio toca UX, wiring o integraciones externas.
- `Backend/TESTING.md` queda como documento obsoleto de una fase antigua y no debe usarse como guía vigente.
