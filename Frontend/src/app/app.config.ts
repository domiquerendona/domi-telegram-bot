// Permite definir la configuración global de la aplicación Angular
import { ApplicationConfig } from '@angular/core';

// Habilita el sistema de rutas en la aplicación
import { provideRouter } from '@angular/router';

// Habilita el cliente HTTP con soporte para interceptores funcionales
import { provideHttpClient, withInterceptors } from '@angular/common/http';

// Importa las rutas definidas en el archivo app.routes.ts
import { routes } from './app.routes';

// Interceptor que agrega el token de autenticación a cada petición
import { authInterceptor } from './core/interceptors/auth.interceptor';

// Configuración principal de la aplicación (Angular Standalone)
export const appConfig: ApplicationConfig = {
  providers: [

    // Activa el sistema de navegación basado en las rutas definidas
    provideRouter(routes),

    // Permite usar HttpClient con el interceptor de autenticación
    provideHttpClient(withInterceptors([authInterceptor]))
  ]
};

