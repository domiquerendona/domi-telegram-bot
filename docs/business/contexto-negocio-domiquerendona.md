# Domiquerendona — Contexto actual del negocio

*Última actualización: 2026-03-11*

---

## 1. Qué es Domiquerendona

Domiquerendona es una infraestructura tecnológica para organizar y operar redes de domicilios. No es una app de pedidos al consumidor final: es la herramienta que usan los administradores, aliados y repartidores para coordinar su trabajo.

Hoy, la gran mayoría de redes de domicilios locales opera por WhatsApp. Alguien publica el pedido en un grupo, los repartidores responden en segundos, se genera un caos de mensajes y el coordinador tiene que leer todo en tiempo real para evitar errores. Domiquerendona reemplaza ese caos con un sistema estructurado que corre dentro de Telegram.

El sistema no compite con Rappi ni con PedidosYa. No intermedia entre el consumidor final y los negocios. Su propósito es organizar internamente la operación de una red de domicilios que ya existe o que quiere crecer de forma ordenada.

---

## 2. Frase corta de 10 segundos

**Para administradores:**
"Domiquerendona es el sistema que reemplaza el grupo de WhatsApp: organiza tus pedidos, protege los datos de tus clientes y registra cada peso que se mueve en tu operación."

**Para aliados:**
"Con Domiquerendona tus pedidos se gestionan solos: el sistema asigna el repartidor, rastrea la entrega y guarda a tus clientes para la próxima vez."

**Para repartidores:**
"Domiquerendona te llega las ofertas directo al celular, te dice adónde recoger sin revelar al cliente hasta que llegues, y registra cada carrera que haces."

---

## 3. Problema que resuelve

Las redes de domicilios que operan por WhatsApp enfrentan problemas operativos recurrentes:

**Pedidos perdidos entre mensajes.** Un aliado publica el pedido en el grupo, pero el mensaje queda sepultado bajo otros mensajes y nadie lo toma. El pedido se pierde o llega tarde.

**Conflicto por aceptación de pedidos.** Dos repartidores dicen "yo lo llevo" al mismo tiempo. El coordinador tiene que definir manualmente quién se lo queda, lo cual genera roces y demoras.

**Datos del cliente expuestos.** El nombre, teléfono y dirección del cliente se publican en un grupo donde los ven todos los repartidores, aunque solo uno lleve el pedido. Es un riesgo de privacidad que muchos aliados no dimensionan.

**Falta de control operativo.** El coordinador no sabe en tiempo real qué repartidor tiene un pedido activo, si ya llegó al punto de recogida, si ya entregó o si hay algún problema. Todo depende de mensajes manuales.

**Falta de registro contable.** No hay un registro confiable de cuánto se ha ganado, cuánto se ha cobrado a cada aliado o repartidor, ni cuánto ha generado cada miembro del equipo. Todo queda en capturas de pantalla o en la memoria del coordinador.

**Dificultad para coordinar redes grandes.** Cuando la red crece a decenas de repartidores y aliados, la coordinación por WhatsApp se vuelve inmanejable. Se pierde control, se generan errores y el coordinador termina quemado.

---

## 4. Actores del sistema

**Plataforma (Admin de Plataforma).** Es el administrador global del sistema. Existe un único usuario con este rol. Tiene control total sobre la plataforma: puede aprobar o rechazar definitivamente a cualquier usuario, registrar ingresos externos para tener saldo operativo y gestionar la configuración global del sistema.

**Administrador local.** Gestiona un equipo de repartidores y aliados en su zona. Aprueba o rechaza miembros pendientes de su equipo, inactiva y reactiva usuarios, y aprueba recargas de saldo a sus miembros. Gana comisiones de los pedidos que generan sus aliados y de los que entregan sus repartidores. El rechazo definitivo de un usuario es exclusivo del Admin de Plataforma.

**Aliado.** Un negocio asociado (restaurante, tienda, droguería, etc.) que genera pedidos a través del sistema. Crea pedidos, consulta el estado de sus envíos, gestiona su agenda de clientes recurrentes y paga una comisión por cada pedido procesado exitosamente.

