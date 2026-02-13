// Permite definir la configuración global de la aplicación Angular
import { ApplicationConfig } from '@angular/core';

// Habilita el sistema de rutas en la aplicación
import { provideRouter } from '@angular/router';

// Habilita el cliente HTTP para consumir APIs externas (backend)
import { provideHttpClient } from '@angular/common/http';

// Importa las rutas definidas en el archivo app.routes.ts
import { routes } from './app.routes';

// Configuración principal de la aplicación (Angular Standalone)
export const appConfig: ApplicationConfig = {
  providers: [

    // Activa el sistema de navegación basado en las rutas definidas
    provideRouter(routes),

    // Permite usar HttpClient en toda la aplicación
    provideHttpClient()
  ]
};
