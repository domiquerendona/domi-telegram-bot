// Importa el tipo Routes desde el sistema de enrutamiento de Angular
import { Routes } from '@angular/router';

// Importa el layout principal que contendrá las vistas del Superadmin
import { SuperadminLayoutComponent } from './layout/superadmin-layout/superadmin-layout';

// Importa los componentes que se mostrarán dentro del layout
import { MapaComponent } from './features/superadmin/mapa/mapa.component';
import { DashboardComponent } from './features/superadmin/dashboard/dashboard';
import { UsersComponent } from './features/superadmin/users/users';
import { SettingsComponent } from './features/superadmin/settings/settings';
import { AdministradoresComponent } from './features/superadmin/administradores/administradores';
import { RepartidoresComponent } from './features/superadmin/repartidores/repartidores';
import { AliadosComponent } from './features/superadmin/aliados/aliados';
import { OrdersComponent } from './features/superadmin/orders/orders';
import { SaldosComponent } from './features/superadmin/saldos/saldos';
import { TerminosComponent } from './features/superadmin/legal/terminos';
import {TratamientoDatosComponent} from './features/superadmin/legal/datos-personales'
import {PoliticaUsoComponent} from './features/superadmin/legal/política-uso'
import { CentroAyudaComponent } from './features/superadmin/soporte/centro-ayuda';
import {ContactoComponent} from './features/superadmin/soporte/contacto'
import { PreguntasFrecuentesComponent } from './features/superadmin/soporte/preguntas-frecuentes';
// Definición de las rutas principales de la aplicación
export const routes: Routes = [

  // Ruta raíz: cuando el usuario entra a la URL base "/"
  {
    path: '',                   // Ruta vacía
    redirectTo: 'superadmin',   // Redirige automáticamente a "/superadmin"
    pathMatch: 'full'           // Debe coincidir exactamente con la ruta vacía
  },

  // Ruta principal del módulo Superadmin
  {
    path: 'superadmin',             // Ruta que representa el layout de superadmin
    component: SuperadminLayoutComponent, // Componente principal que contiene el layout
    children: [                     // Rutas hijas que se muestran dentro del layout
      { 
        path: '',                   // Ruta por defecto dentro de "superadmin"
        component: DashboardComponent, // Componente que se carga (Dashboard)
        data: { title: 'Dashboard' }   // Metadata opcional (por ejemplo, para título de página)
      },
      {
        path: 'users',              // Ruta para usuarios: "/superadmin/users"
        component: UsersComponent,  // Componente que se muestra
        data: { title: 'Usuarios' } // Metadata
      },
      {
        path: 'administradores',
        component: AdministradoresComponent,
        data: { title: 'Administradores' }
      },
      {
        path: 'repartidores',
        component: RepartidoresComponent,
        data: { title: 'Repartidores' }
      },
      {
        path: 'aliados',
        component: AliadosComponent,
        data: { title: 'Aliados' }
      },
      {
        path: 'orders',
        component: OrdersComponent,
        data: { title: 'Pedidos' }
      },
      {
        path: 'saldos',
        component: SaldosComponent,
        data: { title: 'Saldos' }
      },
      { 
        path: 'settings',           // Ruta para configuración: "/superadmin/settings"
        component: SettingsComponent,
        data: { title: 'Configuración' }
      },
      { 
        path: 'mapa',               // Ruta para mapa: "/superadmin/mapa"
        component: MapaComponent,
        data: { title: 'Mapa' }
      },
      
      { path: 'terminos', 
        component: TerminosComponent ,
      data: { title: 'Terminos y Condiciones' }
    },
     { path: 'datos-personales', 
        component: TratamientoDatosComponent ,
      data: { title: 'Tratamiento de Datos Personales' }
    },
        { path: 'politica-uso', 
        component: PoliticaUsoComponent ,
      data: { title: 'Política de Uso de la Plataforma' }
    },
        
    { path: 'centro-ayuda', 
        component: CentroAyudaComponent ,
      data: { title: 'Centro de Ayuda' }
    },
    { path: 'contacto', 
        component: ContactoComponent ,
      data: { title: 'Contacto' }
    },
    { path: 'preguntas-frecuentes', 
        component:  PreguntasFrecuentesComponent,
      data: { title: 'Preguntas Frecuentes' }
    },
    ]
  }
];