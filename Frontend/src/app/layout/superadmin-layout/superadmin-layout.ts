// Importa el decorador Component desde Angular
import { Component } from '@angular/core';

// Permite renderizar rutas hijas dentro del layout
import { RouterOutlet } from '@angular/router';

// Importa los componentes reutilizables del layout
import { SidebarComponent } from '../components/sidebar/sidebar';
import { HeaderComponent } from '../components/header/header';

@Component({
  // Nombre de la etiqueta HTML personalizada
  selector: 'app-superadmin-layout',

  // Indica que es un componente standalone (Angular moderno)
  standalone: true,

  // Componentes y módulos que este componente necesita
  imports: [RouterOutlet, SidebarComponent, HeaderComponent],

  // Template HTML embebido
  template: `
    <div class="layout">
      <!-- Sidebar lateral -->
      <app-sidebar></app-sidebar>

      <div class="main">
        <!-- Header superior -->
        <app-header></app-header>

        <!-- Contenedor donde se renderizan las rutas hijas -->
        <div class="content">
          <router-outlet></router-outlet>
        </div>
      </div>
    </div>
  `,

  // Estilos propios del layout
  styles: [`
    .layout {
      display: flex;        /* Distribuye sidebar y contenido en fila */
      height: 100vh;        /* Ocupa toda la altura de la pantalla */
    }

    .main {
      flex: 1;              /* Ocupa el espacio restante */
      display: flex;
      flex-direction: column; /* Header arriba y contenido abajo */
      background: #f4f6f9;  /* Fondo estilo Admin */
    }

    .content {
      padding: 20px;        /* Espaciado interno */
      flex: 1;              /* Ocupa todo el espacio disponible */
      overflow: auto;       /* Permite scroll si el contenido es grande */
    }
  `]
})
export class SuperadminLayoutComponent {}