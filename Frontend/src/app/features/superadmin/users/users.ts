// Importa el decorador Component para definir un componente en Angular
import { Component } from '@angular/core';

@Component({
  // Selector HTML para usar este componente
  selector: 'app-users',

  // Indica que es un componente standalone (no necesita módulo)
  standalone: true,

  // Plantilla HTML del componente
  template: `
    <div class="users">
      <!-- Título de la sección -->
      <h1>Gestión de Usuarios</h1>

      <!-- Tabla que muestra el listado de usuarios -->
      <table>

        <!-- Encabezado de la tabla -->
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Email</th>
            <th>Rol</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>

        <!-- Cuerpo de la tabla -->
        <tbody>
          <tr>
            <!-- Datos de ejemplo (estáticos por ahora) -->
            <td>Juan Pérez</td>
            <td>juan@email.com</td>
            <td>Admin</td>

            <!-- Estado del usuario con estilo visual -->
            <td><span class="active">Activo</span></td>

            <!-- Botones de acciones -->
            <td>
              <button class="edit">Editar</button>
              <button class="delete">Eliminar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,

  // Estilos del componente
  styles: [`
    .users {
      padding: 10px; /* Espaciado interno */
    }

    table {
      width: 100%; /* La tabla ocupa todo el ancho */
      border-collapse: collapse; /* Quita espacios entre bordes */
      background: white;
      border-radius: 10px;
      overflow: hidden;
    }

    th, td {
      padding: 12px;
      text-align: left;
    }

    thead {
      background: #343a40; /* Fondo oscuro en encabezado */
      color: white;
    }

    tbody tr {
      border-bottom: 1px solid #eee; /* Línea divisoria */
    }

    .active {
      background: #28a745; /* Verde para estado activo */
      color: white;
      padding: 4px 8px;
      border-radius: 5px;
      font-size: 12px;
    }

    button {
      padding: 5px 10px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      margin-right: 5px;
    }

    .edit {
      background: #007bff; /* Azul para editar */
      color: white;
    }

    .delete {
      background: #dc3545; /* Rojo para eliminar */
      color: white;
    }
  `]
})
export class UsersComponent {}