**Repartidor (Courier).** Entrega los pedidos. Recibe ofertas en tiempo real a través del bot, acepta o rechaza, navega al punto de recogida, confirma la llegada, recoge y entrega. Paga una comisión por cada pedido entregado exitosamente.

**Cliente final.** El destinatario del pedido. No tiene cuenta en el sistema; sus datos (nombre, teléfono, dirección) los gestiona el aliado o el administrador que crea el pedido. Sus datos no se revelan al repartidor hasta que el aliado confirma que el repartidor llegó al punto de recogida.

---

## 5. Cómo funciona un pedido

El flujo estándar de un pedido de aliado es el siguiente:

**Creación.** El aliado crea el pedido desde el bot: indica el punto de recogida, los datos del cliente, las instrucciones especiales y puede agregar un incentivo adicional para atraer repartidores más rápido.

**Cálculo de tarifa.** El sistema calcula la tarifa base usando Google Maps para estimar la distancia. El aliado confirma o ajusta la tarifa antes de publicar.

**Publicación a repartidores activos.** El pedido se publica a todos los repartidores activos de la red (de cualquier equipo), en orden y sin revelar los datos del cliente. Cada repartidor ve solo el barrio de destino, la tarifa y el punto de recogida.

**Aceptación.** El primer repartidor que acepta se asigna al pedido. En ese momento, el sistema cancela la oferta para los demás repartidores. Solo puede haber un repartidor asignado a la vez.

**Llegada al punto de recogida.** El sistema rastrea la ubicación del repartidor en tiempo real. Cuando se detecta que está a menos de 100 metros del punto de recogida, notifica al aliado que el repartidor llegó. El aliado confirma la llegada.

**Revelación de datos del cliente.** Solo después de que el aliado confirma que el repartidor llegó, el sistema revela al repartidor el nombre, teléfono y dirección exacta del cliente. Antes de ese momento, el repartidor solo sabe el barrio.

**Entrega.** El repartidor entrega el pedido y lo marca como entregado en el bot.

**Registro económico.** Al confirmar la entrega, el sistema registra automáticamente las comisiones correspondientes en el libro contable.

### Ciclo de pedido actualizado

0 min → pedido publicado  
5 min → sugerencia de incentivo adicional  
10 min → reintento automático del mercado (1/3)
20 min → reintento automático del mercado (2/3)
30 min → reintento automático del mercado (3/3)
40 min → cancelación automática sin costo si nadie acepta

### Cancelación del aliado

≤2 minutos desde creación y sin repartidor asignado → cancelación sin costo  
>2 minutos desde creación y sin repartidor asignado → cobro de $300  
Con repartidor ya asignado (`ACCEPTED`) → cobro de $800 ($600 repartidor / $200 plataforma)  
Cancelación automática final tras 3 reintentos del mercado → sin costo
Pedidos creados por administrador (`ally_id = None`) → misma ventana; el cobro recae sobre el admin creador  

Todo queda registrado. Ningún pedido se pierde. Ningún repartidor acepta dos veces el mismo pedido. Los datos del cliente están protegidos.

---

## 5B. Enlace de pedido directo al cliente (PENDIENTE DE IMPLEMENTACIÓN)

El aliado puede compartir un enlace único con sus clientes para que diligencie los datos del domicilio sin pasar por el bot. El aliado recibe la solicitud en Telegram y la convierte en pedido o la guarda en su agenda.

### Qué puede hacer el cliente con ese enlace

1. **Identificación por teléfono (siempre primero).** El primer paso es siempre el número de teléfono. El sistema verifica si ese número ya existe en la agenda de ese aliado antes de hacer cualquier otra cosa.

2. **Cliente reconocido.** Si el teléfono ya existe, el sistema muestra sus direcciones guardadas. El cliente puede seleccionar una dirección existente o agregar una nueva.

