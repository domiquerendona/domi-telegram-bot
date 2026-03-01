// Importa el decorador Component para crear un componente en Angular
import { Component } from '@angular/core';

// Importa directivas para navegación entre rutas
// RouterLink → permite navegar sin recargar la página
// RouterLinkActive → agrega una clase cuando la ruta está activa
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  // Nombre del selector HTML para usar este componente
  selector: 'app-sidebar',

  // Indica que es un componente standalone (Angular moderno, sin NgModule)
  standalone: true,

  // Directivas necesarias para que funcionen los enlaces de navegación
  imports: [RouterLink, RouterLinkActive],

  // Template HTML embebido
  template: `
    <div class="sidebar">
      <!-- Título del panel -->
      <h2>SuperAdmin</h2>

      <!-- Enlace al Dashboard -->
      <a
        routerLink="/superadmin"
        routerLinkActive="active"
        [routerLinkActiveOptions]="{ exact: true }">
        Dashboard
      </a>

      <!-- Enlace a la sección de usuarios -->
      <a
        routerLink="/superadmin/users"
        routerLinkActive="active">
        Usuarios
      </a>

      <!-- Enlace a la sección de configuración -->
      <a
        routerLink="/superadmin/settings"
        routerLinkActive="active">
        Configuración
      </a>

      <!-- Enlace al mapa de repartidores en tiempo real -->
      <a
        routerLink="/superadmin/mapa"
        routerLinkActive="active">
        Mapa en vivo
      </a>
    </div>
  `,

  // Estilos del sidebar
  styles: [`
    .sidebar {
      width: 220px;                 /* Ancho fijo del menú lateral */
      background: #1f2d3d;          /* Color oscuro estilo admin */
      color: white;                 /* Texto blanco */
      padding: 20px;                /* Espaciado interno */
      display: flex;
      flex-direction: column;       /* Elementos en columna */
      gap: 15px;                    /* Espacio entre enlaces */
    }

    a {
      color: #c2c7d0;               /* Color gris claro */
      text-decoration: none;        /* Quita subrayado */
    }

    .active {
      color: white;                 /* Color cuando está activo */
      font-weight: bold;            /* Resalta el enlace activo */
    }
  `]
})
export class SidebarComponent {}
