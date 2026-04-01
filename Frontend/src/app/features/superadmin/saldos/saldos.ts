import { Component, OnInit, signal } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface BalanceRow {
  id: number;
  nombre: string;
  balance: number;
  status: string;
  ciudad: string;
  admin_nombre?: string;
}

interface SaldosData {
  admins: BalanceRow[];
  couriers: BalanceRow[];
  aliados: BalanceRow[];
}

@Component({
  selector: 'app-saldos',
  standalone: true,
  imports: [NgFor, NgIf, NgClass],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Saldos</h1>
        <button class="btn-refresh" (click)="cargar()">↻ Actualizar</button>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div *ngIf="!cargando() && !error()">

        <!-- ADMINS -->
        <div class="seccion">
          <div class="seccion-header">
            <span class="material-symbols-outlined">admin_panel_settings</span>
            <h2>Administradores</h2>
            <span class="chip">{{ data().admins.length }}</span>
          </div>
          <div class="tabla-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Ciudad</th>
                  <th>Estado</th>
                  <th class="col-balance">Saldo</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let r of data().admins" [class.bajo]="r.balance < 10000">
                  <td class="nombre">{{ r.nombre }}</td>
                  <td>{{ r.ciudad || '—' }}</td>
                  <td><span class="badge" [ngClass]="r.status.toLowerCase()">{{ etiqueta(r.status) }}</span></td>
                  <td class="balance" [class.cero]="r.balance === 0">{{ formatBalance(r.balance) }}</td>
                </tr>
                <tr *ngIf="data().admins.length === 0">
                  <td colspan="4" class="vacio">Sin registros.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- REPARTIDORES -->
        <div class="seccion">
          <div class="seccion-header">
            <span class="material-symbols-outlined">delivery_dining</span>
            <h2>Repartidores</h2>
            <span class="chip">{{ data().couriers.length }}</span>
          </div>
          <div class="tabla-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Ciudad</th>
                  <th>Equipo (Admin)</th>
                  <th>Estado</th>
                  <th class="col-balance">Saldo</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let r of data().couriers" [class.bajo]="r.balance < 5000">
                  <td class="nombre">{{ r.nombre }}</td>
                  <td>{{ r.ciudad || '—' }}</td>
                  <td class="sub-text">{{ r.admin_nombre || '—' }}</td>
                  <td><span class="badge" [ngClass]="r.status.toLowerCase()">{{ etiqueta(r.status) }}</span></td>
                  <td class="balance" [class.cero]="r.balance === 0">{{ formatBalance(r.balance) }}</td>
                </tr>
                <tr *ngIf="data().couriers.length === 0">
                  <td colspan="5" class="vacio">Sin repartidores con saldo activo.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ALIADOS -->
        <div class="seccion">
          <div class="seccion-header">
            <span class="material-symbols-outlined">storefront</span>
            <h2>Aliados</h2>
            <span class="chip">{{ data().aliados.length }}</span>
          </div>
          <div class="tabla-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Negocio</th>
                  <th>Ciudad</th>
                  <th>Equipo (Admin)</th>
                  <th>Estado</th>
                  <th class="col-balance">Saldo</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let r of data().aliados" [class.bajo]="r.balance < 5000">
                  <td class="nombre">{{ r.nombre }}</td>
                  <td>{{ r.ciudad || '—' }}</td>
                  <td class="sub-text">{{ r.admin_nombre || '—' }}</td>
                  <td><span class="badge" [ngClass]="r.status.toLowerCase()">{{ etiqueta(r.status) }}</span></td>
                  <td class="balance" [class.cero]="r.balance === 0">{{ formatBalance(r.balance) }}</td>
                </tr>
                <tr *ngIf="data().aliados.length === 0">
                  <td colspan="5" class="vacio">Sin aliados con saldo activo.</td>
                </tr>
              </tbody>
            </table>
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

    .seccion { margin-bottom: 32px; }
    .seccion-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
    .seccion-header span.material-symbols-outlined { font-size: 22px; color: #4338ca; }
    h2 { font-size: 17px; font-weight: 700; margin: 0; color: #111827; }
    .chip { background: #e0e7ff; color: #3730a3; font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 12px; }

    .tabla-wrapper { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #f9fafb; }
    th { padding: 11px 16px; text-align: left; font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e5e7eb; }
    td { padding: 13px 16px; font-size: 14px; color: #111827; border-bottom: 1px solid #f3f4f6; }
    .nombre { font-weight: 600; }
    .sub-text { color: #6b7280; font-size: 13px; }
    .col-balance { text-align: right; }
    .balance { text-align: right; font-weight: 700; font-size: 15px; color: #059669; font-variant-numeric: tabular-nums; }
    .balance.cero { color: #9ca3af; font-weight: 500; }
    tr.bajo td.balance { color: #d97706; }
    tr.bajo.cero td.balance { color: #9ca3af; }

    .badge { padding: 3px 9px; border-radius: 12px; font-size: 11px; font-weight: 600; }
    .badge.approved { background: #d1fae5; color: #065f46; }
    .badge.inactive { background: #f3f4f6; color: #6b7280; }
    .badge.pending  { background: #fef3c7; color: #92400e; }
    .badge.rejected { background: #fee2e2; color: #991b1b; }

    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 32px; }
  `]
})
export class SaldosComponent implements OnInit {
  data = signal<SaldosData>({ admins: [], couriers: [], aliados: [] });
  cargando = signal(true);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<SaldosData>(`${environment.apiBaseUrl}/admin/saldos`).subscribe({
      next: (d) => { this.data.set(d); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  etiqueta(s: string) {
    return { APPROVED: 'Aprobado', INACTIVE: 'Inactivo', PENDING: 'Pendiente', REJECTED: 'Rechazado' }[s] ?? s;
  }

  formatBalance(val: number) {
    if (!val) return '$0';
    return '$' + val.toLocaleString('es-CO');
  }
}
