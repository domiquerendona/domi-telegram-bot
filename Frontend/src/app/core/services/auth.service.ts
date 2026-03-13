import { Injectable, Inject, PLATFORM_ID, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

// Permisos estáticos por rol — espejo del backend (web/users/roles.py)
const ROLE_PERMISSIONS: Record<string, string[]> = {
  ADMIN_PLATFORM: [
    'view_dashboard',
    'view_users',
    'approve_user',
    'reject_user',
    'deactivate_user',
    'reactivate_user',
    'view_couriers_map',
    'view_unassigned_orders',
    'manage_settings',
  ],
  ADMIN_LOCAL: [
    'view_dashboard',
    'view_users',
    'approve_user',
    'deactivate_user',
    'reactivate_user',
    'view_couriers_map',
    'view_unassigned_orders',
  ],
};

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _role = signal<string | null>(null);
  private _permissions = signal<string[]>([]);

  constructor(@Inject(PLATFORM_ID) private platformId: object) {
    if (isPlatformBrowser(this.platformId)) {
      const role = localStorage.getItem('admin_role');
      if (role) {
        this._role.set(role);
        this._permissions.set(ROLE_PERMISSIONS[role] ?? []);
      }
    }
  }

  get role(): string | null {
    return this._role();
  }

  get permissions(): string[] {
    return this._permissions();
  }

  setUser(role: string): void {
    this._role.set(role);
    this._permissions.set(ROLE_PERMISSIONS[role] ?? []);
    if (isPlatformBrowser(this.platformId)) {
      localStorage.setItem('admin_role', role);
    }
  }

  hasPermission(permission: string): boolean {
    return this._permissions().includes(permission);
  }

  isPlatformAdmin(): boolean {
    return this._role() === 'ADMIN_PLATFORM';
  }

  clear(): void {
    this._role.set(null);
    this._permissions.set([]);
    if (isPlatformBrowser(this.platformId)) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_username');
      localStorage.removeItem('admin_role');
    }
  }
}
