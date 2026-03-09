# Domiquerendona — Contexto actual del negocio

*Última actualización: 2026-03-08*

---

## 1. Qué es Domiquerendona

Domiquerendona es una infraestructura tecnológica para organizar y operar redes de domicilios. No es una app de pedidos al consumidor final: es la herramienta que usan los administradores, aliados y repartidores para coordinar su trabajo.

Hoy, la gran mayoría de redes de domicilios locales opera por WhatsApp. Alguien publica el pedido en un grupo, los repartidores responden en segundos, se genera un caos de mensajes y el coordinador tiene que leer todo en tiempo real para evitar errores. Domiquerendona reemplaza ese caos con un sistema estructurado que corre dentro de Telegram.

El sistema no compite con Rappi ni con PedidosYa. No intermedia entre el consumidor final y los negocios. Su propósito es organizar internamente la operación de una red de domicilios que ya existe o que quiere crecer de forma ordenada.

---

## 2. Problema que resuelve

Las redes de domicilios que operan por WhatsApp enfrentan problemas operativos recurrentes:

**Pedidos perdidos entre mensajes.** Un aliado publica el pedido en el grupo, pero el mensaje queda sepultado bajo otros mensajes y nadie lo toma. El pedido se pierde o llega tarde.

**Conflicto por aceptación de pedidos.** Dos repartidores dicen "yo lo llevo" al mismo tiempo. El coordinador tiene que definir manualmente quién se lo queda, lo cual genera roces y demoras.

**Datos del cliente expuestos.** El nombre, teléfono y dirección del cliente se publican en un grupo donde los ven todos los repartidores, aunque solo uno lleve el pedido. Es un riesgo de privacidad que muchos aliados no dimensionan.

**Falta de control operativo.** El coordinador no sabe en tiempo real qué repartidor tiene un pedido activo, si ya llegó al punto de recogida, si ya entregó o si hay algún problema. Todo depende de mensajes manuales.

**Falta de registro contable.** No hay un registro confiable de cuánto se ha ganado, cuánto se ha cobrado a cada aliado o repartidor, ni cuánto ha generado cada miembro del equipo. Todo queda en capturas de pantalla o en la memoria del coordinador.

**Dificultad para coordinar redes grandes.** Cuando la red crece a decenas de repartidores y aliados, la coordinación por WhatsApp se vuelve inmanejable. Se pierde control, se generan errores y el coordinador termina quemado.

---

## 3. Actores del sistema

**Plataforma (Admin de Plataforma).** Es el administrador global del sistema. Existe un único usuario con este rol. Tiene control total sobre la plataforma: puede aprobar o rechazar definitivamente a cualquier usuario, registrar ingresos externos para tener saldo operativo y gestionar la configuración global del sistema.

**Administrador local.** Gestiona un equipo de repartidores y aliados en su zona. Aprueba o rechaza miembros pendientes de su equipo, inactiva y reactiva usuarios, y aprueba recargas de saldo a sus miembros. Gana comisiones de los pedidos que generan sus aliados y de los que entregan sus repartidores. El rechazo definitivo de un usuario es exclusivo del Admin de Plataforma.

**Aliado.** Un negocio asociado (restaurante, tienda, droguería, etc.) que genera pedidos a través del sistema. Crea pedidos, consulta el estado de sus envíos, gestiona su agenda de clientes recurrentes y paga una comisión por cada pedido procesado exitosamente.

**Repartidor (Courier).** Entrega los pedidos. Recibe ofertas en tiempo real a través del bot, acepta o rechaza, navega al punto de recogida, confirma la llegada, recoge y entrega. Paga una comisión por cada pedido entregado exitosamente.

**Cliente final.** El destinatario del pedido. No tiene cuenta en el sistema; sus datos (nombre, teléfono, dirección) los gestiona el aliado o el administrador que crea el pedido. Sus datos no se revelan al repartidor hasta que el aliado confirma que el repartidor llegó al punto de recogida.

---

## 4. Cómo funciona un pedido

El flujo estándar de un pedido de aliado es el siguiente:

**Creación.** El aliado crea el pedido desde el bot: indica el punto de recogida, los datos del cliente, las instrucciones especiales y puede agregar un incentivo adicional para atraer repartidores más rápido.

**Cálculo de tarifa.** El sistema calcula la tarifa base usando Google Maps para estimar la distancia. El aliado confirma o ajusta la tarifa antes de publicar.

**Publicación a repartidores activos.** El pedido se publica a todos los repartidores activos de la red (de cualquier equipo), en orden y sin revelar los datos del cliente. Cada repartidor ve solo el barrio de destino, la tarifa y el punto de recogida.

**Aceptación.** El primer repartidor que acepta se asigna al pedido. En ese momento, el sistema cancela la oferta para los demás repartidores. Solo puede haber un repartidor asignado a la vez.

**Llegada al punto de recogida.** El sistema rastrea la ubicación del repartidor en tiempo real. Cuando se detecta que está a menos de 100 metros del punto de recogida, notifica al aliado que el repartidor llegó. El aliado confirma la llegada.

