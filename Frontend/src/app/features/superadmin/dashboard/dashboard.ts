// Importa el decorador Component para definir un componente en Angular
import { Component } from '@angular/core';

@Component({
  // Selector HTML para usar este componente
  selector: 'app-dashboard',

  // Indica que es un componente standalone (no necesita módulo)
  standalone: true,

  // Plantilla HTML embebida del dashboard
  template: `
    <div class="dashboard">
      <!-- Título principal del panel -->
      <h1>Dashboard</h1>

      <!-- Contenedor de tarjetas con métricas -->
      <div class="cards">

        <!-- Tarjeta: Total de usuarios registrados -->
        <div class="card blue">
          <h3>Total Usuarios</h3>
          <p>120</p>
        </div>

        <!-- Tarjeta: Usuarios activos en el sistema -->
        <div class="card green">
          <h3>Usuarios Activos</h3>
          <p>95</p>
        </div>

        <!-- Tarjeta: Pedidos realizados hoy -->
        <div class="card orange">
          <h3>Pedidos Hoy</h3>
          <p>34</p>
        </div>

        <!-- Tarjeta: Repartidores actualmente activos -->
        <div class="card red">
          <h3>Repartidores Activos</h3>
          <p>12</p>
        </div>

      </div>
    </div>
  `,

  // Estilos propios del dashboard
  styles: [`
    .dashboard {
      padding: 10px; /* Espaciado interno del contenedor */
    }

    h1 {
      margin-bottom: 20px; /* Espacio debajo del título */
      font-weight: 600;
    }

    .cards {
      display: grid; /* Usa grid para organizar las tarjetas */
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 20px; /* Espacio entre tarjetas */
    }

    .card {
      padding: 20px;
      border-radius: 10px; /* Bordes redondeados */
      color: white; /* Texto blanco */
      box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* Sombra suave */
    }

    .card h3 {
      font-size: 14px;
      font-weight: 500;
    }

    .card p {
      font-size: 28px; /* Número grande */
      font-weight: bold;
      margin-top: 10px;
    }

    /* Colores personalizados para cada tarjeta */
    .blue { background: #007bff; }
    .green { background: #28a745; }
    .orange { background: #fd7e14; }
    .red { background: #dc3545; }
  `]
})
export class DashboardComponent {}