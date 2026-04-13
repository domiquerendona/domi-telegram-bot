// Importa el decorador Component desde Angular
import { Component } from '@angular/core';

// Permite renderizar rutas hijas dentro del layout
import { RouterOutlet } from '@angular/router';

// Importa los componentes reutilizables del layout
import { SidebarComponent } from '../components/sidebar/sidebar';
import { HeaderComponent } from '../components/header/header';
import { FooterComponent } from '../components/footer/footer';
import { ToastComponent } from '../components/toast/toast';
import { ConfirmModalComponent } from '../components/confirm-modal/confirm-modal';

@Component({
  selector: 'app-superadmin-layout',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent, HeaderComponent, FooterComponent, ToastComponent, ConfirmModalComponent],

  template: `
  <div class="app">

    <app-sidebar></app-sidebar>

    <div class="content-wrapper">

      <app-header></app-header>

      <div class="content-container">
        <router-outlet></router-outlet>
      </div>
      <app-footer></app-footer>

    </div>

  </div>
  <app-toast></app-toast>
  <app-confirm-modal></app-confirm-modal>
  `,

styles: [`
 .app {
    display: flex;
    flex-direction: row;
    background: #eef1f6;
  }

  .content-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  .content-container {
    background: #f6f7fb;
    flex: 1;
    padding: 30px;
  }
`]
})
export class SuperadminLayoutComponent {}