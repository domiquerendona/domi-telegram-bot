// Cliente HTTP para realizar peticiones al backend (POST, GET, DELETE, PUT)
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

// Permite que el servicio pueda ser inyectado en toda la aplicación
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root' // Disponible globalmente (singleton)
})
export class ApiService {

  // URL base del backend configurable por environment
  // En producción debería estar en environment.ts
  private baseUrl = environment.apiBaseUrl;

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

  getActiveCourierLocations() {
    return this.http.get<any[]>(`${this.baseUrl}/admin/couriers/active-locations`);
  }

  getUnassignedOrders() {
    return this.http.get<any[]>(`${this.baseUrl}/admin/orders/unassigned`);
  }

  // ─── Formulario público del aliado ───────────────────────────────────────

  getFormInfo(token: string) {
    return this.http.get<any>(`${this.baseUrl}/form/${token}`);
  }

  lookupPhone(token: string, phone: string) {
    return this.http.post<any>(`${this.baseUrl}/form/${token}/lookup-phone`, { phone });
  }

  quoteForm(token: string, lat: number, lng: number) {
    return this.http.post<any>(`${this.baseUrl}/form/${token}/quote`, { lat, lng });
  }

  submitForm(token: string, payload: any) {
    return this.http.post<any>(`${this.baseUrl}/form/${token}/submit`, payload);
  }

}
