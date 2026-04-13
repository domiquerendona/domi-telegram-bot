import { Component, signal, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { FooterComponent } from '../components/footer/footer';
import { ToastComponent } from '../components/toast/toast';
import { filter, map } from 'rxjs/operators';

@Component({
  selector: 'app-courier-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FooterComponent, ToastComponent],
  template: `
  <div class="app">

    <!-- ===== SIDEBAR ===== -->
    <aside class="sidebar" [class.collapsed]="collapsed()">
      <div>
        <div class="header">
          @if (!collapsed()) {
            <span class="logo">Mi Panel</span>
          }
          <button class="toggle-btn" (click)="toggle()">
            <span class="material-icons">{{ collapsed() ? 'menu' : 'close' }}</span>
          </button>
        </div>

        <nav class="menu">
          <a routerLink="/courier" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">
            <span class="material-symbols-outlined">dashboard</span>
            @if (!collapsed()) { <span>Dashboard</span> }
          </a>
          <a routerLink="/courier/ganancias" routerLinkActive="active">
            <span class="material-symbols-outlined">trending_up</span>
            @if (!collapsed()) { <span>Mis ganancias</span> }
          </a>
          <a routerLink="/courier/perfil" routerLinkActive="active">
            <span class="material-symbols-outlined">person</span>
            @if (!collapsed()) { <span>Mi perfil</span> }
          </a>
        </nav>
      </div>

      <div class="logout">
        <a (click)="logout()" style="cursor:pointer">
          <span class="material-icons">logout</span>
          @if (!collapsed()) { <span>Cerrar sesión</span> }
        </a>
      </div>
    </aside>

    <!-- ===== CONTENIDO ===== -->
    <div class="content-wrapper">

      <header class="topbar">
        <div class="left">
          <h2 class="title">{{ pageTitle }}</h2>
        </div>

        <div class="center">
          <div class="search-box">
            <span class="material-icons search-icon">search</span>
            <input type="text" placeholder="Buscar entregas, pedidos..." />
            <span class="shortcut">⌘ K</span>
          </div>
        </div>

        <div class="right">
          <div class="admin-info">
            <span class="admin-title">{{ authService.username() }}</span>
            <span class="admin-role">Repartidor</span>
          </div>
          <div class="avatar">{{ initials() }}</div>
          <span class="material-icons dropdown">expand_more</span>
        </div>
      </header>

      <div class="content-container">
        <router-outlet></router-outlet>
      </div>

      <app-footer base="/courier"></app-footer>

    </div>
  </div>
  <app-toast></app-toast>
  `,
  styles: [`
  .app {
    display: flex;
    flex-direction: row;
    background: #eef1f6;
    min-height: 100vh;
  }

  /* ===== SIDEBAR — mismas medidas y colores que el admin ===== */
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
    flex-shrink: 0;
    position: sticky;
    top: 0;
    min-height: 100vh;
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

  .logo { font-size: 25px; font-weight: 900; }

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

  .menu { display: flex; flex-direction: column; gap: 8px; }

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

  a:hover { background: rgba(255,255,255,0.12); color: white; }
  a.active { background: rgba(0,0,0,0.20); color: white; }

  .logout {
    border-top: 1px solid rgba(255,255,255,0.2);
    padding-top: 20px;
  }

  .sidebar.collapsed .menu a,
  .sidebar.collapsed .logout a { justify-content: center; padding: 12px 0; }
  .sidebar.collapsed .header { justify-content: center; }

  /* ===== CONTENIDO ===== */
  .content-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  /* ===== HEADER — idéntico al admin ===== */
  .topbar {
    height: 80px;
    background: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 30px;
    border-bottom: 1px solid #e5e7eb;
  }

  .title { font-size: 22px; font-weight: 600; color: #111827; }

  .center { flex: 1; display: flex; justify-content: center; }

  .search-box {
    width: 500px;
    background: #f3f4f6;
    border-radius: 12px;
    display: flex;
    align-items: center;
    padding: 8px 15px;
    gap: 10px;
    transition: all 0.2s ease;
  }

  .search-box:focus-within { background: #e5e7eb; }

  .search-box input {
    flex: 1;
    border: none;
    background: transparent;
    outline: none;
    font-size: 14px;
  }

  .search-icon { font-size: 20px; color: #6b7280; }

  .shortcut {
    font-size: 12px;
    background: white;
    padding: 4px 8px;
    border-radius: 6px;
    color: #6b7280;
    border: 1px solid #e5e7eb;
  }

  .right { display: flex; align-items: center; gap: 15px; }

  .admin-info { display: flex; flex-direction: column; align-items: flex-end; }
  .admin-title { font-size: 14px; font-weight: 600; color: #111827; }
  .admin-role  { font-size: 12px; color: #6b7280; }

  .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #5b21b6, #4338ca);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
  }

  .dropdown { color: #6b7280; cursor: pointer; }

  .content-container {
    background: #f6f7fb;
    flex: 1;
    padding: 30px;
  }

  @media (max-width: 1024px) { .search-box { width: 300px; } }
  @media (max-width: 768px)  { .center { display: none; } }
  `]
})
export class CourierLayoutComponent {
  collapsed  = signal(false);
  pageTitle  = '';

  router     = inject(Router);
  route      = inject(ActivatedRoute);
  public authService = inject(AuthService);

  constructor() {
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map(() => {
        let r = this.route.firstChild;
        while (r?.firstChild) r = r.firstChild;
        return r?.snapshot.data['title'] ?? 'Dashboard';
      })
    ).subscribe(t => this.pageTitle = t);
  }

  toggle() { this.collapsed.update(v => !v); }

  logout() {
    this.authService.clear();
    this.router.navigate(['/login']);
  }

  initials(): string {
    const u = this.authService.username() ?? '';
    return u.slice(0, 2).toUpperCase();
  }
}