**Revelación de datos del cliente.** Solo después de que el aliado confirma que el repartidor llegó, el sistema revela al repartidor el nombre, teléfono y dirección exacta del cliente. Antes de ese momento, el repartidor solo sabe el barrio.

**Entrega.** El repartidor entrega el pedido y lo marca como entregado en el bot.

**Registro económico.** Al confirmar la entrega, el sistema registra automáticamente las comisiones correspondientes en el libro contable.

---

## 5. Cómo se financia la red

El modelo económico está basado en comisiones por servicio. Cada pedido exitoso genera dos cobros de $300 COP cada uno: uno al aliado y uno al repartidor.

**Pedido entregado — creado por aliado:**

- El aliado paga $300:
  - $200 van al administrador del aliado
  - $100 van a Plataforma
- El repartidor paga $300:
  - $200 van al administrador del repartidor
  - $100 van a Plataforma

Si el administrador del aliado y el administrador del repartidor son el mismo, ese administrador recibe $400. Si son administradores distintos, cada uno recibe $200 de sus propios miembros.

Si el administrador del aliado o del repartidor es la propia Plataforma, esta recibe los $300 completos (sin split).

**Pedido creado por admin local o admin de plataforma (pedido especial):**

El administrador que crea el pedido no paga comisión. El courier que entrega el pedido sí paga su comisión habitual de $300.

**Pedido expirado sin courier — creado por aliado:**

Si ningún repartidor acepta el pedido antes de que expire, el aliado paga $300 de todas formas. El destino de ese cobro sigue el mismo modelo: $200 al admin del aliado y $100 a Plataforma.

**Pedido expirado sin courier — creado por admin:**

Si un pedido especial de admin no es tomado por ningún repartidor, no se genera ningún cobro.

**El saldo es prepago.** Tanto los aliados como los repartidores necesitan tener saldo suficiente para que su pedido o su oferta sean válidos. El saldo lo recarga el administrador local a sus miembros, y el administrador local debe tener saldo propio para hacerlo. El admin de plataforma registra ingresos externos para fondear su propio saldo operativo.

---

## 6. Por qué conviene usar la plataforma

**Organización operativa.** El sistema reemplaza los grupos de WhatsApp caóticos con un flujo estructurado: un pedido a la vez, un repartidor asignado, estados claros.

**Trazabilidad completa.** Cada pedido queda registrado con timestamps: cuándo se creó, cuándo se publicó, cuándo fue aceptado, cuándo el repartidor llegó al pickup, cuándo se entregó.

**Agenda de clientes.** El aliado y el administrador pueden guardar sus clientes recurrentes con sus direcciones de entrega habituales. Al crear un nuevo pedido, solo seleccionan el cliente de la agenda y eligen la dirección, sin tener que escribir todo de nuevo.

**Protección de datos del cliente.** Los datos del cliente solo se revelan al repartidor después de confirmar que llegó al punto de recogida. Los demás repartidores de la red nunca ven esa información.

**Acceso a red de repartidores.** Los pedidos se publican automáticamente a todos los repartidores activos de la red. Si el equipo propio está ocupado, otros repartidores de la red pueden tomar el pedido. Más repartidores disponibles significa menos pedidos sin atender.

**Registro contable automático.** Cada transacción queda registrada en el libro contable del sistema. No es necesario llevar hojas de cálculo ni capturas de pantalla para saber cuánto se ha ganado.

**Incentivos para acelerar pedidos.** Si un pedido lleva más de 5 minutos sin ser aceptado, el sistema sugiere agregar un incentivo adicional para que sea más atractivo para los repartidores. El aliado puede agregar $1.500, $2.000, $3.000 o un monto libre.

**Optimización con rutas.** El sistema soporta rutas: un repartidor puede llevar varios pedidos en una sola salida. Esto reduce el costo por entrega y mejora el ingreso del repartidor.

---

## 7. Ejemplo económico simple de ruta

**Sin plataforma — pedidos por separado:**

Un aliado necesita enviar tres pedidos a distintos destinos. Si los trata como pedidos independientes, paga:

- Pedido 1: $9.600
- Pedido 2: $7.200
- Pedido 3: $5.000
- **Total: $21.800**

**Con plataforma — ruta combinada:**

El sistema agrupa los tres en una ruta con tarifa combinada de $20.000. La comisión de plataforma es $300.

- **Costo total: $20.300**
- **Ahorro neto: $1.500**

Domiquerendona no solo organiza la operación; también ayuda a reducir el costo total de los envíos cuando se usan rutas bien estructuradas.

---

## 8. Visión del proyecto

Domiquerendona busca construir una red colaborativa regional de domicilios, donde múltiples administradores locales participan con sus equipos y comparten la infraestructura sin perder autonomía sobre sus aliados y repartidores.

El objetivo no es reemplazar a los administradores locales ni centralizar el control. Es darle a cada administrador una red más grande y una herramienta más confiable para que su equipo trabaje mejor.

La plataforma crece cuando los administradores crecen. Cuando hay más aliados generando pedidos y más repartidores disponibles para tomarlos, todos los participantes de la red tienen más oportunidades de ingreso. Ese es el incentivo estructural del modelo cooperativo.
