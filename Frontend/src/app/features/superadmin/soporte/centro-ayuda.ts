import { Component } from '@angular/core';

@Component({
  selector: 'app-centro-ayuda',
  standalone: true,
  template: `

<div class="soporte-wrapper">

  <div class="soporte-card">

    <h1>Centro de Ayuda</h1>
    <p class="subtitle">Estamos aquí para ayudarte</p>

    <!-- CANALES -->

    <h2>Canales de Atención</h2>

    <div class="canales">

      <div class="canal">
        <h3>Correo Electrónico</h3>
        <p>soporte@sistema.com</p>
        <span>Respuesta en 24-48 horas</span>
      </div>

      <div class="canal">
        <h3>Teléfono</h3>
        <p>+57 300 123 4567</p>
        <span>Lun - Vie: 8:00 AM - 6:00 PM</span>
      </div>

      <div class="canal">
        <h3>WhatsApp</h3>
        <p>+57 300 123 4567</p>
        <span>Atención inmediata</span>
      </div>

    </div>

    <!-- HORARIO -->

    <h2>Horario de Atención</h2>

    <p>Lunes a Viernes</p>
    <p>8:00 AM - 6:00 PM (Hora Colombia)</p>

    <!-- FORMULARIO -->

    <h2>Envíanos un Mensaje</h2>

    <form class="form">

      <input type="text" placeholder="Tu nombre">

      <input type="email" placeholder="tu@email.com">

      <textarea rows="4" placeholder="Describe tu consulta o problema..."></textarea>

      <button type="button">Enviar Mensaje</button>

    </form>

    <!-- FAQ -->

    <h2>Preguntas Frecuentes</h2>

    <div class="faq">

      <div class="faq-item">
        <h4>¿Cómo puedo registrarme en la plataforma?</h4>
        <p>
        Contacta con un administrador para que active tu cuenta.
        Necesitarás proporcionar documentos de identidad y aceptar
        los términos y condiciones.
        </p>
      </div>

      <div class="faq-item">
        <h4>¿Cómo funciona el sistema de saldos?</h4>
        <p>
        El saldo es virtual y solo puede usarse dentro de la plataforma.
        Los administradores pueden recargar saldo a repartidores y
        otros usuarios según sea necesario.
        </p>
      </div>

      <div class="faq-item">
        <h4>¿Cuál es el porcentaje de comisión?</h4>
        <p>
        La comisión estándar es del 10% por pedido completado.
        Este porcentaje puede variar según acuerdos específicos
        con aliados o administradores locales.
        </p>
      </div>

      <div class="faq-item">
        <h4>¿Qué hago si tengo un problema con un pedido?</h4>
        <p>
        Contacta inmediatamente al administrador a través de
        cualquiera de nuestros canales.
        </p>
      </div>

      <div class="faq-item">
        <h4>¿Puedo cancelar mi cuenta?</h4>
        <p>
        Sí, puedes solicitar la cancelación de tu cuenta
        contactando a soporte. Ten en cuenta que los saldos
        no son reembolsables según nuestros términos.
        </p>
      </div>

    </div>

    <!-- INFO -->

    <h2>Información Adicional</h2>

    <div class="info">
      <p><b>Dirección:</b> Pereira, Risaralda, Colombia</p>
      <p><b>NIT:</b> 900.XXX.XXX-X</p>
      <p><b>Razón Social:</b> Sistema de Administración S.A.S</p>
    </div>

  </div>

</div>

  `,
  styles: [`
.soporte-wrapper{
  display:flex;
  justify-content:center;
  padding:40px 20px;
}

.soporte-card{
  max-width:900px;
  width:100%;
  background:white;
  padding:40px;
  border-radius:12px;
  border:1px solid #e5e7eb;
}

h1{
  font-size:30px;
  margin-bottom:5px;
}

.subtitle{
  color:#6b7280;
  margin-bottom:25px;
}

h2{
  margin-top:30px;
  margin-bottom:10px;
  font-size:20px;
}

h3{
  font-size:16px;
  margin-bottom:3px;
}

.canales{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:15px;
  margin-bottom:20px;
}

.canal{
  border:1px solid #e5e7eb;
  padding:15px;
  border-radius:8px;
  background:#f9fafb;
}

.canal span{
  font-size:13px;
  color:#6b7280;
}

.form{
  display:flex;
  flex-direction:column;
  gap:10px;
  margin-bottom:20px;
}

input, textarea{
  padding:10px;
  border-radius:6px;
  border:1px solid #d1d5db;
}

button{
  background:#2563eb;
  color:white;
  border:none;
  padding:10px;
  border-radius:6px;
  cursor:pointer;
}

button:hover{
  background:#1d4ed8;
}

.faq-item{
  margin-bottom:15px;
}

.faq-item h4{
  font-size:15px;
  margin-bottom:5px;
}

.faq-item p{
  color:#374151;
}

.info{
  margin-top:10px;
  color:#374151;
}
  `]
})
export class CentroAyudaComponent {}