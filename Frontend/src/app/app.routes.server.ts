import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  {
    // Login: renderizado en servidor (no necesita autenticación)
    path: 'login',
    renderMode: RenderMode.Server
  },
  {
    // Panel admin: solo en el cliente (necesita localStorage y token)
    path: 'superadmin',
    renderMode: RenderMode.Client
  },
  {
    path: 'superadmin/**',
    renderMode: RenderMode.Client
  },
  {
    path: '**',
    renderMode: RenderMode.Server
  }
];