3. **Cliente nuevo.** Si el teléfono no existe, el cliente ingresa su nombre y una dirección de entrega.

4. **Confirmación de ubicación en mapa.** Toda dirección nueva (de cliente reconocido o nuevo) debe confirmarse en mapa antes de continuar. Sin coordenadas confirmadas no hay cotización exacta.

5. **Cotización desglosada.** Una vez confirmada la ubicación, el sistema calcula y presenta la cotización con sus componentes separados:
   - Valor real del domicilio (tarifa calculada por distancia)
   - Subsidio del aliado (descuento fijo que el aliado define para sus clientes)
   - Incentivo adicional del cliente (monto opcional que el cliente puede agregar para atraer repartidores más rápido)
   - Total a pagar por el cliente (valor real − subsidio + incentivo)

6. **Subsidio del aliado.** El aliado configura cuánto desea subsidiar del domicilio a sus clientes. Ese monto se descuenta del valor que ve el cliente en la cotización.

7. **Incentivo adicional del cliente.** El cliente puede agregar voluntariamente un monto adicional para acelerar la asignación de repartidor.

8. **Bandeja temporal.** La solicitud no crea un pedido automáticamente. Entra a una bandeja transitoria y el aliado decide en Telegram qué hacer: convertir en pedido, guardar en agenda o ignorar.

### Por qué este flujo importa

Los aliados que tienen clientes recurrentes (domicilios a residencias o empresas habituales) pasan mucho tiempo repitiendo los mismos datos en el bot. El enlace de pedido elimina ese trabajo: el cliente diligencia sus propios datos, el aliado solo confirma.

A diferencia de crear el pedido directamente desde el formulario web, este diseño mantiene al aliado en control: él decide si el domicilio se crea o no. No hay pedidos automáticos sin intervención del aliado.

### Relación con la agenda de clientes

El sistema de enlace de pedido no es independiente de la agenda. Es el punto de entrada externo a la misma agenda que el aliado ya gestiona en el bot. Cuando el aliado acepta la solicitud:

- Si el cliente era nuevo, queda registrado en la agenda del aliado.
- Si el cliente ya existía, su dirección puede actualizarse o complementarse.
- El pedido que se cree tendrá los datos del cliente vinculados a su registro de agenda, no como texto suelto.

### Implementación por fases

Este sistema se construirá paso a paso, comenzando por la infraestructura mínima (token por aliado, endpoint público, notificación Telegram) y avanzando hacia la cotización y el subsidio en pasos posteriores.

---

## 6. Cómo se financia la red

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

Si ningún repartidor acepta el pedido después de 3 reintentos automáticos del mercado, no se genera ningún cobro.

**Pedido expirado sin courier — creado por admin:**

Si un pedido especial de admin no es tomado por ningún repartidor después de 3 reintentos automáticos del mercado, no se genera ningún cobro.

**El saldo es prepago.** Tanto los aliados como los repartidores necesitan tener saldo suficiente para que su pedido o su oferta sean válidos. El saldo lo recarga el administrador local a sus miembros, y el administrador local debe tener saldo propio para hacerlo. El admin de plataforma registra ingresos externos para fondear su propio saldo operativo.

---

## 7. El valor para cada actor

**Para el administrador local:** sistema de gestión centralizado, registro contable automático, control sobre su equipo, comisiones claras y acceso a una red más amplia de aliados y repartidores que amplía las oportunidades de su equipo.

**Para el aliado:** menos caos operativo, agenda de clientes reutilizable, trazabilidad de cada pedido, acceso a más repartidores disponibles y protección de los datos de sus clientes.

**Para el repartidor:** ofertas organizadas, claridad sobre la tarifa antes de aceptar, protección del cliente hasta confirmar llegada y registro de cada carrera.

### Beneficios resumidos por actor

#### Administrador local

