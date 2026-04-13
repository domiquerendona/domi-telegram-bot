import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { FormatMoneyPipe } from '../../../core/pipes/format-money.pipe';
import { fmtFecha } from '../../../core/utils/fecha';

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
  imports: [FormatMoneyPipe],
  template: `
  <div class="page">
    <div class="page-header">
      <h1>Mis Ganancias</h1>
    </div>

    <div class="period-tabs">
      @for (p of periods; track p.value) {
        <button [class.active]="period() === p.value" (click)="loadPeriod(p.value)">
          {{ p.label }}
        </button>
      }
    </div>

    @if (cargando()) { <div class="loading">Cargando...</div> }
    @if (error()) { <div class="error-msg">{{ error() }}</div> }

    @if (data()) {
      <div class="summary-cards">
        <div class="scard indigo">
          <span class="material-symbols-outlined">package_2</span>
          <div>
            <div class="slabel">Entregas</div>
            <div class="svalue">{{ data()!.count }}</div>
          </div>
        </div>
        <div class="scard blue">
          <span class="material-symbols-outlined">payments</span>
          <div>
            <div class="slabel">Tarifa total</div>
            <div class="svalue">{{ data()!.total_tarifa | fmtMoney }}</div>
          </div>
        </div>
        <div class="scard teal">
          <span class="material-symbols-outlined">star</span>
          <div>
            <div class="slabel">Incentivos</div>
            <div class="svalue">{{ data()!.total_incentivo | fmtMoney }}</div>
          </div>
        </div>
        <div class="scard purple">
          <span class="material-symbols-outlined">trending_up</span>
          <div>
            <div class="slabel">Total ganado</div>
            <div class="svalue">{{ data()!.total | fmtMoney }}</div>
          </div>
        </div>
      </div>

      @if (data()!.orders.length === 0) {
        <div class="empty">No hay entregas en este periodo.</div>
      }

      @if (data()!.orders.length > 0) {
        <div class="table-wrapper">
          <table>
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
              @for (o of data()!.orders; track o.order_id) {
                <tr>
                  <td>{{ fmtFecha(o.delivered_at) }}</td>
                  <td>{{ o.ally_name }}</td>
                  <td>{{ o.dropoff_city }}</td>
                  <td>{{ o.total_fee | fmtMoney }}</td>
                  <td>{{ o.incentivo | fmtMoney }}</td>
                  <td class="total-col">{{ (o.total_fee + o.incentivo) | fmtMoney }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    }
  </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; color: #111827; }

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

    .period-tabs button:hover { border-color: #4338ca; color: #4338ca; }

    .period-tabs button.active {
      background: #4338ca;
      border-color: #4338ca;
      color: white;
    }

    .summary-cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }

    .scard {
      border-radius: 14px;
      padding: 20px 22px;
      color: white;
      display: flex;
      align-items: flex-start;
      gap: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }

    .scard .material-symbols-outlined { font-size: 32px; opacity: 0.85; flex-shrink: 0; margin-top: 2px; }
    .slabel { font-size: 12px; font-weight: 500; opacity: 0.85; margin-bottom: 4px; }
    .svalue { font-size: 24px; font-weight: 800; line-height: 1; }

    .indigo  { background: linear-gradient(135deg, #4338ca, #6366f1); }
    .blue    { background: linear-gradient(135deg, #1d4ed8, #3b82f6); }
    .teal    { background: linear-gradient(135deg, #0d9488, #14b8a6); }
    .purple  { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }

    .loading { color: #6b7280; padding: 20px; }
    .error-msg { color: #ef4444; padding: 20px; }
    .empty { color: #6b7280; padding: 20px 0; }

    .table-wrapper {
      background: white;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    }

    table { width: 100%; border-collapse: collapse; }

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
    .total-col { font-weight: 700; color: #4338ca; }

    @media (max-width: 900px) { .summary-cards { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 560px) { .summary-cards { grid-template-columns: 1fr; } }
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
    this.http.get<EarningsResponse>(`${environment.apiBaseUrl}/courier/earnings?period=${p}`).subscribe({
      next: (res) => { this.data.set(res); this.cargando.set(false); },
      error: (e) => { this.error.set(e.error?.detail ?? 'Error al cargar ganancias'); this.cargando.set(false); }
    });
  }

  fmtFecha = fmtFecha;
}
