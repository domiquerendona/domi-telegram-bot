import { Component } from '@angular/core';

@Component({
  selector: 'app-tratamiento-datos',
  standalone: true,
  template: `
  <div class="legal-wrapper">

    <div class="legal-card">

      <h1>Política de Tratamiento de Datos Personales</h1>
      <p class="fecha">
        Última actualización: 25 de febrero de 2024 | Ley 1581 de 2012
      </p>

      <p class="sub">
        Incluye: Política de Privacidad, Tratamiento de Datos y Cookies
      </p>

      <h2>1. Identificación del Responsable</h2>
      <p><b>Razón Social:</b> Sistema de Administración S.A.S</p>
      <p><b>NIT:</b> 900.XXX.XXX-X</p>
      <p><b>Domicilio:</b> Pereira, Risaralda, Colombia</p>
      <p><b>Correo:</b> habeasdata@sistema.com</p>
      <p><b>Teléfono:</b> +57 300 123 4567</p>

      <h2>2. Marco Legal</h2>
      <ul>
        <li>Ley 1581 de 2012 - Protección de Datos Personales</li>
        <li>Decreto 1377 de 2013</li>
        <li>Decreto 1074 de 2015</li>
      </ul>

      <h2>3. Definiciones Importantes</h2>

      <h3>Dato Personal</h3>
      <p>
        Información vinculada o que pueda asociarse a una persona natural
        determinada o determinable.
      </p>

      <h3>Tratamiento</h3>
      <p>
        Cualquier operación sobre datos personales: recolección,
        almacenamiento, uso, circulación o supresión.
      </p>

      <h3>Titular</h3>
      <p>Persona natural cuyos datos son objeto de tratamiento.</p>

      <h3>Encargado</h3>
      <p>Persona que realiza el tratamiento por cuenta del responsable.</p>

      <h2>4. Finalidades del Tratamiento</h2>

      <h3>4.1 Finalidades Principales</h3>
      <ul>
        <li>Gestión de cuentas y autenticación</li>
        <li>Procesamiento de pedidos</li>
        <li>Gestión de pagos y comisiones</li>
        <li>Comunicación con usuarios</li>
        <li>Coordinación entre clientes, aliados y repartidores</li>
      </ul>

      <h3>4.2 Finalidades Secundarias</h3>
      <ul>
        <li>Mejorar la calidad del servicio</li>
        <li>Enviar notificaciones importantes</li>
        <li>Análisis estadístico</li>
        <li>Encuestas de satisfacción</li>
        <li>Prevención de fraude</li>
        <li>Cumplimiento legal</li>
      </ul>

      <h2>5. Datos que Recopilamos</h2>

      <h3>5.1 Datos de Identificación</h3>
      <ul>
        <li>Nombre completo</li>
        <li>Documento de identidad</li>
        <li>Fecha de nacimiento</li>
        <li>Fotografía (opcional)</li>
      </ul>

      <h3>5.2 Datos de Contacto</h3>
      <ul>
        <li>Correo electrónico</li>
        <li>Número celular</li>
        <li>Dirección física</li>
      </ul>

      <h3>5.3 Datos de Transacciones</h3>
      <ul>
        <li>Historial de pedidos</li>
        <li>Información de pagos</li>
        <li>Saldo y movimientos</li>
        <li>Comisiones generadas</li>
      </ul>

      <h3>5.4 Datos de Geolocalización</h3>
      <ul>
        <li>Ubicación durante el servicio</li>
        <li>Direcciones de recogida y entrega</li>
      </ul>

      <h2>6. Derechos de los Titulares</h2>

      <ul class="check">
        <li>✓ Derecho de Acceso</li>
        <li>✓ Derecho de Consulta</li>
        <li>✓ Derecho de Rectificación</li>
        <li>✓ Derecho de Supresión</li>
        <li>✓ Derecho de Oposición</li>
        <li>✓ Derecho de Revocación</li>
      </ul>

      <h2>7. Procedimiento para Ejercer sus Derechos</h2>

      <h3>Paso 1: Presentar Solicitud</h3>
      <p>Enviar solicitud a: habeasdata@sistema.com</p>

      <h3>Paso 2: Requisitos</h3>
      <ul>
        <li>Nombre completo</li>
        <li>Documento de identidad</li>
        <li>Datos de contacto</li>
        <li>Descripción de la solicitud</li>
      </ul>

      <h3>Paso 3: Tiempo de Respuesta</h3>
      <p>
        Solicitudes: máximo 15 días hábiles.  
        Consultas: máximo 10 días hábiles.
      </p>

      <h2>8. Medidas de Seguridad</h2>
      <ul>
        <li>Encriptación SSL/TLS</li>
        <li>Control de acceso</li>
        <li>Respaldos periódicos</li>
        <li>Monitoreo de seguridad</li>
        <li>Capacitación del personal</li>
      </ul>

      <h2>9. Transferencia Internacional de Datos</h2>
      <p>
        Actualmente no realizamos transferencias internacionales de datos.
      </p>

      <h2>10. Vigencia y Cambios</h2>
      <p>
        Esta política permanecerá vigente hasta que sea modificada.
      </p>

      <h2>11. Autoridad de Control</h2>

      <div class="info-box">
        Superintendencia de Industria y Comercio  
        www.sic.gov.co  
        Línea: 018000 910165
      </div>

      <h2>12. Compartir Información</h2>

      <ul class="check">
        <li>✓ Para completar el servicio</li>
        <li>✓ Cumplimiento legal</li>
        <li>✓ Prevención de fraude</li>
        <li>✓ Con su consentimiento</li>
      </ul>

      <h2>13. Cookies y Tecnologías de Rastreo</h2>

      <div class="cookie-box">
        🍪 Política de Cookies
      </div>

      <h3>Tipos de Cookies</h3>
      <ul>
        <li>Cookies esenciales</li>
        <li>Cookies de rendimiento</li>
        <li>Cookies de funcionalidad</li>
      </ul>

      <h2>14. Retención de Datos</h2>
      <ul>
        <li>Datos contables: 5 años</li>
        <li>Historial de transacciones: 5 años</li>
        <li>Datos de contacto: cuenta activa + 2 años</li>
      </ul>

      <h2>15. Menores de Edad</h2>

      <div class="warning">
        ⚠️ Nuestros servicios están dirigidos exclusivamente a mayores de 18 años.
      </div>

      <h2>16. Fecha de Vigencia</h2>
      <p>
        Esta política fue aprobada el 25 de febrero de 2024.
      </p>

      <h2>17. Declaración de Aceptación</h2>

      <ul class="check">
        <li>✓ Ha leído y acepta esta política</li>
        <li>✓ Autoriza el tratamiento de sus datos</li>
        <li>✓ Comprende sus derechos</li>
        <li>✓ Acepta el uso de cookies</li>
      </ul>

      <div class="contact">
        <p><b>Contacto Habeas Data</b></p>
        <p>Email: habeasdata@sistema.com</p>
        <p>Tiempo de respuesta: 15 días hábiles</p>
      </div>

    </div>

  </div>
  `,
  styles: [`

  .legal-wrapper{
    display:flex;
    justify-content:center;
    padding:40px 20px;
  }

  .legal-card{
    max-width:900px;
    width:100%;
    background:white;
    padding:40px;
    border-radius:12px;
    border:1px solid #e5e7eb;
  }

  h1{
    font-size:30px;
    margin-bottom:10px;
  }

  .fecha{
    color:#6b7280;
    margin-bottom:10px;
  }

  .sub{
    margin-bottom:25px;
    color:#374151;
  }

  h2{
    margin-top:28px;
    margin-bottom:10px;
    font-size:20px;
  }

  h3{
    margin-top:15px;
    font-size:16px;
  }

  p{
    color:#374151;
    line-height:1.7;
  }

  ul{
    padding-left:20px;
  }

  li{
    margin-bottom:6px;
  }

  .check li{
    list-style:none;
  }

  .info-box{
    background:#eef2ff;
    padding:12px;
    border-radius:6px;
    margin-top:10px;
  }

  .cookie-box{
    background:#fef3c7;
    padding:10px;
    border-radius:6px;
    margin-bottom:10px;
  }

  .warning{
    background:#fff3cd;
    border:1px solid #ffeeba;
    padding:12px;
    border-radius:8px;
  }

  .contact{
    margin-top:25px;
    padding:15px;
    background:#f9fafb;
    border-radius:8px;
    border:1px solid #e5e7eb;
  }

  `]
})
export class TratamientoDatosComponent {}