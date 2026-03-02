// Importa el decorador Component para definir un componente en Angular
import { Component } from '@angular/core';

@Component({
  // Selector HTML para usar este componente
  selector: 'app-settings',

  // Indica que es un componente standalone (no necesita módulo)
  standalone: true,

  // Plantilla HTML del componente
  template: `
    <div class="settings">
      <!-- Título de la sección -->
      <h1>Configuración</h1>

      <!-- Tarjeta que contiene el formulario básico de configuración -->
      <div class="card">

        <!-- Campo para el nombre de la plataforma -->
        <label>Nombre de la Plataforma</label>
        <input type="text" placeholder="DomiExpress" />

        <!-- Campo para el correo de soporte -->
        <label>Email de soporte</label>
        <input type="email" placeholder="soporte@domiexpress.com" />

        <!-- Botón para guardar los cambios -->
        <button>Guardar Cambios</button>
      </div>
    </div>
  `,

  // Estilos propios del componente
  styles: [`
    .settings {
      padding: 10px; /* Espaciado interno del contenedor */
    }

    .card {
      background: white; /* Fondo blanco tipo tarjeta */
      padding: 20px;
      border-radius: 10px; /* Bordes redondeados */
      display: flex;
      flex-direction: column; /* Elementos en columna */
      gap: 10px; /* Espacio entre elementos */
      width: 400px; /* Ancho fijo */
      box-shadow: 0 4px 10px rgba(0,0,0,0.05); /* Sombra suave */
    }

    input {
      padding: 8px;
      border-radius: 5px;
      border: 1px solid #ccc;
    }

    button {
      margin-top: 10px;
      padding: 10px;
      background: #007bff; /* Azul principal */
      border: none;
      border-radius: 5px;
      color: white;
      cursor: pointer;
    }
  `]
})
export class SettingsComponent {}