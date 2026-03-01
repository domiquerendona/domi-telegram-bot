import { Routes } from '@angular/router';
import { SuperadminLayoutComponent } from './layout/superadmin-layout/superadmin-layout';
import { MapaComponent } from './features/superadmin/mapa/mapa.component';

export const routes: Routes = [
  // Redirige la raíz al panel superadmin
  {
    path: '',
    redirectTo: 'superadmin',
    pathMatch: 'full'
  },

  // Panel superadmin con layout (sidebar + header)
  {
    path: 'superadmin',
    component: SuperadminLayoutComponent,
    children: [
      // Mapa de repartidores en tiempo real → /superadmin/mapa
      { path: 'mapa', component: MapaComponent },
      // future: { path: '', component: DashboardComponent },
      // future: { path: 'users', component: UsersComponent },
      // future: { path: 'settings', component: SettingsComponent },
    ]
  }
];
