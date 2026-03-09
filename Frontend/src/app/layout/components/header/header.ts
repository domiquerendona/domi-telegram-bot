// Importamos lo necesario desde Angular
import { Component, inject } from '@angular/core';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';

@Component({
  // Selector que se usa en el HTML para llamar el componente
  selector: 'app-header',

  // Indicamos que es un componente standalone (Angular moderno)
  standalone: true,

  // ================================
  // TEMPLATE (HTML DEL HEADER)
  // ================================
  template: `
  <header class="header">

    <!-- IZQUIERDA -->
    <!-- Aquí mostramos el título dinámico de la página -->
    <div class="left">
      <h2 class="title">{{ pageTitle }}</h2>
    </div>

    <!-- CENTRO (BARRA DE BÚSQUEDA) -->
    <div class="center">
      <div class="search-box">

        <!-- Icono de búsqueda -->
        <span class="material-icons search-icon">search</span>

        <!-- Input para buscar -->
        <input 
          type="text" 
          placeholder="Buscar usuarios, pedidos, aliados..."
        />

        <!-- Atajo de teclado visual -->
        <span class="shortcut">⌘ K</span>
      </div>
    </div>

    <!-- DERECHA -->
    <div class="right">

      <!-- Información del administrador -->
      <div class="admin-info">
        <span class="admin-title">Admin Principal</span>
        <span class="admin-role">admin</span>
      </div>

      <!-- Avatar con iniciales -->
      <div class="avatar">
        AP
      </div>

      <!-- Icono desplegable -->
      <span class="material-icons dropdown">expand_more</span>

    </div>

  </header>
  `,

  // ================================
  // ESTILOS DEL COMPONENTE (CSS)
  // ================================
  styles: [`
  /* Contenedor principal del header */
  .header {
    height: 80px;
    background: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 30px;
    border-bottom: 1px solid #e5e7eb;
  }

  /* Título dinámico */
  .title {
    font-size: 22px;
    font-weight: 600;
    color: #111827;
  }

  /* Centro del header */
  .center {
    flex: 1;
    display: flex;
    justify-content: center;
  }

  /* Caja de búsqueda */
  .search-box {
    width: 500px;
    background: #f3f4f6;
    border-radius: 12px;
    display: flex;
    align-items: center;
    padding: 8px 15px;
    gap: 10px;
    transition: all 0.2s ease;
  }

  /* Cambio de color cuando el input está activo */
  .search-box:focus-within {
    background: #e5e7eb;
  }

  /* Input interno */
  .search-box input {
    flex: 1;
    border: none;
    background: transparent;
    outline: none;
    font-size: 14px;
  }

  /* Icono lupa */
  .search-icon {
    font-size: 20px;
    color: #6b7280;
  }

  /* Atajo visual */
  .shortcut {
    font-size: 12px;
    background: white;
    padding: 4px 8px;
    border-radius: 6px;
    color: #6b7280;
    border: 1px solid #e5e7eb;
  }

  /* Sección derecha */
  .right {
    display: flex;
    align-items: center;
    gap: 15px;
  }

  /* Contenedor del admin */
  .admin-info {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .admin-title {
    font-size: 14px;
    font-weight: 600;
    color: #111827;
  }

  .admin-role {
    font-size: 12px;
    color: #6b7280;
  }

  /* Avatar circular */
  .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #5b21b6, #4338ca);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
  }

  /* Icono dropdown */
  .dropdown {
    color: #6b7280;
    cursor: pointer;
  }

  /* Responsive tablet */
  @media (max-width: 1024px) {
    .search-box {
      width: 300px;
    }
  }

  /* Responsive móvil */
  @media (max-width: 768px) {
    .center {
      display: none;
    }
  }
  `]
})
export class HeaderComponent {

  // Inyectamos el Router para escuchar cambios de navegación
  router = inject(Router);

  // Inyectamos ActivatedRoute para acceder a la ruta actual
  route = inject(ActivatedRoute);

  // Variable donde guardaremos el título dinámico
  pageTitle = '';

  constructor() {

    // Escuchamos los eventos del router
    this.router.events
      .pipe(

        // Filtramos solo cuando la navegación termina
        filter(event => event instanceof NavigationEnd),

        // Mapeamos el evento para obtener el título desde la ruta
        map(() => {

          // Tomamos la primera ruta hija
          let currentRoute = this.route.firstChild;

          // Recorremos hasta llegar a la última ruta hija activa
          while (currentRoute?.firstChild) {
            currentRoute = currentRoute.firstChild;
          }

          // Retornamos el título definido en el data del routing
          // Si no existe, usamos 'Dashboard' por defecto
          return currentRoute?.snapshot.data['title'] ?? 'Dashboard';
        })
      )

      // Nos suscribimos y actualizamos el título
      .subscribe(title => {
        this.pageTitle = title;
      });
  }
}