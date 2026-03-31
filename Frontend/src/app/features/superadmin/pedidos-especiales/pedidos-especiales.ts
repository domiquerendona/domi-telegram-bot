import { Component, signal, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NgIf, NgFor, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { environment } from '../../../../environments/environment';

interface OrdenEspecial {
  id: number;
  created_at: string;
  status: string;
  total_fee: number;
  special_commission: number;
  platform_fee: number;
  tech_dev_fee: number;
  fee_admin_pagado: number;
  ganancia_neta: number;
  courier_name: string | null;
  customer_name: string | null;
  customer_barrio: string | null;
  customer_city: string | null;
  creator_admin_id: number | null;
}

interface Resumen {
  total_pedidos: number;
  entregados: number;
  cancelados: number;
  total_tarifas: number;
  total_comisiones: number;
  total_fees_admin: number;
  ganancia_neta: number;
}

interface MetricasResponse {
  periodo: string;
  resumen: Resumen;
  pedidos: OrdenEspecial[];
}

@Component({
  selector: 'app-pedidos-especiales',
  standalone: true,
  imports: [NgIf, NgFor, NgClass, FormsModule],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <h1>Pedidos especiales</h1>
          <p class="subtitle">Rentabilidad por periodo</p>
        </div>
        <button class="btn-refresh" (click)="cargar()">
          <span class="material-symbols-outlined">refresh</span>
          Actualizar
        </button>
      </div>

      <!-- Filtros -->
      <div class="filtros-row">
        <div class="periodo-tabs">
          <button *ngFor="let p of periodos"
                  [class.active]="periodo() === p.val"
                  (click)="setPeriodo(p.val)">
            {{ p.label }}
          </button>
        </div>
      </div>

      <!-- Estado de carga / error -->
      <div *ngIf="cargando()" class="estado">
        <span class="material-symbols-outlined spin">sync</span> Cargando...
      </div>
      <div *ngIf="error()" class="estado error">{{ error() }}</div>

      <!-- Tarjetas de resumen -->
      <div *ngIf="datos() && !cargando()" class="cards-grid">
        <div class="card card-blue">
          <span class="material-symbols-outlined">receipt_long</span>
          <div class="card-body">
            <div class="card-value">{{ datos()!.resumen.entregados }}</div>
            <div class="card-label">Entregados</div>
          </div>
        </div>
        <div class="card card-gray">
          <span class="material-symbols-outlined">cancel</span>
          <div class="card-body">
            <div class="card-value">{{ datos()!.resumen.cancelados }}</div>
            <div class="card-label">Cancelados</div>
          </div>
        </div>
        <div class="card card-purple">
          <span class="material-symbols-outlined">local_atm</span>
          <div class="card-body">
            <div class="card-value">{{ fmt(datos()!.resumen.total_tarifas) }}</div>
            <div class="card-label">Total tarifas cobradas</div>
          </div>
        </div>
        <div class="card card-indigo">
          <span class="material-symbols-outlined">handshake</span>
          <div class="card-body">
            <div class="card-value">{{ fmt(datos()!.resumen.total_comisiones) }}</div>
            <div class="card-label">Total comisiones al courier</div>
          </div>
        </div>
        <div class="card card-orange">
          <span class="material-symbols-outlined">account_balance</span>
          <div class="card-body">
            <div class="card-value">{{ fmt(datos()!.resumen.total_fees_admin) }}</div>
            <div class="card-label">Fees pagados a plataforma</div>
          </div>
        </div>
        <div class="card card-green">
          <span class="material-symbols-outlined">trending_up</span>
          <div class="card-body">
            <div class="card-value">{{ fmt(datos()!.resumen.ganancia_neta) }}</div>
            <div class="card-label">Ganancia neta del admin</div>
          </div>
        </div>
      </div>

      <!-- Tabla de pedidos -->
      <div *ngIf="datos() && !cargando() && datos()!.pedidos.length > 0" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Fecha</th>
              <th>Estado</th>
              <th>Cliente</th>
              <th>Courier</th>
              <th>Tarifa</th>
              <th>Comision</th>
              <th>Fees plataforma</th>
              <th>Ganancia neta</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let o of datos()!.pedidos">
              <td class="id-cell">#{{ o.id }}</td>
              <td>{{ fmtFecha(o.created_at) }}</td>
              <td>
                <span class="badge" [ngClass]="badgeStatus(o.status)">{{ o.status }}</span>
              </td>
              <td>
                <div>{{ o.customer_name || '—' }}</div>
                <div class="sub" *ngIf="o.customer_barrio">{{ o.customer_barrio }}, {{ o.customer_city }}</div>
              </td>
              <td>{{ o.courier_name || '—' }}</td>
              <td class="num">{{ fmt(o.total_fee) }}</td>
              <td class="num">{{ o.special_commission > 0 ? fmt(o.special_commission) : '—' }}</td>
              <td class="num fee-col">
                <ng-container *ngIf="o.status === 'DELIVERED'">
                  <span title="Plataforma: {{ fmt(o.platform_fee) }}{{ o.tech_dev_fee > 0 ? ' + Tech: ' + fmt(o.tech_dev_fee) : '' }}">
                    {{ fmt(o.fee_admin_pagado) }}
                  </span>
                </ng-container>
                <span *ngIf="o.status !== 'DELIVERED'" class="na">—</span>
              </td>
              <td class="num" [class.ganancia-pos]="o.ganancia_neta > 0" [class.ganancia-neg]="o.ganancia_neta < 0">
                {{ o.status === 'DELIVERED' ? fmt(o.ganancia_neta) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div *ngIf="datos() && !cargando() && datos()!.pedidos.length === 0" class="empty">
        No hay pedidos especiales en este periodo.
      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }

    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 20px;
    }
    h1 { font-size: 22px; font-weight: 700; color: #1e293b; margin: 0 0 4px; }
    .subtitle { font-size: 13px; color: #64748b; margin: 0; }

    .btn-refresh {
      display: flex; align-items: center; gap: 6px;
      background: #4338ca; color: white;
      border: none; border-radius: 8px;
      padding: 8px 16px; font-size: 14px; cursor: pointer;
    }
    .btn-refresh:hover { background: #3730a3; }

    .filtros-row { margin-bottom: 20px; }

    .periodo-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
    .periodo-tabs button {
      padding: 6px 14px; border-radius: 20px; border: 1.5px solid #cbd5e1;
      background: white; color: #475569; font-size: 13px; cursor: pointer;
      transition: all .15s;
    }
    .periodo-tabs button.active {
      background: #4338ca; color: white; border-color: #4338ca;
    }
    .periodo-tabs button:hover:not(.active) { border-color: #4338ca; color: #4338ca; }

    .estado {
      display: flex; align-items: center; gap: 8px;
      padding: 16px; color: #64748b; font-size: 14px;
    }
    .estado.error { color: #dc2626; }
    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .card {
      border-radius: 12px; padding: 18px 16px;
      display: flex; align-items: center; gap: 14px;
      color: white; box-shadow: 0 2px 8px rgba(0,0,0,.08);
    }
    .card .material-symbols-outlined { font-size: 28px; opacity: .85; }
    .card-body { min-width: 0; }
    .card-value { font-size: 20px; font-weight: 700; line-height: 1.2; }
    .card-label { font-size: 11px; opacity: .85; margin-top: 2px; }

    .card-blue   { background: linear-gradient(135deg,#3b82f6,#1d4ed8); }
    .card-gray   { background: linear-gradient(135deg,#94a3b8,#475569); }
    .card-purple { background: linear-gradient(135deg,#a855f7,#7c3aed); }
    .card-indigo { background: linear-gradient(135deg,#6366f1,#4338ca); }
    .card-orange { background: linear-gradient(135deg,#f97316,#ea580c); }
    .card-green  { background: linear-gradient(135deg,#22c55e,#16a34a); }

    .table-wrap {
      background: white; border-radius: 12px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow-x: auto;
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    thead th {
      padding: 12px 14px; text-align: left;
      background: #f8fafc; color: #475569; font-weight: 600;
      border-bottom: 1px solid #e2e8f0; white-space: nowrap;
    }
    tbody tr { border-bottom: 1px solid #f1f5f9; }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: #f8fafc; }
    td { padding: 10px 14px; color: #334155; vertical-align: top; }
    .id-cell { font-weight: 600; color: #4338ca; }
    .sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
    .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .fee-col { color: #dc2626; }
    .na { color: #cbd5e1; }
    .ganancia-pos { color: #16a34a; font-weight: 600; }
    .ganancia-neg { color: #dc2626; font-weight: 600; }

    .badge {
      display: inline-block; padding: 2px 10px; border-radius: 20px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .badge-delivered { background: #dcfce7; color: #15803d; }
    .badge-cancelled { background: #fee2e2; color: #b91c1c; }

    .empty {
      text-align: center; padding: 48px 16px;
      color: #94a3b8; font-size: 14px;
    }

    @media (max-width: 700px) {
      .page { padding: 12px; }
      .cards-grid { grid-template-columns: repeat(2, 1fr); }
    }
  `]
})
export class PedidosEspecialesComponent implements OnInit {
  datos = signal<MetricasResponse | null>(null);
  cargando = signal(false);
  error = signal('');
  periodo = signal('semana');

  periodos = [
    { val: 'hoy', label: 'Hoy' },
    { val: 'ayer', label: 'Ayer' },
    { val: 'semana', label: 'Esta semana' },
    { val: 'mes', label: 'Este mes' },
    { val: 'todo', label: 'Todo' },
  ];

  constructor(private http: HttpClient, public authService: AuthService) {}

  ngOnInit() { this.cargar(); }

  setPeriodo(p: string) {
    this.periodo.set(p);
    this.cargar();
  }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    const token = localStorage.getItem('admin_token');
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const url = `${environment.apiBaseUrl}/admin/pedidos-especiales/metricas?periodo=${this.periodo()}`;
    this.http.get<MetricasResponse>(url, { headers }).subscribe({
      next: (r) => { this.datos.set(r); this.cargando.set(false); },
      error: (e) => {
        this.error.set('Error al cargar datos: ' + (e?.error?.detail || e?.message || 'desconocido'));
        this.cargando.set(false);
      },
    });
  }

  fmt(n: number): string {
    if (n == null) return '—';
    return '$' + n.toLocaleString('es-CO');
  }

  fmtFecha(s: string): string {
    if (!s) return '—';
    const d = new Date(s);
    if (isNaN(d.getTime())) return s.slice(0, 10);
    return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  badgeStatus(status: string): Record<string, boolean> {
    return {
      'badge-delivered': status === 'DELIVERED',
      'badge-cancelled': status === 'CANCELLED',
    };
  }
}
