import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { CanActivate, Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(private router: Router, @Inject(PLATFORM_ID) private platformId: object) {}

  canActivate(): boolean {
    // En SSR (Node.js) no hay localStorage — dejar pasar, el API protege con token
    if (!isPlatformBrowser(this.platformId)) return true;

    const token = localStorage.getItem('admin_token');
    if (token) return true;
    this.router.navigate(['/login']);
    return false;
  }
}
