import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-preguntas-frecuentes',
  standalone: true,
  imports: [RouterLink],
  template: `

<div class="faq-wrapper">

  <div class="faq-card">

    <h1>Preguntas Frecuentes</h1>
    <p class="subtitle">Encuentra respuestas a las dudas más comunes</p>

    <!-- GENERAL -->

    <h2>General</h2>

    <div class="faq-item">
      <h4>¿Qué es esta plataforma?</h4>
      <p>
        Es una plataforma tecnológica que permite gestionar pedidos,
        entregas y coordinación logística entre usuarios, repartidores
        y comercios aliados.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Cómo puedo registrarme?</h4>
      <p>
        El registro debe ser aprobado por un administrador. Contacta
        al equipo de soporte con tus datos personales y documentos
        de identidad. Una vez aprobado recibirás tus credenciales
        de acceso por correo electrónico.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿La plataforma tiene app móvil?</h4>
      <p>
        Actualmente puedes acceder desde cualquier navegador
        web en tu celular, tablet o computador.
      </p>
    </div>

    <!-- USUARIOS -->

    <h2>Usuarios y Cuentas</h2>

    <div class="faq-item">
      <h4>¿Qué tipos de usuarios existen?</h4>
      <p>
        La plataforma cuenta con diferentes roles como
        administradores, repartidores, aliados comerciales
        y clientes.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Puedo cambiar mi contraseña?</h4>
      <p>
        Sí. Puedes cambiar tu contraseña desde la configuración
        de tu cuenta dentro de la plataforma.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Qué hago si olvidé mi contraseña?</h4>
      <p>
        Contacta al equipo de soporte para restablecer tu acceso
        y recibir nuevas credenciales de forma segura.
      </p>
    </div>

    <!-- PEDIDOS -->

    <h2>Pedidos</h2>

    <div class="faq-item">
      <h4>¿Cómo funciona el proceso de pedidos?</h4>
      <p>
        Los pedidos se registran en la plataforma, se asigna
        un repartidor disponible y se realiza el seguimiento
        hasta la entrega final.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Puedo cancelar un pedido?</h4>
      <p>
        Sí. Los administradores pueden cancelar o modificar
        pedidos dependiendo del estado en el que se encuentren.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Qué hago si hay un problema con un pedido?</h4>
      <p>
        Debes contactar inmediatamente con soporte para que
        un administrador revise el caso y realice las correcciones
        necesarias.
      </p>
    </div>

    <!-- SALDOS -->

    <h2>Saldos y Pagos</h2>

    <div class="faq-item">
      <h4>¿Cómo funciona el sistema de saldos?</h4>
      <p>
        El saldo es virtual y se utiliza únicamente dentro
        de la plataforma para gestionar pedidos y comisiones.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Puedo retirar mi saldo en efectivo?</h4>
      <p>
        No. Los saldos son internos de la plataforma y se
        utilizan únicamente para operaciones dentro del sistema.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Cuánto es la comisión por pedido?</h4>
      <p>
        La comisión estándar es del 10% por cada pedido
        completado.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Cómo solicito una recarga de saldo?</h4>
      <p>
        Debes solicitarla directamente a un administrador
        o al área de soporte.
      </p>
    </div>

    <!-- SEGURIDAD -->

    <h2>Seguridad y Privacidad</h2>

    <div class="faq-item">
      <h4>¿Es segura la plataforma?</h4>
      <p>
        Sí. Implementamos medidas de seguridad para proteger
        la información de nuestros usuarios.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Cómo se usan mis datos personales?</h4>
      <p>
        Los datos se utilizan únicamente para el funcionamiento
        de la plataforma conforme a la política de tratamiento
        de datos personales.
      </p>
    </div>

    <div class="faq-item">
      <h4>¿Puedo eliminar mi cuenta?</h4>
      <p>
        Sí. Puedes solicitar la eliminación de tu cuenta
        contactando al equipo de soporte.
      </p>
    </div>

    <!-- TECNICOS -->

    <h2>Problemas Técnicos</h2>

    <div class="faq-item">
      <h4>No puedo iniciar sesión</h4>
      <p>
        Verifica tus credenciales o contacta al soporte
        técnico para restablecer tu acceso.
      </p>
    </div>

    <div class="faq-item">
      <h4>La página no carga correctamente</h4>
      <p>
        Intenta recargar la página o limpiar la caché
        del navegador.
      </p>
    </div>

    <div class="faq-item">
      <h4>No recibo notificaciones</h4>
      <p>
        Verifica la configuración de tu cuenta o consulta
        con soporte técnico.
      </p>
    </div>

    <!-- CONTACTO -->

    <div class="contact-box">

      <h3>¿No encontraste tu respuesta?</h3>

      <p>
        Contáctanos directamente y estaremos encantados de ayudarte.
      </p>

      <div class="actions">

        <a routerLink="/contacto" class="btn-primary">
          Formulario de Contacto
        </a>

        <a routerLink="/centro-ayuda" class="btn-secondary">
          Centro de Soporte
        </a>

      </div>

    </div>

  </div>

</div>

  `,
  styles: [`

.faq-wrapper{
  display:flex;
  justify-content:center;
  padding:40px 20px;
}

.faq-card{
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
  margin-bottom:30px;
}

h2{
  margin-top:30px;
  margin-bottom:10px;
  font-size:20px;
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

.contact-box{
  margin-top:40px;
  padding:20px;
  border-radius:10px;
  background:#f9fafb;
  border:1px solid #e5e7eb;
  text-align:center;
}

.actions{
  margin-top:15px;
  display:flex;
  gap:10px;
  justify-content:center;
}

.btn-primary{
  background:#2563eb;
  color:white;
  padding:10px 15px;
  border-radius:6px;
  text-decoration:none;
}

.btn-primary:hover{
  background:#1d4ed8;
}

.btn-secondary{
  background:#e5e7eb;
  color:#111827;
  padding:10px 15px;
  border-radius:6px;
  text-decoration:none;
}

.btn-secondary:hover{
  background:#d1d5db;
}

  `]
})
export class PreguntasFrecuentesComponent {}