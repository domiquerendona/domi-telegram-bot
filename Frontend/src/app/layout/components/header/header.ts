// Importa el decorador Component para crear un componente en Angular
import { Component } from '@angular/core';

@Component({
  // Selector HTML para usar este componente
  selector: 'app-header',

  // Indica que es un componente standalone (no necesita NgModule)
  standalone: true,

  // Template HTML embebido
  template: `
    <div class="header">
      <!-- Texto que se muestra en la parte superior del panel -->
      <span>Panel Super Administrador</span>
    </div>
  `,

  // Estilos propios del header
  styles: [`
    .header {
      height: 60px;                         /* Altura fija del header */
      background: white;                    /* Fondo blanco */
      display: flex;                        /* Flexbox para alineación */
      align-items: center;                  /* Centra verticalmente el contenido */
      padding: 0 20px;                      /* Espaciado horizontal */
      box-shadow: 0 2px 5px rgba(0,0,0,0.05); /* Sombra ligera inferior */
    }
  `]
})
export class HeaderComponent {}