- Sistema de gestión centralizado que reemplaza el caos de WhatsApp
- Registro contable automático: sabe exactamente cuánto ha ganado y cuánto ha movido
- Control total sobre su equipo: aprobaciones, recargas, activaciones
- Comisiones claras y automáticas por cada pedido de sus aliados y cada entrega de sus repartidores
- Acceso a una red más amplia que amplía las oportunidades de su equipo sin que pierda propiedad sobre él
- Herramientas de gestión de pedidos especiales (puede crear pedidos propios sin pagar comisión de aliado)
- Agenda de clientes de entrega con direcciones guardadas

#### Aliado

- Creación de pedidos rápida y organizada
- Agenda de clientes recurrentes con direcciones guardadas: menos tiempo escribiendo, más tiempo atendiendo
- Trazabilidad en tiempo real: sabe exactamente en qué estado está cada pedido
- Protección de datos del cliente: los datos solo se revelan al repartidor confirmado, no a toda la red
- Acceso a todos los repartidores activos de la red, no solo a los del equipo inmediato
- Incentivos para acelerar pedidos sin respuesta
- Optimización de costos a través de rutas combinadas

#### Repartidor

- Ofertas organizadas y claras: tarifa visible antes de aceptar, sin negociaciones
- Privacidad del cliente protegida: no recibe los datos hasta confirmar llegada al pickup
- Registro automático de cada carrera
- Acceso a pedidos de toda la red, no solo de los aliados de su equipo inmediato
- Rutas combinadas que maximizan el ingreso por salida
- Flujo claro: oferta → aceptar → navegar → llegada confirmada → entregar → registrar

---

## 8. La red cooperativa

Domiquerendona no opera con equipos aislados. La red es compartida: cualquier repartidor activo puede tomar pedidos de cualquier aliado, sin importar a qué administrador pertenezca cada uno.

Esto no es una amenaza para los administradores; es el mecanismo que hace que la red tenga valor. Si todos los aliados y repartidores solo interactuaran dentro de su propio equipo, la plataforma no sería más útil que un grupo de WhatsApp privado.

La red cooperativa permite que en momentos de alta demanda los pedidos sean atendidos aunque el equipo propio esté ocupado, y que en momentos de baja actividad los repartidores encuentren trabajo en pedidos de otros aliados de la red. Todos ganan más cuando la red es más activa.

### Pregunta más común del administrador

**"¿Y si mis repartidores empiezan a trabajar con otros aliados de la red y me dejan de traer pedidos a mí?"**

Esta es la pregunta más frecuente, y tiene una respuesta clara.

El repartidor puede, y debe, trabajar en toda la red. Eso es parte del diseño. Pero la comisión del repartidor siempre va al administrador que lo vinculó. Si el repartidor A, que pertenece al equipo del administrador 1, entrega un pedido de un aliado del administrador 2, el administrador 1 recibe su $200 de comisión sobre ese repartidor, y el administrador 2 recibe su $200 de comisión sobre ese aliado.

El repartidor no "se va" a otro equipo cuando toma un pedido de otro aliado. Sigue siendo del equipo de su administrador. Su administrador sigue ganando por cada entrega que haga, venga el pedido de donde venga.

Lo que sí podría preocupar es la salida definitiva de un repartidor: que el repartidor decida cambiarse de administrador. Pero eso no ocurre automáticamente por trabajar en la red compartida; requiere una decisión activa. Y si un repartidor decide cambiarse, la razón suele ser una diferencia de trato o de condiciones con su administrador actual, no el hecho de haber interactuado con aliados de otros equipos.

En resumen: la red compartida amplía las oportunidades del repartidor y, por extensión, los ingresos de su administrador. No hay motivo estructural para que eso debilite la relación entre ambos.

### ¿Qué pasa si un aliado o repartidor ya no quiere seguir con su administrador actual?

Esta pregunta aparece tarde o temprano en cualquier red con múltiples administradores, y tiene una respuesta clara.

Domiquerendona no considera a las personas propiedad de ningún administrador. Un aliado o un repartidor que desee cambiarse de equipo puede solicitarlo. La plataforma reconoce esa libertad como un principio de gobernanza, no como una excepción.

