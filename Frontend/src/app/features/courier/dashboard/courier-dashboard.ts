import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NgIf } from '@angular/common';
import { environment } from '../../../../environments/environment';

interface CourierDashboard {
  entregas_hoy: number;
  entregas_mes: number;
  tarifa_mes: number;
  saldo: number;
  total_entregas: number;
}

@Component({
  selector: 'app-courier-dashboard',
  standalone: true,
  imports: [NgIf],
  template: `
  <div class="page">
    <h2 class="title">Dashboard</h2>

    <div *ngIf="cargando()" class="loading">Cargando...</div>
    <div *ngIf="error()" class="error">{{ error() }}</div>

    <div *ngIf="data()" class="cards">
      <div class="card green">
        <span class="material-symbols-outlined">today</span>
        <div class="info">
          <span class="value">{{ data()!.entregas_hoy }}</span>
          <span class="label">Entregas hoy</span>
        </div>
      </div>

      <div class="card blue">
        <span class="material-symbols-outlined">calendar_month</span>
        <div class="info">
          <span class="value">{{ data()!.entregas_mes }}</span>
          <span class="label">Entregas este mes</span>
        </div>
      </div>

      <div class="card purple">
        <span class="material-symbols-outlined">trending_up</span>
        <div class="info">
          <span class="value">{{ formatCop(data()!.tarifa_mes) }}</span>
          <span class="label">Ganancias este mes</span>
        </div>
      </div>

      <div class="card orange">
        <span class="material-symbols-outlined">account_balance_wallet</span>
        <div class="info">
          <span class="value">{{ formatCop(data()!.saldo) }}</span>
          <span class="label">Saldo disponible</span>
        </div>
      </div>

      <div class="card gray">
        <span class="material-symbols-outlined">local_shipping</span>
        <div class="info">
          <span class="value">{{ data()!.total_entregas }}</span>
          <span class="label">Total entregas históricas</span>
        </div>
      </div>
    </div>
  </div>
  `,
  styles: [`
  .page { max-width: 900px; }
  .title { font-size: 22px; font-weight: 700; color: #1f2937; margin-bottom: 24px; }
  .loading { color: #6b7280; }
  .error { color: #dc2626; background: #fef2f2; padding: 12px; border-radius: 8px; }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
  }

  .card {
    background: white;
    border-radius: 14px;
    padding: 24px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }

  .card span.material-symbols-outlined {
    font-size: 36px;
    border-radius: 10px;
    padding: 10px;
  }

  .card.green  span.material-symbols-outlined { color: #059669; background: #d1fae5; }
  .card.blue   span.material-symbols-outlined { color: #2563eb; background: #dbeafe; }
  .card.purple span.material-symbols-outlined { color: #7c3aed; background: #ede9fe; }
  .card.orange span.material-symbols-outlined { color: #d97706; background: #fef3c7; }
  .card.gray   span.material-symbols-outlined { color: #4b5563; background: #f3f4f6; }

  .info { display: flex; flex-direction: column; }
  .value { font-size: 24px; font-weight: 800; color: #111827; }
  .label { font-size: 13px; color: #6b7280; margin-top: 2px; }
  `]
})
export class CourierDashboardComponent implements OnInit {
  data = signal<CourierDashboard | null>(null);
  cargando = signal(true);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() {
    const token = localStorage.getItem('admin_token');
    this.http.get<CourierDashboard>(`${environment.apiBaseUrl}/courier/dashboard`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => { this.data.set(res); this.cargando.set(false); },
      error: (e) => { this.error.set(e.error?.detail ?? 'Error al cargar datos'); this.cargando.set(false); }
    });
  }

  formatCop(v: number): string {
    return '$' + v.toLocaleString('es-CO');
  }
}
