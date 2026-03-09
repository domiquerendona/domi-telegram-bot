import { Component, OnInit, signal } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { HttpClient } from '@angular/common/http';

interface Order {
  id: number;
  status: string;
  customer_name: string;
  customer_phone: string;
  customer_address: string;
  customer_city: string;
  customer_barrio: string;
  total_fee: number;
  additional_incentive: number;
  courier_name: string;
  ally_name: string;
  created_at: string;
  delivered_at: string;
  canceled_at: string;
}

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [NgFor, NgIf, NgClass],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Pedidos</h1>
        <span class="total">{{ filtrados().length }} registros</span>
      </div>

      <div class="filtros">
        <button *ngFor="let f of filtroOpciones"
          [class.activo]="filtroActivo() === f.valor"
          (click)="setFiltro(f.valor)">
          {{ f.label }}
        </button>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div class="tabla-wrapper" *ngIf="!cargando() && !error()">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Cliente</th>
              <th>Destino</th>
              <th>Aliado</th>
              <th>Repartidor</th>
              <th>Tarifa</th>
              <th>Estado</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let o of filtrados()">
              <td class="id-cell">{{ o.id }}</td>
              <td>
                <div class="nombre">{{ o.customer_name }}</div>
                <div class="sub">{{ o.customer_phone }}</div>
              </td>
              <td>
                <div class="nombre">{{ o.customer_address }}</div>
                <div class="sub">{{ o.customer_city }}, {{ o.customer_barrio }}</div>
              </td>
              <td>{{ o.ally_name || '—' }}</td>
              <td>{{ o.courier_name || '—' }}</td>
              <td>
                <span class="fee">\${{ formatFee(o.total_fee) }}</span>
                <span *ngIf="o.additional_incentive > 0" class="incentivo">
                  +\${{ formatFee(o.additional_incentive) }}
                </span>
              </td>
              <td>
                <span class="badge" [ngClass]="o.status.toLowerCase()">
                  {{ etiqueta(o.status) }}
                </span>
              </td>
              <td class="fecha">{{ formatDate(o.created_at) }}</td>
            </tr>
            <tr *ngIf="filtrados().length === 0">
              <td colspan="8" class="vacio">No hay pedidos en este estado.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 20px; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
    .total { font-size: 14px; color: #6b7280; }
    .filtros { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
    .filtros button { padding: 6px 16px; border-radius: 20px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 13px; color: #374151; transition: all 0.15s; }
    .filtros button:hover { border-color: #4338ca; color: #4338ca; }
    .filtros button.activo { background: #4338ca; color: white; border-color: #4338ca; }
    .tabla-wrapper { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 900px; }
    thead { background: #f9fafb; }
    th { padding: 12px 16px; text-align: left; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
    td { padding: 14px 16px; font-size: 14px; color: #111827; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
    .id-cell { color: #9ca3af; font-size: 13px; font-weight: 600; }
    .nombre { font-weight: 600; }
    .sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
    .fee { font-weight: 600; }
    .incentivo { font-size: 12px; color: #10b981; margin-left: 4px; }
    .fecha { font-size: 12px; color: #6b7280; white-space: nowrap; }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
    .badge.pending    { background: #fef3c7; color: #92400e; }
    .badge.published  { background: #dbeafe; color: #1e40af; }
    .badge.accepted   { background: #ede9fe; color: #5b21b6; }
    .badge.picked_up  { background: #fce7f3; color: #9d174d; }
    .badge.delivered  { background: #d1fae5; color: #065f46; }
    .badge.cancelled  { background: #fee2e2; color: #991b1b; }
    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 40px; }
  `]
})
export class OrdersComponent implements OnInit {
  orders = signal<Order[]>([]);
  cargando = signal(true);
  error = signal('');
  filtroActivo = signal('TODOS');

  filtroOpciones = [
    { label: 'Todos', valor: 'TODOS' },
    { label: 'Activos', valor: 'ACTIVE' },
    { label: 'Entregados', valor: 'DELIVERED' },
    { label: 'Cancelados', valor: 'CANCELLED' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar('TODOS'); }

  setFiltro(valor: string) {
    this.filtroActivo.set(valor);
    this.cargar(valor);
  }

  cargar(filtro: string) {
    this.cargando.set(true);
    this.error.set('');
    const params = filtro !== 'TODOS' ? `?status=${filtro}` : '';
    this.http.get<Order[]>(`http://localhost:8000/admin/orders${params}`).subscribe({
      next: (data) => { this.orders.set(data); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  filtrados() {
    return this.orders();
  }

  etiqueta(s: string) {
    const map: Record<string, string> = {
      PENDING: 'Pendiente', PUBLISHED: 'Publicado', ACCEPTED: 'Aceptado',
      PICKED_UP: 'Recogido', DELIVERED: 'Entregado', CANCELLED: 'Cancelado',
    };
    return map[s] ?? s;
  }

  formatFee(val: number) {
    return val.toLocaleString('es-CO');
  }

  formatDate(dt: string) {
    if (!dt) return '—';
    return dt.slice(0, 16).replace('T', ' ');
  }
}
