import { Component, OnInit, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { FormatMoneyPipe } from '../../../core/pipes/format-money.pipe';
import { fmtFecha } from '../../../core/utils/fecha';

interface Resumen {
  hoy: number;
  semana: number;
  mes: number;
  total: number;
}

interface AdminGanancia {
  nombre: string;
  total: number;
}

interface MovimientoLedger {
  id: number;
  kind: string;
  amount: number;
  from_type: string;
  note: string;
  created_at: string;
  admin_nombre: string;
}

interface GananciasData {
  resumen: Resumen;
  por_admin: AdminGanancia[];
  historial: MovimientoLedger[];
}

@Component({
  selector: 'app-ganancias',
  standalone: true,
  imports: [NgFor, NgIf, FormatMoneyPipe],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Ganancias</h1>
        <button class="btn-refresh" (click)="cargar()">↻ Actualizar</button>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div *ngIf="!cargando() && !error()">

        <!-- TARJETAS RESUMEN -->
        <div class="cards">
          <div class="card">
            <div class="card-label">Hoy</div>
            <div class="card-value">{{ data().resumen.hoy | fmtMoney }}</div>
          </div>
          <div class="card">
            <div class="card-label">Esta semana</div>
            <div class="card-value">{{ data().resumen.semana | fmtMoney }}</div>
          </div>
          <div class="card accent">
            <div class="card-label">Este mes</div>
            <div class="card-value">{{ data().resumen.mes | fmtMoney }}</div>
          </div>
          <div class="card dark">
            <div class="card-label">Total histórico</div>
            <div class="card-value">{{ data().resumen.total | fmtMoney }}</div>
          </div>
        </div>

        <div class="cols">

          <!-- POR ADMIN -->
          <div class="col-panel">
            <div class="panel-header">
              <span class="material-symbols-outlined">leaderboard</span>
              <h2>Por administrador</h2>
            </div>
            <div class="tabla-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Administrador</th>
                    <th class="col-right">Total ganado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let r of data().por_admin; let i = index">
                    <td>
                      <span class="rank">{{ i + 1 }}</span>
                      {{ r.nombre }}
                    </td>
                    <td class="monto">{{ r.total | fmtMoney }}</td>
                  </tr>
                  <tr *ngIf="data().por_admin.length === 0">
                    <td colspan="2" class="vacio">Sin ganancias aún.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- HISTORIAL -->
          <div class="col-panel wide">
            <div class="panel-header">
              <span class="material-symbols-outlined">receipt_long</span>
              <h2>Historial reciente</h2>
            </div>
            <div class="tabla-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Admin</th>
                    <th>Nota</th>
                    <th class="col-right">Monto</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let h of data().historial">
                    <td><span class="kind-badge" [class]="kindClass(h.kind)">{{ kindLabel(h.kind) }}</span></td>
                    <td class="sub-text">{{ h.admin_nombre || '—' }}</td>
                    <td class="nota">{{ h.note || '—' }}</td>
                    <td class="monto">{{ h.amount | fmtMoney }}</td>
                    <td class="fecha">{{ fmtFecha(h.created_at) }}</td>
                  </tr>
                  <tr *ngIf="data().historial.length === 0">
                    <td colspan="5" class="vacio">Sin movimientos.</td>
                  </tr>
                </tbody>
              </table>
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

    /* Tarjetas */
    .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
    .card { background: white; border-radius: 12px; padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); border-left: 4px solid #e5e7eb; }
    .card.accent { border-left-color: #4338ca; }
    .card.dark { border-left-color: #059669; background: #f0fdf4; }
    .card-label { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .card-value { font-size: 24px; font-weight: 800; color: #111827; }
    .card.dark .card-value { color: #059669; }

    /* Layout dos columnas */
    .cols { display: flex; gap: 20px; align-items: flex-start; }
    .col-panel { flex: 0 0 280px; }
    .col-panel.wide { flex: 1; min-width: 0; }

    .panel-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
    .panel-header span { font-size: 20px; color: #4338ca; }
    h2 { font-size: 16px; font-weight: 700; margin: 0; color: #111827; }

    .tabla-wrapper { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #f9fafb; }
    th { padding: 11px 16px; text-align: left; font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
    .col-right { text-align: right; }
    td { padding: 12px 16px; font-size: 14px; color: #111827; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
    .rank { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; background: #e0e7ff; color: #3730a3; border-radius: 50%; font-size: 11px; font-weight: 700; margin-right: 8px; }
    .monto { text-align: right; font-weight: 700; color: #059669; font-variant-numeric: tabular-nums; }
    .sub-text { color: #6b7280; font-size: 13px; }
    .nota { color: #6b7280; font-size: 12px; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .fecha { font-size: 12px; color: #9ca3af; white-space: nowrap; }

    .kind-badge { padding: 3px 9px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }
    .kind-badge.fee { background: #d1fae5; color: #065f46; }
    .kind-badge.platform { background: #dbeafe; color: #1e40af; }
    .kind-badge.income { background: #fef3c7; color: #92400e; }

    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 32px; }

    @media (max-width: 900px) {
      .cards { grid-template-columns: repeat(2, 1fr); }
      .cols { flex-direction: column; }
      .col-panel { flex: unset; width: 100%; }
    }
  `]
})
export class GananciasComponent implements OnInit {
  data = signal<GananciasData>({
    resumen: { hoy: 0, semana: 0, mes: 0, total: 0 },
    por_admin: [],
    historial: [],
  });
  cargando = signal(true);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<GananciasData>(`${environment.apiBaseUrl}/admin/ganancias`).subscribe({
      next: (d) => { this.data.set(d); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  fmtFecha = fmtFecha;

  kindLabel(kind: string) {
    return { FEE_INCOME: 'Comisión', PLATFORM_FEE: 'Fee plataforma', INCOME: 'Ingreso externo' }[kind] ?? kind;
  }

  kindClass(kind: string) {
    return { FEE_INCOME: 'fee', PLATFORM_FEE: 'platform', INCOME: 'income' }[kind] ?? '';
  }
}
