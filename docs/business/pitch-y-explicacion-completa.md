# Domiquerendona — Pitch y explicación completa

*Última actualización: 2026-03-08*

---

## 1. Frase corta de 10 segundos

**Para administradores:**
> "Domiquerendona es el sistema que reemplaza el grupo de WhatsApp: organiza tus pedidos, protege los datos de tus clientes y registra cada peso que se mueve en tu operación."

**Para aliados:**
> "Con Domiquerendona tus pedidos se gestionan solos: el sistema asigna el repartidor, rastrea la entrega y guarda a tus clientes para la próxima vez."

**Para repartidores:**
> "Domiquerendona te llega las ofertas directo al celular, te dice adónde recoger sin revelar al cliente hasta que llegues, y registra cada carrera que haces."

---

## 2. Explicación completa de 5–7 minutos

### El problema de WhatsApp

Hoy, la mayoría de redes de domicilios locales en Colombia operan por WhatsApp. El modelo es conocido: el aliado escribe el pedido en el grupo, los repartidores responden "yo lo cojo", el coordinador tiene que leer todo en tiempo real, resolver quién se queda el pedido, confirmar que fue entregado y registrar el cobro manualmente.

Esto funciona cuando la red es pequeña y el volumen es bajo. Cuando crece, falla. Los pedidos se pierden entre mensajes. Dos repartidores aceptan el mismo pedido y hay conflicto. El coordinador se satura. Los datos del cliente —nombre, teléfono, dirección— quedan expuestos en el grupo para que los vean todos. Y al final del día, nadie sabe con certeza cuánto se ganó ni cuánto se cobró a quién.

### La solución

Domiquerendona es un sistema de coordinación de domicilios que corre dentro de Telegram. No es una app para el consumidor final; es la herramienta que usa la red interna —administradores, aliados y repartidores— para operar de forma ordenada.

El sistema reemplaza el grupo de WhatsApp con un flujo estructurado:

- El aliado crea el pedido desde el bot: ingresa los datos del cliente, el punto de recogida, la tarifa calculada automáticamente y, si quiere, un incentivo adicional para atraer repartidores más rápido.
- El sistema publica el pedido a todos los repartidores activos de la red, sin revelar los datos del cliente. El repartidor solo ve el barrio de destino, la tarifa y el punto de recogida.
- El primer repartidor que acepta se asigna. Los demás ya no ven la oferta.
- El sistema rastrea la ubicación del repartidor en tiempo real. Cuando está a menos de 100 metros del punto de recogida, notifica al aliado que ya llegó.
- El aliado confirma la llegada. En ese momento —y solo en ese momento— el sistema revela al repartidor el nombre, teléfono y dirección exacta del cliente.
- El repartidor entrega y lo marca en el bot.
- El sistema registra automáticamente las comisiones correspondientes en el libro contable.

Todo queda registrado. Ningún pedido se pierde. Ningún repartidor acepta dos veces el mismo pedido. Los datos del cliente están protegidos.

### Los actores

**La plataforma** provee la infraestructura tecnológica y establece las reglas generales. Hay un único administrador de plataforma.

**Los administradores locales** coordinan sus equipos: aprueban aliados y repartidores, gestionan recargas de saldo y hacen seguimiento a la operación de su zona. Ganan comisiones de los pedidos que generan sus aliados y de las entregas que hacen sus repartidores.

**Los aliados** son los negocios: restaurantes, tiendas, droguerías. Crean pedidos, consultan el estado de sus envíos y administran su agenda de clientes recurrentes.

**Los repartidores** reciben ofertas en tiempo real, aceptan, navegan al pickup y entregan. Todo desde el bot, sin necesidad de estar en un grupo de WhatsApp.

**El cliente final** recibe su pedido. No tiene cuenta en el sistema; sus datos los gestiona el aliado o el administrador que crea el pedido.

### El modelo económico

El sistema opera con saldo prepago. Los aliados y repartidores deben tener saldo disponible para que sus pedidos y ofertas sean válidos. El administrador local recarga ese saldo a sus miembros.

Cada pedido entregado genera dos comisiones de $300 COP:

- El aliado paga $300: $200 van al administrador del aliado, $100 a la plataforma.
- El repartidor paga $300: $200 van al administrador del repartidor, $100 a la plataforma.

Si el administrador del aliado y el del repartidor son el mismo, recibe $400. Si son distintos, cada uno recibe $200 de sus propios miembros.

El administrador no pierde comisiones cuando sus miembros interactúan con miembros de otros equipos. Las comisiones siempre siguen el vínculo.

### El valor para cada actor

**Para el aliado:** menos caos operativo, agenda de clientes reutilizable, trazabilidad de cada pedido, acceso a más repartidores disponibles y protección de los datos de sus clientes.

**Para el repartidor:** ofertas organizadas, claridad sobre la tarifa antes de aceptar, protección del cliente hasta confirmar llegada y registro de cada carrera.

