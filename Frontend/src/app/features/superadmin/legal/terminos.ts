import { Component } from '@angular/core';

@Component({
  selector: 'app-terminos',
  standalone: true,
  template: `
  <div class="terminos-wrapper">

    <div class="terminos-card">

      <h1>Términos y Condiciones</h1>
      <p class="fecha">Última actualización: 25 de febrero de 2024</p>

      <h2>1. Naturaleza de la Plataforma</h2>
      <p>
        Esta plataforma actúa como intermediario tecnológico entre usuarios,
        repartidores y comercios aliados. No somos responsables directos de la
        ejecución de los servicios de entrega, los cuales son realizados por
        repartidores independientes registrados en la plataforma.
      </p>

      <div class="warning">
        ⚠️ <b>Limitación de Responsabilidad</b>
        <p>
          La plataforma actúa exclusivamente como intermediario tecnológico.
          No garantizamos la calidad, idoneidad o disponibilidad continua de los
          servicios prestados por terceros (repartidores, aliados comerciales).
        </p>
      </div>

      <h2>2. Aceptación de los Términos</h2>
      <p>
        El registro y uso de esta plataforma implica la aceptación expresa de
        estos términos y condiciones, así como de la Política de Tratamiento de
        Datos Personales.
      </p>

      <h2>3. Responsabilidad de las Partes</h2>

      <h3>3.1 Responsabilidad de la Plataforma</h3>
      <ul>
        <li>Proporcionar la tecnología para conectar usuarios, repartidores y aliados</li>
        <li>Gestionar los pagos y comisiones dentro del sistema</li>
        <li>Mantener la seguridad de los datos personales</li>
        <li>Brindar soporte técnico</li>
      </ul>

      <h3>3.2 Responsabilidad de los Repartidores</h3>
      <ul>
        <li>Realizar las entregas en tiempo y forma</li>
        <li>Mantener actualizados sus datos</li>
        <li>Cumplir con normas de tránsito</li>
        <li>Tratar con respeto a clientes</li>
      </ul>

      <h3>3.3 Responsabilidad de los Aliados</h3>
      <ul>
        <li>Proporcionar información veraz sobre productos</li>
        <li>Preparar los pedidos en tiempo razonable</li>
        <li>Mantener estándares de calidad</li>
      </ul>

      <h2>4. Uso Indebido de la Plataforma</h2>
      <ul>
        <li>Fraude o actividades engañosas</li>
        <li>Información personal falsa</li>
        <li>Manipulación de saldo</li>
        <li>Suplantación de identidad</li>
        <li>Uso para actividades ilegales</li>
      </ul>

      <h2>5. Saldos y Recargas</h2>

      <div class="info-box">
        ⚠️ <b>Importante sobre el saldo</b>
      </div>

      <h3>5.1 Tipos de Saldo</h3>
      <ul>
        <li><b>Crédito promocional:</b> saldo por promociones o referidos. NO es reembolsable.</li>
        <li><b>Saldo recargado:</b> dinero agregado voluntariamente por el usuario. Solo utilizable dentro de la plataforma y NO reembolsable.</li>
      </ul>

      <h3>5.2 Condiciones Generales del Saldo</h3>
      <ul>
        <li>El saldo de la plataforma no es dinero bancario</li>
        <li>Solo puede usarse dentro del sistema</li>
        <li>No somos responsables del uso indebido</li>
        <li>Puede tener fecha de expiración</li>
      </ul>

      <h2>6. Comisiones y Pagos</h2>
      <p>
        La plataforma cobra una comisión por cada pedido completado.
        La comisión se descuenta automáticamente del valor del pedido
        y se refleja en el balance del usuario.
      </p>

      <h2>7. Suspensión y Cancelación de Cuentas</h2>
      <ul>
        <li>Incumplimiento de términos</li>
        <li>Actividades fraudulentas</li>
        <li>Múltiples quejas</li>
        <li>Inactividad prolongada</li>
        <li>Solicitud del usuario</li>
      </ul>

      <h2>8. Política de Cancelaciones</h2>
      <p>
        Los pedidos pueden cancelarse dentro de los primeros 5 minutos
        después de la asignación sin penalización.
      </p>

      <h2>9. Propiedad Intelectual</h2>
      <p>
        Todos los contenidos, marcas y elementos visuales son propiedad
        exclusiva de la empresa.
      </p>

      <h2>10. Modificaciones</h2>
      <p>
        Nos reservamos el derecho de modificar estos términos en cualquier
        momento. Los cambios serán publicados en la plataforma.
      </p>

      <h2>11. Fuerza Mayor</h2>
      <ul>
        <li>Fallas de internet</li>
        <li>Cortes eléctricos</li>
        <li>Desastres naturales</li>
        <li>Protestas o bloqueos</li>
        <li>Ataques cibernéticos</li>
      </ul>

      <h2>12. Disponibilidad del Servicio</h2>
      <ul>
        <li>No garantizamos disponibilidad 24/7</li>
        <li>Pueden existir mantenimientos</li>
        <li>Puede haber errores técnicos o bugs</li>
        <li>No garantizamos compatibilidad con todos los dispositivos</li>
      </ul>

      <h2>13. Jurisdicción</h2>
      <p>
        Estos términos se rigen por las leyes de la República de Colombia.
        Cualquier disputa será resuelta en los tribunales de Pereira, Risaralda.
      </p>

      <h2>14. Declaración de Aceptación</h2>
      <ul class="check">
        <li>✓ Ha leído y acepta estos términos</li>
        <li>✓ Acepta la política de datos personales</li>
        <li>✓ Comprende las limitaciones de responsabilidad</li>
        <li>✓ Acepta que los saldos no son reembolsables</li>
        <li>✓ Declara ser mayor de 18 años</li>
      </ul>

    </div>

  </div>
  `,
  styles: [`

  .terminos-wrapper{
    display:flex;
    justify-content:center;
    padding:40px 20px;
  }

  .terminos-card{
    max-width:900px;
    width:100%;
    background:white;
    padding:40px;
    border-radius:12px;
    border:1px solid #e5e7eb;
  }

  h1{
    font-size:32px;
    margin-bottom:8px;
  }

  .fecha{
    color:#6b7280;
    margin-bottom:30px;
  }

  h2{
    margin-top:30px;
    margin-bottom:10px;
    font-size:20px;
  }

  h3{
    margin-top:15px;
    font-size:16px;
  }

  p{
    line-height:1.7;
    color:#374151;
  }

  ul{
    padding-left:20px;
    margin-top:10px;
  }

  li{
    margin-bottom:6px;
  }

  .warning{
    background:#fff3cd;
    border:1px solid #ffeeba;
    padding:15px;
    border-radius:8px;
    margin:15px 0;
  }

  .info-box{
    background:#eef2ff;
    padding:10px;
    border-radius:6px;
    margin-bottom:10px;
  }

  .check li{
    list-style:none;
    margin-bottom:8px;
  }

  `]
})
export class TerminosComponent {}