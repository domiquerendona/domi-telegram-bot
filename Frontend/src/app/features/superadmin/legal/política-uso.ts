import { Component } from '@angular/core';

@Component({
  selector: 'app-politica-uso',
  standalone: true,
  template: `
  <div class="legal-wrapper">

    <div class="legal-card">

      <h1>Política de Uso de la Plataforma</h1>
      <p class="fecha">Última actualización: 25 de febrero de 2024</p>

      <h2>1. Uso Aceptable</h2>
      <p>
        Esta plataforma debe utilizarse únicamente para los fines previstos:
        coordinar servicios de domicilio y logística entre usuarios,
        repartidores y comercios aliados.
      </p>

      <p>
        Todo uso debe ser legal, ético y conforme a estos lineamientos.
      </p>

      <h2>2. Conductas Prohibidas</h2>

      <div class="warning">
        ⚠️ Está estrictamente prohibido:
      </div>

      <ul>
        <li>Realizar actividades fraudulentas o engañosas</li>
        <li>Proporcionar información falsa o inexacta</li>
        <li>Suplantar identidad de otra persona o empresa</li>
        <li>Intentar acceder a cuentas de otros usuarios</li>
        <li>Manipular saldos, comisiones o pagos</li>
        <li>Realizar ingeniería inversa de la plataforma</li>
        <li>Usar bots o scripts automatizados sin autorización</li>
        <li>Difundir contenido ofensivo o ilegal</li>
        <li>Acosar o intimidar a otros usuarios</li>
        <li>Solicitar o enviar productos prohibidos por ley</li>
      </ul>

      <h2>3. Responsabilidades por Rol</h2>

      <h3>3.1 Administradores</h3>
      <ul>
        <li>Gestionar usuarios de forma justa</li>
        <li>Mantener confidencialidad de la información</li>
        <li>No abusar de privilegios administrativos</li>
        <li>Documentar decisiones importantes</li>
        <li>Responder a reportes y quejas</li>
      </ul>

      <h3>3.2 Repartidores</h3>
      <ul>
        <li>Completar entregas en tiempo y forma</li>
        <li>Tratar con respeto a clientes</li>
        <li>Mantener productos en buen estado</li>
        <li>Cumplir normas de tránsito</li>
        <li>Actualizar estado de pedidos</li>
        <li>Comunicación profesional</li>
        <li>Reportar incidentes</li>
      </ul>

      <h3>3.3 Aliados (Comercios)</h3>
      <ul>
        <li>Proporcionar información veraz</li>
        <li>Preparar pedidos oportunamente</li>
        <li>Mantener estándares de calidad</li>
        <li>Empacar adecuadamente productos</li>
        <li>Actualizar inventario</li>
        <li>Respetar precios publicados</li>
      </ul>

      <h3>3.4 Clientes</h3>
      <ul>
        <li>Proporcionar direcciones correctas</li>
        <li>Estar disponible al momento de la entrega</li>
        <li>Tratar con respeto a repartidores</li>
        <li>Reportar problemas honestamente</li>
        <li>No solicitar productos prohibidos</li>
      </ul>

      <h2>4. Contenido y Comunicaciones</h2>
      <ul>
        <li>No publicar contenido ofensivo o ilegal</li>
        <li>Mantener comunicaciones respetuosas</li>
        <li>No compartir datos personales de terceros</li>
        <li>Respetar derechos de propiedad intelectual</li>
        <li>No hacer spam o mensajes masivos</li>
      </ul>

      <h2>5. Calificaciones y Reseñas</h2>
      <p>Las reseñas deben ser honestas y basadas en experiencias reales.</p>

      <ul>
        <li>Está prohibido publicar reseñas falsas</li>
        <li>No manipular calificaciones</li>
        <li>No usar múltiples cuentas</li>
      </ul>

      <h2>6. Productos Prohibidos</h2>

      <ul>
        <li>Sustancias ilegales o drogas</li>
        <li>Armas o explosivos</li>
        <li>Productos robados</li>
        <li>Animales vivos (sin autorización)</li>
        <li>Documentos confidenciales sin protocolo</li>
        <li>Productos que violen propiedad intelectual</li>
      </ul>

      <h2>7. Consecuencias por Incumplimiento</h2>

      <div class="consecuencias">

        <div class="item">
          <b>Advertencia Formal</b>
          <p>Primera infracción menor</p>
        </div>

        <div class="item">
          <b>Suspensión Temporal</b>
          <p>Infracciones repetidas</p>
        </div>

        <div class="item">
          <b>Suspensión Permanente</b>
          <p>Infracciones graves</p>
        </div>

        <div class="item">
          <b>Acciones Legales</b>
          <p>Actividades ilegales</p>
        </div>

      </div>

      <h2>8. Reportar Violaciones</h2>

      <p>Puede reportar uso indebido a través de:</p>

      <div class="info-box">
        <p><b>Email:</b> soporte@sistema.com</p>
        <p><b>Teléfono:</b> +57 300 123 4567</p>
        <p><b>Horario:</b> Lunes a viernes 8:00 AM - 6:00 PM</p>
      </div>

      <p>
        Todos los reportes son tratados con confidencialidad y se investigan
        en un plazo aproximado de 48 horas.
      </p>

      <h2>9. Actualizaciones de Políticas</h2>
      <p>
        Nos reservamos el derecho de actualizar estas políticas en cualquier
        momento. Los cambios significativos serán notificados con al menos
        15 días de anticipación.
      </p>

      <h2>10. Resolución de Disputas</h2>
      <p>
        Cualquier disputa relacionada con el uso de la plataforma se resolverá
        primero mediante mediación interna. Si no se alcanza un acuerdo,
        las partes se someterán a los tribunales de Pereira, Risaralda, Colombia.
      </p>

      <h2>Compromiso de Uso Responsable</h2>

      <div class="commitment">
        Al aceptar estas políticas, usted se compromete a usar la plataforma
        de manera responsable, ética y legal, contribuyendo a un ambiente
        seguro y confiable para todos los usuarios.
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
    margin-bottom:25px;
  }

  h2{
    margin-top:28px;
    margin-bottom:10px;
    font-size:20px;
  }

  h3{
    margin-top:16px;
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

  .warning{
    background:#fff3cd;
    border:1px solid #ffeeba;
    padding:12px;
    border-radius:8px;
    margin-bottom:10px;
  }

  .info-box{
    background:#eef2ff;
    padding:15px;
    border-radius:8px;
    margin-top:10px;
  }

  .commitment{
    margin-top:15px;
    padding:15px;
    background:#f9fafb;
    border-radius:8px;
    border:1px solid #e5e7eb;
  }

  .consecuencias{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
    gap:10px;
    margin-top:10px;
  }

  .item{
    background:#f9fafb;
    padding:12px;
    border-radius:8px;
    border:1px solid #e5e7eb;
  }

  `]
})
export class PoliticaUsoComponent {}