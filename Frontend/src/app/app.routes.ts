// Importa el tipo Routes desde el sistema de enrutamiento de Angular
import { Routes } from '@angular/router';
import { SuperadminLayoutComponent } from './layout/superadmin-layout/superadmin-layout';
import { MapaComponent } from './features/superadmin/mapa/mapa.component';
// Importa los componentes que se mostrarán dentro del layout
 import { DashboardComponent } from './features/superadmin/dashboard/dashboard';
 import { UsersComponent } from './features/superadmin/users/users';
 import { SettingsComponent } from './features/superadmin/settings/settings';

// Definición de las rutas principales de la aplicación
export const routes: Routes = [

  // Ruta raíz: cuando el usuario entra a "/"
  {
    path: '',
    redirectTo: 'superadmin', // Redirige automáticamente a /superadmin
    pathMatch: 'full' // La URL debe coincidir exactamente
  },

  // Ruta principal del panel superadmin
  {
    path: 'superadmin',
    component: SuperadminLayoutComponent, // Layout base (sidebar + navbar + router-outlet)

    // Rutas hijas que se renderizan dentro del layout
    children: [
       { path: '', component: DashboardComponent }, // /superadmin
       { path: 'users', component: UsersComponent }, // /superadmin/users
       { path: 'settings', component: SettingsComponent }, // /superadmin/settings
       { path: 'mapa', component: MapaComponent },
    ]
  }
];
