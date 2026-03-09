import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterModule],
 template: `
<footer class="footer">

  <div class="footer-content">
<!-- INFO SISTEMA -->
<div class="footer-col system">
  <h3>Sistema de Administración</h3>

  <p>
    Plataforma tecnológica de intermediación para servicios
    de domicilio y logística.
  </p>

  <div class="info">

    <div class="info-item">
      <span class="material-icons">location_on</span>
      Pereira, Risaralda, Colombia
    </div>

    <div class="info-item">
      <span class="material-icons">mail</span>
      contacto@sistema.com
    </div>

    <div class="info-item">
      <span class="material-icons">call</span>
      +57 300 123 4567
    </div>

  </div>
</div>
    <!-- LEGAL -->
    <div class="footer-col">
      <h4>Legal</h4>
    <a routerLink="/superadmin/terminos">Términos y Condiciones</a>
    <a routerLink="/superadmin/datos-personales">Tratamiento de Datos Personales</a>
     <a routerLink="/superadmin/politica-uso">Política de Uso</a>
   
    </div>

    <!-- SOPORTE -->
    <div class="footer-col">
      <h4>Soporte</h4>
      <a routerLink="/superadmin/centro-ayuda">Centro de Ayuda</a>
      <a routerLink="/superadmin/contacto">Contacto</a>
      <a routerLink="/superadmin/preguntas-frecuentes">Preguntas Frecuentes</a>
    </div>

  </div>

  <div class="footer-bottom">
    © 2026 Sistema de Administración. Todos los derechos reservados.
    <div class="nit">
      NIT: 900.XXX.XXX-X | Pereira, Colombia
    </div>
  </div>

</footer>
`,
  styles: [`
.footer{
  background:#081a33;
  color:#d1d5db;
}

/* CONTENIDO PRINCIPAL */

.footer-content{
  display:grid;
  grid-template-columns:2fr 1fr 1fr;
  gap:60px;
  padding:50px 60px;
}

.footer-col h3{
  color:white;
  margin-bottom:15px;
  font-size:20px;
}

.footer-col h4{
  color:white;
  margin-bottom:15px;
  font-size:16px;
}

.footer-col p{
  color:#9ca3af;
  line-height:1.6;
  margin-bottom:20px;
}
.info-item{
  display:flex;
  align-items:center;
  gap:8px;
  margin-bottom:8px;
  color:#9ca3af;
}

.info-item .material-icons{
  font-size:18px;
  color:#9ca3af;
}
.footer-col a{
  display:block;
  color:#9ca3af;
  text-decoration:none;
  margin-bottom:10px;
  transition:0.2s;
}

.footer-col a:hover{
  color:white;
}

.info div{
  margin-bottom:8px;
  color:#9ca3af;
}

/* PARTE INFERIOR */

.footer-bottom{
  border-top:1px solid rgba(255,255,255,0.1);
  text-align:center;
  padding:20px;
  font-size:14px;
  color:#9ca3af;
}

.nit{
  margin-top:5px;
  font-size:13px;
}

/* RESPONSIVE */

@media(max-width:900px){

.footer-content{
  grid-template-columns:1fr;
  gap:30px;
}

}
`]
})
export class FooterComponent {}