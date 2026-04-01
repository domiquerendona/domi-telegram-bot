import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NgIf, NgFor } from '@angular/common';
import { environment } from '../../../../environments/environment';

interface OrderEarning {
  order_id: number;
  delivered_at: string;
  total_fee: number;
  incentivo: number;
  ally_name: string;
  dropoff_city: string;
}

interface EarningsResponse {
  period: string;
  orders: OrderEarning[];
  total_tarifa: number;
  total_incentivo: number;
  total: number;
  count: number;
}

@Component({
  selector: 'app-courier-ganancias',
  standalone: true,
  imports: [NgIf, NgFor],
  template: `
  <div class="page">
    <h2 class="title">Mis Ganancias</h2>

    <div class="period-tabs">
      <button
        *ngFor="let p of periods"
        [class.active]="period() === p.value"
        (click)="loadPeriod(p.value)">
        {{ p.label }}
      </button>
    </div>

    <div *ngIf="cargando()" class="loading">Cargando...</div>
    <div *ngIf="error()" class="error">{{ error() }}</div>

    <div *ngIf="data()">
      <div class="summary-cards">
        <div class="scard">
          <span class="slabel">Entregas</span>
          <span class="svalue">{{ data()!.count }}</span>
        </div>
        <div class="scard">
          <span class="slabel">Tarifa total</span>
          <span class="svalue">{{ formatCop(data()!.total_tarifa) }}</span>
        </div>
        <div class="scard">
          <span class="slabel">Incentivos</span>
          <span class="svalue">{{ formatCop(data()!.total_incentivo) }}</span>
        </div>
        <div class="scard highlight">
          <span class="slabel">Total ganado</span>
          <span class="svalue">{{ formatCop(data()!.total) }}</span>
        </div>
      </div>

      <div *ngIf="data()!.orders.length === 0" class="empty">
        No hay entregas en este periodo.
      </div>

      <table *ngIf="data()!.orders.length > 0">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Aliado</th>
            <th>Ciudad entrega</th>
            <th>Tarifa</th>
            <th>Incentivo</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let o of data()!.orders">
            <td>{{ formatDate(o.delivered_at) }}</td>
            <td>{{ o.ally_name }}</td>
            <td>{{ o.dropoff_city }}</td>
            <td>{{ formatCop(o.total_fee) }}</td>
            <td>{{ formatCop(o.incentivo) }}</td>
            <td class="total-col">{{ formatCop(o.total_fee + o.incentivo) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  `,
  styles: [`
  .page { max-width: 960px; }
  .title { font-size: 22px; font-weight: 700; color: #1f2937; margin-bottom: 20px; }
  .loading { color: #6b7280; }
  .error { color: #dc2626; background: #fef2f2; padding: 12px; border-radius: 8px; }
  .empty { color: #6b7280; padding: 20px 0; }

  .period-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
  }

  .period-tabs button {
    padding: 8px 20px;
    border: 1.5px solid #d1d5db;
    border-radius: 20px;
    background: white;
    color: #374151;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .period-tabs button.active {
    background: #059669;
    border-color: #059669;
    color: white;
  }

  .summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .scard {
    background: white;
    border-radius: 12px;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  }

  .scard.highlight { border: 2px solid #059669; }

  .slabel { font-size: 12px; color: #6b7280; }
  .svalue { font-size: 20px; font-weight: 700; color: #111827; }

  table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }

  th {
    text-align: left;
    padding: 12px 16px;
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }

  td {
    padding: 12px 16px;
    font-size: 14px;
    color: #374151;
    border-bottom: 1px solid #f3f4f6;
  }

  tr:last-child td { border-bottom: none; }

  .total-col { font-weight: 700; color: #059669; }
  `]
})
export class CourierGananciasComponent implements OnInit {
  data = signal<EarningsResponse | null>(null);
  cargando = signal(true);
  error = signal('');
  period = signal('mes');

  periods = [
    { value: 'hoy', label: 'Hoy' },
    { value: 'semana', label: 'Esta semana' },
    { value: 'mes', label: 'Este mes' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() { this.loadPeriod('mes'); }

  loadPeriod(p: string) {
    this.period.set(p);
    this.cargando.set(true);
    this.error.set('');
    const token = localStorage.getItem('admin_token');
    this.http.get<EarningsResponse>(`${environment.apiBaseUrl}/courier/earnings?period=${p}`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => { this.data.set(res); this.cargando.set(false); },
      error: (e) => { this.error.set(e.error?.detail ?? 'Error al cargar ganancias'); this.cargando.set(false); }
    });
  }

  formatCop(v: number): string {
    return '$' + v.toLocaleString('es-CO');
  }

  formatDate(s: string): string {
    if (!s) return '';
    return new Date(s).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
