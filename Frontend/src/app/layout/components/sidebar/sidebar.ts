
import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, Router } from '@angular/router';
import { NgIf } from '@angular/common';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-sidebar', // Selector del componente
  standalone: true,         // Componente standalone (Angular moderno)
  imports: [RouterLink, RouterLinkActive, NgIf], // Directivas necesarias
  template: `
  <!-- Contenedor principal del sidebar -->
  <aside class="sidebar" [class.collapsed]="collapsed()">

    <!-- ================= HEADER ================= -->
    <div>
      <div class="header">
        <!-- Logo solo visible cuando NO está colapsado -->
        <span class="logo" *ngIf="!collapsed()">Sistema Admin</span>

        <!-- Botón que alterna entre menú y cerrar -->
        <button class="toggle-btn" (click)="toggle()">
          <span class="material-icons">
            {{ collapsed() ? 'menu' : 'close' }}
          </span>
        </button>
      </div>

      <!-- ================= MENÚ ================= -->
      <nav class="menu">

        <!-- Cada enlace usa routerLink y routerLinkActive -->
        <!-- routerLinkActive agrega la clase 'active' automáticamente -->

        <a routerLink="/superadmin"
           routerLinkActive="active"
           [routerLinkActiveOptions]="{ exact: true }">
          <span class="material-symbols-outlined">dashboard</span>
          <span *ngIf="!collapsed()">Dashboard</span>
        </a>

        <a routerLink="/superadmin/users"
           routerLinkActive="active">
          <span class="material-symbols-outlined">group</span>
          <span *ngIf="!collapsed()">Usuarios</span>
        </a>

        <a *ngIf="authService.isPlatformAdmin()"
           routerLink="/superadmin/administradores"
           routerLinkActive="active">
          <span class="material-symbols-outlined">admin_panel_settings</span>
          <span *ngIf="!collapsed()">Administradores</span>
        </a>

        <a routerLink="/superadmin/repartidores"
           routerLinkActive="active">
          <span class="material-symbols-outlined">delivery_dining</span>
          <span *ngIf="!collapsed()">Repartidores</span>
        </a>

        <a routerLink="/superadmin/aliados"
           routerLinkActive="active">
          <span class="material-symbols-outlined">storefront</span>
          <span *ngIf="!collapsed()">Aliados</span>
        </a>

        <a routerLink="/superadmin/orders"
           routerLinkActive="active">
          <span class="material-symbols-outlined">inventory_2</span>
          <span *ngIf="!collapsed()">Pedidos</span>
        </a>

        <a routerLink="/superadmin/saldos"
           routerLinkActive="active">
          <span class="material-symbols-outlined">payments</span>
          <span *ngIf="!collapsed()">Saldos</span>
        </a>

        <a routerLink="/superadmin/ganancias"
           routerLinkActive="active">
          <span class="material-symbols-outlined">trending_up</span>
          <span *ngIf="!collapsed()">Ganancias</span>
        </a>

      <a routerLink="/superadmin/mapa"
              routerLinkActive="active">
              <span class="material-symbols-outlined">map</span>
              <span *ngIf="!collapsed()">Mapa</span>
      </a>

          <a routerLink="/superadmin/solicitudes-soporte"
           routerLinkActive="active">
          <span class="material-symbols-outlined">support_agent</span>
          <span *ngIf="!collapsed()">Soporte</span>
        </a>

        <a routerLink="/superadmin/pedidos-especiales"
           routerLinkActive="active">
          <span class="material-symbols-outlined">assignment</span>
          <span *ngIf="!collapsed()">Pedidos especiales</span>
        </a>

        <a *ngIf="authService.isPlatformAdmin()"
           routerLink="/superadmin/settings"
           routerLinkActive="active">
          <span class="material-symbols-outlined">settings</span>
          <span *ngIf="!collapsed()">Configuración</span>
        </a>

        <a routerLink="/superadmin/perfil"
           routerLinkActive="active">
          <span class="material-symbols-outlined">person</span>
          <span *ngIf="!collapsed()">Mi perfil</span>
        </a>

      </nav>
    </div>

    <!-- ================= LOGOUT ================= -->
    <div class="logout">
      <a (click)="logout()" style="cursor:pointer">
        <span class="material-icons">logout</span>
        <span *ngIf="!collapsed()">Cerrar sesión</span>
      </a>
    </div>

  </aside>
  `,
  styles: [`
  /* ================= CONTENEDOR PRINCIPAL ================= */
  .sidebar {
    width: 260px;
    height: 100%;
    background: #4338ca;
    color: white;
    padding: 20px;
    display: flex;
    font-size: 16px;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.25s cubic-bezier(.4,0,.2,1);
  }

  /* Estado colapsado */
  .sidebar.collapsed {
    width: 56px;
    padding: 20px 8px;
  }

  /* Header superior */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 40px;
  }

  /* Logo */
  .logo {
    font-size: 25px;
    font-weight: 900;
  }

  /* Botón toggle sin fondo */
  .toggle-btn {
    background: transparent;
    border: none;
    color: white;
    cursor: pointer;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Menú vertical */
  .menu {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Estilo base de los enlaces */
  a {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 14px;
    border-radius: 8px;
    text-decoration: none;
    color: #e2e8f0f0;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  /* Hover → color más claro */
  a:hover {
    background: rgba(255, 255, 255, 0.12);
    color: white;
  }

  /* Activo → color más oscuro */
  a.active {
    background: rgba(0, 0, 0, 0.20);
    color: white;
  }

  /* Línea separadora inferior */
  .logout {
    border-top: 1px solid rgba(255,255,255,0.2);
    padding-top: 20px;
  }

  /* Centrar iconos cuando esté colapsado */
  .sidebar.collapsed .menu a,
  .sidebar.collapsed .logout a {
    justify-content: center;
    padding: 12px 0;
  }

  .sidebar.collapsed .header {
    justify-content: center;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .sidebar {
      position: fixed;
      z-index: 1000;
      left: 0;
      top: 0;
    }
  }
  `]
})
export class SidebarComponent {

  // Signal que controla si el sidebar está colapsado
  collapsed = signal(false);

  constructor(
    private router: Router,
    public authService: AuthService,
  ) {}

  // Método que alterna el estado del sidebar
  toggle() {
    this.collapsed.update(v => !v);
  }

  logout() {
    this.authService.clear();
    this.router.navigate(['/login']);
  }
}
