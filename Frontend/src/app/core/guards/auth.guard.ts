import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: object,
    private authService: AuthService,
  ) {}

  canActivate(): boolean {
    // En SSR (Node.js) no hay localStorage — dejar pasar, el API protege con token
    if (!isPlatformBrowser(this.platformId)) return true;

    const token = localStorage.getItem('admin_token');
    if (token) return true;

    // Limpiar estado stale si hay role pero no token
    this.authService.clear();
    this.router.navigate(['/login']);
    return false;
  }
}
