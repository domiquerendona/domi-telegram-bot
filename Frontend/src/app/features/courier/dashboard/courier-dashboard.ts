import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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
  imports: [],
  template: `
  <div class="page">
    <div class="page-header">
      <h1>Dashboard</h1>
      <button class="btn-refresh" (click)="cargar()">↻ Actualizar</button>
    </div>

    @if (cargando()) { <div class="loading">Cargando...</div> }
    @if (error()) { <div class="error-msg">{{ error() }}</div> }

    @if (!cargando() && !error() && data()) {

      <div class="section-label">Entregas</div>
      <div class="cards">
        <div class="card indigo">
          <span class="material-symbols-outlined">today</span>
          <div>
            <div class="card-label">Entregas hoy</div>
            <div class="card-value">{{ data()!.entregas_hoy }}</div>
          </div>
        </div>
        <div class="card blue">
          <span class="material-symbols-outlined">calendar_month</span>
          <div>
            <div class="card-label">Entregas este mes</div>
            <div class="card-value">{{ data()!.entregas_mes }}</div>
          </div>
        </div>
        <div class="card teal">
          <span class="material-symbols-outlined">local_shipping</span>
          <div>
            <div class="card-label">Total histórico</div>
            <div class="card-value">{{ data()!.total_entregas }}</div>
          </div>
        </div>
      </div>

      <div class="section-label">Finanzas</div>
      <div class="cards">
        <div class="card purple">
          <span class="material-symbols-outlined">trending_up</span>
          <div>
            <div class="card-label">Ganancias este mes</div>
            <div class="card-value">{{ fmt(data()!.tarifa_mes) }}</div>
          </div>
        </div>
        <div class="card dark">
          <span class="material-symbols-outlined">account_balance_wallet</span>
          <div>
            <div class="card-label">Saldo disponible</div>
            <div class="card-value">{{ fmt(data()!.saldo) }}</div>
          </div>
        </div>
      </div>

    }
  </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; color: #111827; }
    .btn-refresh { padding: 6px 14px; border-radius: 8px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 13px; color: #374151; }
    .btn-refresh:hover { border-color: #4338ca; color: #4338ca; }

    .section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #9ca3af; margin-bottom: 12px; margin-top: 8px; }

    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }

    .card {
      border-radius: 14px;
      padding: 20px 22px;
      color: white;
      display: flex;
      align-items: flex-start;
      gap: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .card .material-symbols-outlined { font-size: 36px; opacity: 0.85; margin-top: 2px; flex-shrink: 0; }
    .card-label { font-size: 12px; font-weight: 500; opacity: 0.85; margin-bottom: 4px; }
    .card-value { font-size: 30px; font-weight: 800; line-height: 1; }

    .indigo  { background: linear-gradient(135deg, #4338ca, #6366f1); }
    .blue    { background: linear-gradient(135deg, #1d4ed8, #3b82f6); }
    .teal    { background: linear-gradient(135deg, #0d9488, #14b8a6); }
    .purple  { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
    .dark    { background: linear-gradient(135deg, #1e293b, #334155); }

    .loading { color: #6b7280; padding: 20px; }
    .error-msg { color: #ef4444; padding: 20px; }

    @media (max-width: 900px) { .cards { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 560px) { .cards { grid-template-columns: 1fr; } }
  `]
})
export class CourierDashboardComponent implements OnInit {
  data = signal<CourierDashboard | null>(null);
  cargando = signal(true);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    const token = localStorage.getItem('admin_token');
    this.http.get<CourierDashboard>(`${environment.apiBaseUrl}/courier/dashboard`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => { this.data.set(res); this.cargando.set(false); },
      error: (e) => { this.error.set(e.error?.detail ?? 'Error al cargar datos'); this.cargando.set(false); }
    });
  }

  fmt(v: number): string {
    return '$' + v.toLocaleString('es-CO');
  }
}
