import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { NgIf } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-courier-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgIf],
  template: `
  <div class="app">

    <aside class="sidebar" [class.collapsed]="collapsed()">
      <div>
        <div class="header">
          <span class="logo" *ngIf="!collapsed()">Mi Panel</span>
          <button class="toggle-btn" (click)="toggle()">
            <span class="material-icons">{{ collapsed() ? 'menu' : 'close' }}</span>
          </button>
        </div>

        <nav class="menu">
          <a routerLink="/courier" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">
            <span class="material-symbols-outlined">dashboard</span>
            <span *ngIf="!collapsed()">Dashboard</span>
          </a>
          <a routerLink="/courier/ganancias" routerLinkActive="active">
            <span class="material-symbols-outlined">trending_up</span>
            <span *ngIf="!collapsed()">Mis ganancias</span>
          </a>
          <a routerLink="/courier/perfil" routerLinkActive="active">
            <span class="material-symbols-outlined">person</span>
            <span *ngIf="!collapsed()">Mi perfil</span>
          </a>
        </nav>
      </div>

      <div class="logout">
        <a (click)="logout()" style="cursor:pointer">
          <span class="material-icons">logout</span>
          <span *ngIf="!collapsed()">Cerrar sesión</span>
        </a>
      </div>
    </aside>

    <div class="content-wrapper">
      <header class="topbar">
        <span class="username">
          <span class="material-symbols-outlined">delivery_dining</span>
          Repartidor
        </span>
      </header>
      <div class="content-container">
        <router-outlet></router-outlet>
      </div>
    </div>

  </div>
  `,
  styles: [`
  .app {
    display: flex;
    flex-direction: row;
    min-height: 100vh;
    background: #eef1f6;
  }

  .sidebar {
    width: 220px;
    background: #059669;
    color: white;
    padding: 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.25s cubic-bezier(.4,0,.2,1);
    flex-shrink: 0;
  }

  .sidebar.collapsed {
    width: 56px;
    padding: 20px 8px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 40px;
  }

  .logo {
    font-size: 20px;
    font-weight: 900;
  }

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

  .menu {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  a {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 14px;
    border-radius: 8px;
    text-decoration: none;
    color: #d1fae5;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  a:hover { background: rgba(255,255,255,0.15); color: white; }
  a.active { background: rgba(0,0,0,0.2); color: white; }

  .logout {
    border-top: 1px solid rgba(255,255,255,0.2);
    padding-top: 20px;
  }

  .sidebar.collapsed .menu a,
  .sidebar.collapsed .logout a {
    justify-content: center;
    padding: 12px 0;
  }

  .sidebar.collapsed .header { justify-content: center; }

  .content-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .topbar {
    background: white;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }

  .username {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #374151;
  }

  .content-container {
    padding: 30px;
    flex: 1;
  }
  `]
})
export class CourierLayoutComponent {
  collapsed = signal(false);

  constructor(private router: Router, public authService: AuthService) {}

  toggle() { this.collapsed.update(v => !v); }

  logout() {
    this.authService.clear();
    this.router.navigate(['/login']);
  }
}
