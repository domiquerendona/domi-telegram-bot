import { Component, inject } from '@angular/core';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  template: `
  <header class="header">

    <div class="left">
      <h2 class="title">{{ pageTitle }}</h2>
    </div>

    <div class="center">
      <div class="search-box">
        <span class="material-icons search-icon">search</span>
        <input type="text" placeholder="Buscar usuarios, pedidos, aliados..." />
        <span class="shortcut">⌘ K</span>
      </div>
    </div>

    <div class="right">
      <div class="admin-info">
        <span class="admin-title">{{ displayName() }}</span>
        <span class="admin-role">{{ roleLabel() }}</span>
      </div>
      <div class="avatar">{{ initials() }}</div>
      <span class="material-icons dropdown">expand_more</span>
    </div>

  </header>
  `,
  styles: [`
  .header {
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
    transition: all .2s;
  }
  .search-box:focus-within { background: #e5e7eb; }
  .search-box input { flex: 1; border: none; background: transparent; outline: none; font-size: 14px; }
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
    width: 40px; height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #5b21b6, #4338ca);
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 14px;
  }
  .dropdown { color: #6b7280; cursor: pointer; }
  @media (max-width: 1024px) { .search-box { width: 300px; } }
  @media (max-width: 768px)  { .center { display: none; } }
  `]
})
export class HeaderComponent {
  private authService = inject(AuthService);
  private router      = inject(Router);
  private route       = inject(ActivatedRoute);

  pageTitle = '';

  constructor() {
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map(() => {
        let r = this.route.firstChild;
        while (r?.firstChild) r = r.firstChild;
        return r?.snapshot.data['title'] ?? 'Dashboard';
      })
    ).subscribe(title => this.pageTitle = title);
  }

  displayName(): string {
    const u = this.authService.username();
    return u || 'Usuario';
  }

  roleLabel(): string {
    const role = this.authService.role;
    return role === 'ADMIN_PLATFORM' ? 'Admin Plataforma'
         : role === 'ADMIN_LOCAL'    ? 'Admin Local'
         : role === 'COURIER'        ? 'Repartidor'
         : 'Panel Web';
  }

  initials(): string {
    const name = this.displayName();
    return name.split(' ').slice(0, 2).map(w => w[0]?.toUpperCase() ?? '').join('') || 'U';
  }
}
