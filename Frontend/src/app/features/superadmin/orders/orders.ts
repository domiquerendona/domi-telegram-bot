import { Component, OnInit, OnDestroy, signal } from '@angular/core';
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
        <span class="total">{{ orders().length }} registros</span>
        <span class="auto-badge" *ngIf="filtroActivo() === 'ACTIVE'">↻ auto</span>
        <button class="btn-refresh" (click)="cargar(filtroActivo())">↻ Actualizar</button>
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
              <th>Aliado / Admin</th>
              <th>Repartidor</th>
              <th>Tarifa</th>
              <th>Estado</th>
              <th>Fecha</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let o of orders()">
              <td class="id-cell">#{{ o.id }}</td>
              <td>
                <div class="nombre">{{ o.customer_name }}</div>
                <div class="sub">{{ o.customer_phone }}</div>
              </td>
              <td>
                <div class="nombre">{{ o.customer_address }}</div>
                <div class="sub">{{ o.customer_city }}<span *ngIf="o.customer_barrio">, {{ o.customer_barrio }}</span></div>
              </td>
              <td>{{ o.ally_name || '(Admin)' }}</td>
              <td>
                <span *ngIf="o.courier_name">{{ o.courier_name }}</span>
                <span *ngIf="!o.courier_name" class="sin-courier">Sin asignar</span>
              </td>
              <td>
                <span class="fee">\${{ fmt(o.total_fee) }}</span>
                <span *ngIf="o.additional_incentive > 0" class="incentivo"> +\${{ fmt(o.additional_incentive) }}</span>
              </td>
              <td>
                <span class="badge" [ngClass]="o.status.toLowerCase()">{{ etiqueta(o.status) }}</span>
              </td>
              <td class="fecha">{{ formatDate(o.created_at) }}</td>
              <td>
                <button *ngIf="cancelable(o.status)" class="btn-cancel" (click)="cancelar(o)">Cancelar</button>
              </td>
            </tr>
            <tr *ngIf="orders().length === 0">
              <td colspan="9" class="vacio">No hay pedidos en este estado.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
    .total { font-size: 14px; color: #6b7280; }
    .auto-badge { font-size: 11px; color: #10b981; font-weight: 600; background: #d1fae5; padding: 2px 8px; border-radius: 10px; }
    .btn-refresh { margin-left: auto; padding: 6px 14px; border-radius: 8px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 13px; color: #374151; }
    .btn-refresh:hover { border-color: #4338ca; color: #4338ca; }

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
    .incentivo { font-size: 12px; color: #10b981; }
    .sin-courier { font-size: 12px; color: #f59e0b; font-weight: 600; }
    .fecha { font-size: 12px; color: #6b7280; white-space: nowrap; }

    .badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
    .badge.pending   { background: #fef3c7; color: #92400e; }
    .badge.published { background: #dbeafe; color: #1e40af; }
    .badge.accepted  { background: #ede9fe; color: #5b21b6; }
    .badge.picked_up { background: #fce7f3; color: #9d174d; }
    .badge.delivered { background: #d1fae5; color: #065f46; }
    .badge.cancelled { background: #fee2e2; color: #991b1b; }

    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 40px; }
    .btn-cancel { padding: 4px 12px; border-radius: 6px; border: 1px solid #fca5a5; background: #fff; color: #dc2626; font-size: 12px; cursor: pointer; font-weight: 600; }
    .btn-cancel:hover { background: #fee2e2; }
  `]
})
export class OrdersComponent implements OnInit, OnDestroy {
  orders = signal<Order[]>([]);
  cargando = signal(true);
  error = signal('');
  filtroActivo = signal('ACTIVE');

  private intervalo: any = null;

  filtroOpciones = [
    { label: 'Activos', valor: 'ACTIVE' },
    { label: 'Todos', valor: 'TODOS' },
    { label: 'Entregados', valor: 'DELIVERED' },
    { label: 'Cancelados', valor: 'CANCELLED' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.cargar('ACTIVE');
    this.intervalo = setInterval(() => {
      if (this.filtroActivo() === 'ACTIVE') this.cargar('ACTIVE');
    }, 30000);
  }

  ngOnDestroy() {
    if (this.intervalo) clearInterval(this.intervalo);
  }

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

  cancelable(status: string) {
    return ['PENDING', 'PUBLISHED', 'ACCEPTED'].includes(status);
  }

  cancelar(o: Order) {
    if (!confirm(`¿Cancelar pedido #${o.id} de ${o.customer_name}?`)) return;
    this.http.post(`http://localhost:8000/admin/orders/${o.id}/cancel`, {}).subscribe({
      next: () => this.cargar(this.filtroActivo()),
      error: (e) => alert(e.error?.detail ?? 'Error al cancelar el pedido'),
    });
  }

  etiqueta(s: string) {
    const map: Record<string, string> = {
      PENDING: 'Pendiente', PUBLISHED: 'Publicado', ACCEPTED: 'Aceptado',
      PICKED_UP: 'Recogido', DELIVERED: 'Entregado', CANCELLED: 'Cancelado',
    };
    return map[s] ?? s;
  }

  fmt(val: number) {
    if (!val) return '0';
    return val.toLocaleString('es-CO');
  }

  formatDate(dt: string) {
    if (!dt) return '—';
    return dt.slice(0, 16).replace('T', ' ');
  }
}
