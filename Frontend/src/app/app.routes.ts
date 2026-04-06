import { Routes } from '@angular/router';

import { SuperadminLayoutComponent } from './layout/superadmin-layout/superadmin-layout';
import { CourierLayoutComponent } from './layout/courier-layout/courier-layout';

import { MapaComponent } from './features/superadmin/mapa/mapa.component';
import { DashboardComponent } from './features/superadmin/dashboard/dashboard';
import { UsersComponent } from './features/superadmin/users/users';
import { SettingsComponent } from './features/superadmin/settings/settings';
import { AdministradoresComponent } from './features/superadmin/administradores/administradores';
import { RepartidoresComponent } from './features/superadmin/repartidores/repartidores';
import { AliadosComponent } from './features/superadmin/aliados/aliados';
import { OrdersComponent } from './features/superadmin/orders/orders';
import { SaldosComponent } from './features/superadmin/saldos/saldos';
import { GananciasComponent } from './features/superadmin/ganancias/ganancias';
import { TerminosComponent } from './features/superadmin/legal/terminos';
import { TratamientoDatosComponent } from './features/superadmin/legal/datos-personales';
import { PoliticaUsoComponent } from './features/superadmin/legal/política-uso';
import { CentroAyudaComponent } from './features/superadmin/soporte/centro-ayuda';
import { ContactoComponent } from './features/superadmin/soporte/contacto';
import { PreguntasFrecuentesComponent } from './features/superadmin/soporte/preguntas-frecuentes';
import { SolicitudesSoporteComponent } from './features/superadmin/soporte/solicitudes-soporte';
import { PedidosEspecialesComponent } from './features/superadmin/pedidos-especiales/pedidos-especiales';

import { CourierDashboardComponent } from './features/courier/dashboard/courier-dashboard';
import { CourierGananciasComponent } from './features/courier/ganancias/courier-ganancias';
import { PerfilComponent } from './features/shared/perfil/perfil';

import { LoginComponent } from './features/login/login';
import { FormPedidoComponent } from './features/public/form-pedido';
import { AuthGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [

  { path: 'login', component: LoginComponent },

  { path: 'form/:token', component: FormPedidoComponent },

  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full'
  },

  // --- Panel Administrativo (admin plataforma y admin local) ---
  {
    path: 'superadmin',
    component: SuperadminLayoutComponent,
    canActivate: [AuthGuard],
    children: [
      { path: '', component: DashboardComponent, data: { title: 'Dashboard' } },
      { path: 'users', component: UsersComponent, data: { title: 'Usuarios' } },
      {
        path: 'administradores',
        component: AdministradoresComponent,
        canActivate: [roleGuard],
        data: { title: 'Administradores', requiredPermission: 'manage_settings' }
      },
      { path: 'repartidores', component: RepartidoresComponent, data: { title: 'Repartidores' } },
      { path: 'aliados', component: AliadosComponent, data: { title: 'Aliados' } },
      { path: 'orders', component: OrdersComponent, data: { title: 'Pedidos' } },
      { path: 'saldos', component: SaldosComponent, data: { title: 'Saldos' } },
      { path: 'ganancias', component: GananciasComponent, data: { title: 'Ganancias' } },
      {
        path: 'settings',
        component: SettingsComponent,
        canActivate: [roleGuard],
        data: { title: 'Configuración', requiredPermission: 'manage_settings' }
      },
      { path: 'mapa', component: MapaComponent, data: { title: 'Mapa' } },
      { path: 'terminos', component: TerminosComponent, data: { title: 'Terminos y Condiciones' } },
      { path: 'datos-personales', component: TratamientoDatosComponent, data: { title: 'Tratamiento de Datos Personales' } },
      { path: 'politica-uso', component: PoliticaUsoComponent, data: { title: 'Política de Uso de la Plataforma' } },
      { path: 'centro-ayuda', component: CentroAyudaComponent, data: { title: 'Centro de Ayuda' } },
      { path: 'contacto', component: ContactoComponent, data: { title: 'Contacto' } },
      { path: 'preguntas-frecuentes', component: PreguntasFrecuentesComponent, data: { title: 'Preguntas Frecuentes' } },
      { path: 'solicitudes-soporte', component: SolicitudesSoporteComponent, data: { title: 'Soporte — Pin mal ubicado' } },
      { path: 'pedidos-especiales', component: PedidosEspecialesComponent, data: { title: 'Pedidos especiales' } },
      { path: 'perfil', component: PerfilComponent, data: { title: 'Mi Perfil' } },
    ]
  },

  // --- Panel Repartidor ---
  {
    path: 'courier',
    component: CourierLayoutComponent,
    canActivate: [AuthGuard],
    children: [
      { path: '', component: CourierDashboardComponent, data: { title: 'Dashboard' } },
      { path: 'ganancias', component: CourierGananciasComponent, data: { title: 'Mis Ganancias' } },
      { path: 'perfil', component: PerfilComponent, data: { title: 'Mi Perfil' } },
      { path: 'terminos', component: TerminosComponent, data: { title: 'Términos y Condiciones' } },
      { path: 'datos-personales', component: TratamientoDatosComponent, data: { title: 'Tratamiento de Datos Personales' } },
      { path: 'politica-uso', component: PoliticaUsoComponent, data: { title: 'Política de Uso' } },
      { path: 'centro-ayuda', component: CentroAyudaComponent, data: { title: 'Centro de Ayuda' } },
      { path: 'contacto', component: ContactoComponent, data: { title: 'Contacto' } },
      { path: 'preguntas-frecuentes', component: PreguntasFrecuentesComponent, data: { title: 'Preguntas Frecuentes' } },
    ]
  },
];