**Para el administrador local:** sistema de gestión centralizado, registro contable automático, control sobre su equipo, comisiones claras y acceso a una red más amplia de aliados y repartidores que amplía las oportunidades de su equipo.

### La red cooperativa

Domiquerendona no opera con equipos aislados. La red es compartida: cualquier repartidor activo puede tomar pedidos de cualquier aliado, sin importar a qué administrador pertenezca cada uno.

Esto no es una amenaza para los administradores; es el mecanismo que hace que la red tenga valor. Si todos los aliados y repartidores solo interactuaran dentro de su propio equipo, la plataforma no sería más útil que un grupo de WhatsApp privado.

La red cooperativa permite que en momentos de alta demanda los pedidos sean atendidos aunque el equipo propio esté ocupado, y que en momentos de baja actividad los repartidores encuentren trabajo en pedidos de otros aliados de la red. Todos ganan más cuando la red es más activa.

---

## 3. Pregunta más común del administrador

**"¿Y si mis repartidores empiezan a trabajar con otros aliados de la red y me dejan de traer pedidos a mí?"**

Esta es la pregunta más frecuente, y tiene una respuesta clara.

El repartidor puede —y debe— trabajar en toda la red. Eso es parte del diseño. Pero la comisión del repartidor siempre va al administrador que lo vinculó. Si el repartidor A, que pertenece al equipo del administrador 1, entrega un pedido de un aliado del administrador 2, el administrador 1 recibe su $200 de comisión sobre ese repartidor, y el administrador 2 recibe su $200 de comisión sobre ese aliado.

El repartidor no "se va" a otro equipo cuando toma un pedido de otro aliado. Sigue siendo del equipo de su administrador. Su administrador sigue ganando por cada entrega que haga, venga el pedido de donde venga.

Lo que sí podría preocupar es la salida definitiva de un repartidor: que el repartidor decida cambiarse de administrador. Pero eso no ocurre automáticamente por trabajar en la red compartida; requiere una decisión activa. Y si un repartidor decide cambiarse, la razón suele ser una diferencia de trato o de condiciones con su administrador actual, no el hecho de haber interactuado con aliados de otros equipos.

En resumen: la red compartida amplía las oportunidades del repartidor y, por extensión, los ingresos de su administrador. No hay motivo estructural para que eso debilite la relación entre ambos.

---

## 4. Mensaje clave para tranquilizar administradores

**"Domiquerendona no viene a quitarte tu equipo; viene a darte una red más grande para que tu equipo trabaje más."**

Este es el mensaje central para un administrador que duda. No es solo un argumento de venta: es la descripción exacta de cómo funciona el sistema.

Un administrador con 5 repartidores que opera en aislamiento tiene capacidad para atender los pedidos de sus propios aliados y nada más. Un administrador con los mismos 5 repartidores en la red Domiquerendona tiene acceso a todos los pedidos de todos los aliados de la red. Sus repartidores tienen más trabajo disponible. Sus aliados tienen más repartidores disponibles cuando los suyos están ocupados.

El administrador no cede nada de lo que ya tiene. Gana acceso a más.

---

## 5. Beneficios resumidos por actor

### Administrador local

- Sistema de gestión centralizado que reemplaza el caos de WhatsApp
- Registro contable automático: sabe exactamente cuánto ha ganado y cuánto ha movido
- Control total sobre su equipo: aprobaciones, recargas, activaciones
- Comisiones claras y automáticas por cada pedido de sus aliados y cada entrega de sus repartidores
- Acceso a una red más amplia que amplía las oportunidades de su equipo sin que pierda propiedad sobre él
- Herramientas de gestión de pedidos especiales (puede crear pedidos propios sin pagar comisión de aliado)
- Agenda de clientes de entrega con direcciones guardadas

### Aliado

- Creación de pedidos rápida y organizada
- Agenda de clientes recurrentes con direcciones guardadas: menos tiempo escribiendo, más tiempo atendiendo
- Trazabilidad en tiempo real: sabe exactamente en qué estado está cada pedido
- Protección de datos del cliente: los datos solo se revelan al repartidor confirmado, no a toda la red
- Acceso a todos los repartidores activos de la red, no solo a los del equipo inmediato
- Incentivos para acelerar pedidos sin respuesta
- Optimización de costos a través de rutas combinadas

### Repartidor

- Ofertas organizadas y claras: tarifa visible antes de aceptar, sin negociaciones
- Privacidad del cliente protegida: no recibe los datos hasta confirmar llegada al pickup
- Registro automático de cada carrera
- Acceso a pedidos de toda la red, no solo de los aliados de su equipo inmediato
- Rutas combinadas que maximizan el ingreso por salida
- Flujo claro: oferta → aceptar → navegar → llegada confirmada → entregar → registrar
