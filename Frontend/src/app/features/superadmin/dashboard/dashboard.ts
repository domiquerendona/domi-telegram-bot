import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NgIf } from '@angular/common';

interface DashboardStats {
  admins: { total: number; activos: number; pendientes: number };
  couriers: { total: number; activos: number; pendientes: number };
  aliados: { total: number; activos: number; pendientes: number };
  pedidos: { activos: number; entregados_hoy: number; total_entregados: number };
  saldo_plataforma: number;
  ganancias_mes: number;
  ganancias_total: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NgIf],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Dashboard</h1>
        <button class="btn-refresh" (click)="cargar()">↻ Actualizar</button>
      </div>

      <div class="loading" *ngIf="cargando()">Cargando...</div>
      <div class="error-msg" *ngIf="error()">{{ error() }}</div>

      <div *ngIf="!cargando() && !error()">

        <!-- FILA 1: Pedidos -->
        <div class="section-label">Pedidos</div>
        <div class="cards">
          <div class="card indigo">
            <span class="material-symbols-outlined">local_shipping</span>
            <div>
              <div class="card-label">En curso</div>
              <div class="card-value">{{ s().pedidos.activos }}</div>
            </div>
          </div>
          <div class="card green">
            <span class="material-symbols-outlined">check_circle</span>
            <div>
              <div class="card-label">Entregados hoy</div>
              <div class="card-value">{{ s().pedidos.entregados_hoy }}</div>
            </div>
          </div>
          <div class="card teal">
            <span class="material-symbols-outlined">inventory_2</span>
            <div>
              <div class="card-label">Total entregados</div>
              <div class="card-value">{{ s().pedidos.total_entregados }}</div>
            </div>
          </div>
        </div>

        <!-- FILA 2: Finanzas -->
        <div class="section-label">Finanzas</div>
        <div class="cards">
          <div class="card dark">
            <span class="material-symbols-outlined">account_balance_wallet</span>
            <div>
              <div class="card-label">Saldo plataforma</div>
              <div class="card-value">{{ fmt(s().saldo_plataforma) }}</div>
            </div>
          </div>
          <div class="card purple">
            <span class="material-symbols-outlined">trending_up</span>
            <div>
              <div class="card-label">Ganancias este mes</div>
              <div class="card-value">{{ fmt(s().ganancias_mes) }}</div>
            </div>
          </div>
          <div class="card slate">
            <span class="material-symbols-outlined">leaderboard</span>
            <div>
              <div class="card-label">Ganancias totales</div>
              <div class="card-value">{{ fmt(s().ganancias_total) }}</div>
            </div>
          </div>
        </div>

        <!-- FILA 3: Equipo -->
        <div class="section-label">Equipo</div>
        <div class="cards">
          <div class="card blue">
            <span class="material-symbols-outlined">admin_panel_settings</span>
            <div>
              <div class="card-label">Administradores</div>
              <div class="card-value">{{ s().admins.activos }}<span class="sub-val"> / {{ s().admins.total }}</span></div>
              <div class="card-sub" *ngIf="s().admins.pendientes > 0">{{ s().admins.pendientes }} pendientes</div>
            </div>
          </div>
          <div class="card cyan">
            <span class="material-symbols-outlined">delivery_dining</span>
            <div>
              <div class="card-label">Repartidores</div>
              <div class="card-value">{{ s().couriers.activos }}<span class="sub-val"> / {{ s().couriers.total }}</span></div>
              <div class="card-sub" *ngIf="s().couriers.pendientes > 0">{{ s().couriers.pendientes }} pendientes</div>
            </div>
          </div>
          <div class="card orange">
            <span class="material-symbols-outlined">storefront</span>
            <div>
              <div class="card-label">Aliados</div>
              <div class="card-value">{{ s().aliados.activos }}<span class="sub-val"> / {{ s().aliados.total }}</span></div>
              <div class="card-sub" *ngIf="s().aliados.pendientes > 0">{{ s().aliados.pendientes }} pendientes</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
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
    .sub-val { font-size: 16px; font-weight: 500; opacity: 0.7; }
    .card-sub { font-size: 11px; margin-top: 6px; background: rgba(255,255,255,0.2); border-radius: 10px; padding: 2px 8px; display: inline-block; }

    .indigo  { background: linear-gradient(135deg, #4338ca, #6366f1); }
    .green   { background: linear-gradient(135deg, #059669, #10b981); }
    .teal    { background: linear-gradient(135deg, #0d9488, #14b8a6); }
    .dark    { background: linear-gradient(135deg, #1e293b, #334155); }
    .purple  { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
    .slate   { background: linear-gradient(135deg, #475569, #64748b); }
    .blue    { background: linear-gradient(135deg, #1d4ed8, #3b82f6); }
    .cyan    { background: linear-gradient(135deg, #0891b2, #06b6d4); }
    .orange  { background: linear-gradient(135deg, #d97706, #f59e0b); }

    .loading { color: #6b7280; padding: 20px; }
    .error-msg { color: #ef4444; padding: 20px; }

    @media (max-width: 900px) {
      .cards { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 560px) {
      .cards { grid-template-columns: 1fr; }
    }
  `]
})
export class DashboardComponent implements OnInit {
  private _stats = signal<DashboardStats | null>(null);
  cargando = signal(true);
  error = signal('');

  s() {
    return this._stats()!;
  }

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<DashboardStats>('http://localhost:8000/dashboard/stats').subscribe({
      next: (d) => { this._stats.set(d); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  fmt(val: number) {
    if (!val) return '$0';
    return '$' + val.toLocaleString('es-CO');
  }
}
