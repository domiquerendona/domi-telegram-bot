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
  <div class="app">
    <app-sidebar></app-sidebar>

    <div class="content-wrapper">
      <app-header></app-header>

      <div class="content-container">
        <router-outlet></router-outlet>
      </div>
    </div>
  </div>
`,
styles: [`
  .app {
    display: flex;
    height: 100vh;
    background: #eef1f6;
  }

  .content-wrapper {
    flex: 1;
    padding: 20px;
    display: flex;
    flex-direction: column;
  }

  .content-container {
    background: #f6f7fb;
    flex: 1;
    border-radius: 20px;
    padding: 30px;
    overflow: auto;
  }
`]
})
export class SuperadminLayoutComponent {}