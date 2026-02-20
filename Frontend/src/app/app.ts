// Importaciones necesarias para crear un componente Angular moderno
import { Component, OnInit, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

// Servicio que se comunica con el backend (FastAPI)
import { ApiService } from '../app/services/api';

@Component({
  selector: 'app-root', // Componente raíz de la aplicación
  standalone: true, // Indica que es un componente standalone (sin NgModule)
  imports: [RouterOutlet], // Permite renderizar las rutas hijas
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {

  // Estado reactivo usando Signals (Angular moderno)
  protected readonly title = signal('Frontend');

  // Inyección del servicio ApiService
  constructor(private api: ApiService) {}

  // Se ejecuta cuando el componente se inicializa
  ngOnInit() {

    // Llamada al backend para obtener la lista de usuarios
    this.api.getUsers().subscribe({

      // Si la petición es exitosa
      next: (data) => {
        console.log('Usuarios:', data);
      },

      // Si ocurre un error
      error: (err) => {
        console.error('Error:', err);
      }
    });
  }
}
