// Cliente HTTP para realizar peticiones al backend (POST, GET, DELETE, PUT)
import { HttpClient } from '@angular/common/http';

// Permite que el servicio pueda ser inyectado en toda la aplicación
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root' // Disponible globalmente (singleton)
})
export class ApiService {

  // URL base del backend (FastAPI en desarrollo)
  // En producción debería estar en environment.ts
  private baseUrl = 'http://127.0.0.1:8000';

  // Inyección del cliente HTTP de Angular
  constructor(private http: HttpClient) { }

  /**
   * Obtiene la lista de usuarios desde el backend.
   * Realiza una petición GET al endpoint /users.
   * Retorna un Observable con la respuesta del servidor.
   */
  getUsers() {
    return this.http.get(`${this.baseUrl}/users`);
  }

}
