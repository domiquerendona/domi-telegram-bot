// Importa la función para iniciar (bootstrap) una aplicación Angular moderna
import { bootstrapApplication } from '@angular/platform-browser';

// Importa la función para configurar el sistema de rutas
import { provideRouter } from '@angular/router';

// Importa el componente raíz de la aplicación
import { App} from './app/app';

// Importa la configuración de rutas definida en app.routes
import { routes } from './app/app.routes';

// Inicia la aplicación usando el componente raíz (AppComponent)
// y registra el sistema de enrutamiento con las rutas definidas
bootstrapApplication(App, {
  providers: [
    provideRouter(routes) // Habilita el router con las rutas configuradas
  ]
});