El cambio se organiza de forma ordenada: no ocurre de manera inmediata si hay operaciones en curso, y existe un periodo de transición para que todo quede cerrado correctamente antes de que el nuevo vínculo entre en vigor.

Desde que el cambio se hace efectivo, las comisiones futuras de ese miembro pasan al nuevo administrador. Las operaciones históricas y los registros contables pasados no se modifican.

Esta regla tiene una consecuencia directa: obliga a todos los administradores a cuidar bien a su equipo. Un administrador que trata bien a sus aliados y repartidores, que recarga a tiempo y que apoya su operación, no necesita preocuparse por la movilidad. Su equipo se queda porque quiere quedarse. Eso crea una red más sana para todos.

---

## 9. Ejemplo económico simple de ruta

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

## 10. Mensaje clave para administradores

**"Domiquerendona no viene a quitarte tu equipo; viene a darte una red más grande para que tu equipo trabaje más."**

Este es el mensaje central para un administrador que duda. No es solo un argumento de venta: es la descripción exacta de cómo funciona el sistema.

Un administrador con 5 repartidores que opera en aislamiento tiene capacidad para atender los pedidos de sus propios aliados y nada más. Un administrador con los mismos 5 repartidores en la red Domiquerendona tiene acceso a todos los pedidos de todos los aliados de la red. Sus repartidores tienen más trabajo disponible. Sus aliados tienen más repartidores disponibles cuando los suyos están ocupados.

El administrador no cede nada de lo que ya tiene. Gana acceso a más.

---

## 11. Visión del proyecto

Domiquerendona busca construir una red colaborativa regional de domicilios, donde múltiples administradores locales participan con sus equipos y comparten la infraestructura sin perder autonomía sobre sus aliados y repartidores.

El objetivo no es reemplazar a los administradores locales ni centralizar el control. Es darle a cada administrador una red más grande y una herramienta más confiable para que su equipo trabaje mejor.

La plataforma crece cuando los administradores crecen. Cuando hay más aliados generando pedidos y más repartidores disponibles para tomarlos, todos los participantes de la red tienen más oportunidades de ingreso. Ese es el incentivo estructural del modelo cooperativo.

### Principio fundacional e inmutable

Domiquerendona nació de la idea de organizar el trabajo de los repartidores independientes, sistematizar los procesos de la operación y crear una red donde el trabajo bien coordinado permita ingresos justos.

La base del proyecto no es la monopolización. Domiquerendona busca ser una plataforma descentralizada que entrega herramientas tecnológicas a repartidores y administradores independientes. Todos ellos forman parte de la red que la plataforma pretende construir.

La visión de Domiquerendona es una red muy grande donde la ganancia no quede concentrada en un solo actor, sino donde el trabajo de todos haga crecer la red completa. El propósito es que haya más trabajo para los repartidores, que los aliados siempre tengan acceso a repartidores verificados y calificados, y que toda persona que use la red encuentre más tranquilidad, orden y confianza en el servicio.

El papel de los administradores es central en esa visión. Cada administrador es responsable de su equipo, y por eso el éxito de la red depende del orden y la disciplina con que los administradores filtran ingresos, cuidan a sus miembros y ayudan a sacar de la red a las personas conflictivas, dañinas o inútiles para el propósito colectivo. La plataforma provee seguimiento y registros precisamente para que los administradores puedan cumplir ese trabajo con criterio y evidencia.

Un administrador que solo piensa en su beneficio, que quiere todo para sí o que no desea el progreso de los demás, no encaja en el ideal de Domiquerendona. Tampoco encaja la idea de ser dueño de ciudades o territorios. Domiquerendona pretende ser una red cooperativa donde el trabajo de todos beneficie a todos.

Los pilares de Domiquerendona son el respeto, el progreso y la cooperación. Quien entra al sistema debe entender que la plataforma existe para ayudarle a prestar un mejor servicio a sus clientes, con más seguridad gracias a los filtros humanos de la red, y con más eficacia gracias al trabajo diligente de repartidores calificados.
