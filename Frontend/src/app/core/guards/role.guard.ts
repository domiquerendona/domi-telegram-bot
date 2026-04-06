import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';
import { PLATFORM_ID } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * Guard funcional que protege rutas según el permiso requerido.
 * Uso en rutas: data: { requiredPermission: 'manage_settings' }
 * Si el usuario no tiene el permiso → redirige a /superadmin.
 */
export const roleGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const platformId = inject(PLATFORM_ID);
  // En SSR no hay localStorage — dejar pasar, el API protege con token
  if (!isPlatformBrowser(platformId)) return true;

  const authService = inject(AuthService);
  const router = inject(Router);
  const requiredPermission: string | undefined = route.data['requiredPermission'];

  if (!requiredPermission) return true;

  if (authService.hasPermission(requiredPermission)) return true;

  return router.createUrlTree(['/superadmin']);
};
