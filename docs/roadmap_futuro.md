# Roadmap Futuro

Fecha base: 2026-04-04
Rama base: staging
Objetivo: concentrar mejoras futuras importantes que aun no conviene activar por completo en la etapa actual de red pequena.

## Estado actual

La operacion sigue en etapa temprana:

- pocos aliados activos
- pocos repartidores activos
- volumen aun bajo y no sostenido

Decision vigente:

- mantener el flujo simple
- evitar UI que abrume al aliado
- priorizar mensajes claros, confirmaciones utiles y ayudas opcionales

## Mejoras importantes para activar despues

### 1. Semaforo de demanda mas exigente

Hoy el semaforo esta suavizado para no sonar alarmista con una red pequena.

Activar despues:

- umbrales mas estrictos segun escasez real
- recomendaciones mas precisas por zona y horario
- mensajes menos conservadores cuando exista mas liquidez de mercado

Referencia tecnica actual:

- `build_offer_demand_preview(...)` en `Backend/services.py`

### 2. Incentivo inteligente asistido mas completo

Hoy solo existe sugerencia discreta y un boton simple para aplicar la recomendacion en previews pre-confirmacion.

Activar despues:

- mas opciones contextuales de incentivo
- sugerencia exacta segun demanda real del momento
- posibilidad de usar el incentivo sugerido tambien en T+5 con logica unificada

Referencias tecnicas actuales:

- `build_offer_suggestion_button_row(...)` en `Backend/handlers/common.py`
- callbacks `pedido_inc_*`, `ruta_inc_*`, `admin_pedido_inc_*`

### 3. Estado del mercado en vivo post-publicacion

Hoy solo se muestra un estado simple y tranquilizador:

- busqueda en curso
- ciclo actual del mercado
- aclaracion de cancelacion sin cargo al expirar

Activar despues:

- mas detalle de progreso por ciclo
- resumen del mercado en vivo post-publicacion
- visibilidad de relanzamientos automaticos e incentivo recomendado

Referencia tecnica actual:

- `build_market_launch_status_text(...)` en `Backend/order_delivery.py`

### 5. Borrador persistido en BD (retomar pedido tras cerrar el bot)

Los flujos de creacion de pedido y ruta no sobreviven reinicios del proceso ni cierres de sesion del usuario. Si el usuario cierra Telegram a mitad del flujo, pierde todo y debe empezar de nuevo.

Activar despues:

- Nueva tabla `order_drafts` que guarda el estado parcial (user_data del flujo) en BD.
- Al iniciar `/nuevo_pedido` o `/nueva_ruta`, verificar si hay un borrador en curso: "Tienes un pedido en borrador. Retomar o empezar nuevo?"
- Al retomar: restaurar user_data desde BD y mostrar el paso donde el usuario se quedó.
- Al completar o cancelar: borrar el borrador.
- Protege también contra reinicios del bot en Railway con pedidos a mitad de flujo.

Aplica a los tres flujos: `nuevo_pedido_conv`, `nueva_ruta_conv`, `admin_pedido_conv`.

Referencia tecnica: los flujos ya usan `PicklePersistence` para `user_data`, pero ese archivo se pierde si Railway recrece el contenedor sin volumen persistente. La solucion BD es mas robusta.

### 4. Tarifa dinamica asistida o automatica

Todavia no conviene activarla de forma fuerte.

Activar despues:

- version asistida primero
- version automatica solo con topes, trazabilidad y datos reales suficientes

## Gatillo sugerido para reabrir este roadmap

Revisar estas mejoras cuando se cumpla de forma sostenida que:

- hay mas pedidos concurrentes y ya no son casos aislados
- hay mas aliados y repartidores activos al mismo tiempo
- el semaforo actual empieza a quedarse corto o demasiado conservador
- el equipo ya necesite mas automatizacion para acelerar toma y asignacion

## Regla operativa

Antes de activar cualquiera de estas mejoras:

- validar primero en `staging`
- documentar el cambio en `CLAUDE.md`
- actualizar `docs/callback_governance_2026-03-12.md` si cambia algun callback
- dejar evidencia visible si el flujo afectado es critico
