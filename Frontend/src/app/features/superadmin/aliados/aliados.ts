import { Component, OnInit, signal, inject } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmService } from '../../../core/services/confirm.service';

interface Ally {
  id: number;
  business_name: string;
  owner_name: string;
  phone: string;
  city: string;
  barrio: string;
  status: string;
  address: string;
}

@Component({
  selector: 'app-aliados',
  standalone: true,
  imports: [NgFor, NgIf, NgClass, FormsModule],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Aliados</h1>
        <span class="total">{{ filtrados().length }} registros</span>
      </div>

      <div class="controles">
        <div class="filtros">
          <button *ngFor="let f of filtroOpciones"
            [class.activo]="filtroActivo() === f.valor"
            (click)="setFiltro(f.valor)">
            {{ f.label }}
          </button>
        </div>
        <div class="buscador">
          <span class="material-icons icono-buscar">search</span>
          <input
            type="text"
            [(ngModel)]="busqueda"
            placeholder="Buscar por negocio, propietario, teléfono o ciudad..."
            class="input-buscar" />
          <button *ngIf="busqueda" class="btn-limpiar" (click)="busqueda = ''">
            <span class="material-icons">close</span>
          </button>
        </div>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div class="tabla-wrapper" *ngIf="!cargando() && !error()">
        <table>
          <thead>
            <tr>
              <th>Negocio</th>
              <th>Propietario</th>
              <th>Teléfono</th>
              <th>Ciudad</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let a of filtrados()">
              <td>
                <div class="nombre">{{ a.business_name }}</div>
                <div class="sub">{{ a.address }}</div>
              </td>
              <td>{{ a.owner_name }}</td>
              <td>{{ a.phone }}</td>
              <td>{{ a.city }}<span *ngIf="a.barrio">, {{ a.barrio }}</span></td>
              <td>
                <span class="badge" [ngClass]="a.status.toLowerCase()">
                  {{ etiqueta(a.status) }}
                </span>
              </td>
              <td class="acciones">
                <button *ngIf="a.status === 'PENDING'" class="btn aprobar" (click)="accion(a, 'approve')">Aprobar</button>
                <button *ngIf="a.status === 'PENDING'" class="btn rechazar" (click)="accion(a, 'reject')">Rechazar</button>
                <button *ngIf="a.status === 'APPROVED'" class="btn inactivar" (click)="accion(a, 'deactivate')">Inactivar</button>
                <button *ngIf="a.status === 'INACTIVE'" class="btn reactivar" (click)="accion(a, 'reactivate')">Reactivar</button>
                <span *ngIf="a.status === 'REJECTED'" class="sin-accion">—</span>
              </td>
            </tr>
            <tr *ngIf="filtrados().length === 0">
              <td colspan="6" class="vacio">
                {{ busqueda ? 'Sin resultados para "' + busqueda + '"' : 'No hay aliados en este estado.' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
    .total { font-size: 14px; color: #6b7280; }

    .controles { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }

    .filtros { display: flex; gap: 8px; flex-wrap: wrap; }
    .filtros button { padding: 6px 16px; border-radius: 20px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 13px; color: #374151; transition: all 0.15s; }
    .filtros button:hover { border-color: #4338ca; color: #4338ca; }
    .filtros button.activo { background: #4338ca; color: white; border-color: #4338ca; }

    .buscador { position: relative; display: flex; align-items: center; max-width: 440px; }
    .icono-buscar { position: absolute; left: 10px; font-size: 18px; color: #9ca3af; }
    .input-buscar { width: 100%; padding: 8px 36px 8px 36px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; outline: none; transition: border-color .15s; background: white; }
    .input-buscar:focus { border-color: #4338ca; }
    .btn-limpiar { position: absolute; right: 6px; background: none; border: none; cursor: pointer; color: #9ca3af; display: flex; align-items: center; padding: 2px; }
    .btn-limpiar:hover { color: #374151; }
    .btn-limpiar .material-icons { font-size: 16px; }

    .tabla-wrapper { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #f9fafb; }
    th { padding: 12px 16px; text-align: left; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e5e7eb; }
    td { padding: 14px 16px; font-size: 14px; color: #111827; border-bottom: 1px solid #f3f4f6; }
    .nombre { font-weight: 600; }
    .sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    .badge.pending  { background: #fef3c7; color: #92400e; }
    .badge.approved { background: #d1fae5; color: #065f46; }
    .badge.inactive { background: #f3f4f6; color: #6b7280; }
    .badge.rejected { background: #fee2e2; color: #991b1b; }
    .acciones { display: flex; gap: 8px; align-items: center; }
    .btn { padding: 5px 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; transition: opacity 0.15s; }
    .btn:hover { opacity: 0.85; }
    .aprobar   { background: #10b981; color: white; }
    .rechazar  { background: #ef4444; color: white; }
    .inactivar { background: #f59e0b; color: white; }
    .reactivar { background: #3b82f6; color: white; }
    .sin-accion { color: #d1d5db; }
    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 40px; }
  `]
})
export class AliadosComponent implements OnInit {
  allies       = signal<Ally[]>([]);
  cargando     = signal(true);
  error        = signal('');
  filtroActivo = signal('PENDING');
  busqueda     = '';

  filtroOpciones = [
    { label: 'Pendientes', valor: 'PENDING' },
    { label: 'Aprobados',  valor: 'APPROVED' },
    { label: 'Inactivos',  valor: 'INACTIVE' },
    { label: 'Rechazados', valor: 'REJECTED' },
    { label: 'Todos',      valor: 'TODOS' },
  ];

  private toast   = inject(ToastService);
  private confirm = inject(ConfirmService);
  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<Ally[]>(`${environment.apiBaseUrl}/admin/allies`).subscribe({
      next: (data) => { this.allies.set(data); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  setFiltro(valor: string) {
    this.filtroActivo.set(valor);
    this.busqueda = '';
  }

  filtrados() {
    const f   = this.filtroActivo();
    const q   = this.busqueda.toLowerCase().trim();
    let lista = f === 'TODOS' ? this.allies() : this.allies().filter(a => a.status === f);
    if (q) {
      lista = lista.filter(a =>
        (a.business_name ?? '').toLowerCase().includes(q) ||
        (a.owner_name ?? '').toLowerCase().includes(q) ||
        (a.phone ?? '').includes(q) ||
        (a.city ?? '').toLowerCase().includes(q) ||
        (a.barrio ?? '').toLowerCase().includes(q)
      );
    }
    return lista;
  }

  etiqueta(s: string) {
    return { PENDING: 'Pendiente', APPROVED: 'Aprobado', INACTIVE: 'Inactivo', REJECTED: 'Rechazado' }[s] ?? s;
  }

  async accion(a: Ally, tipo: string) {
    const labels: Record<string, string> = {
      approve: 'Aprobar', reject: 'Rechazar', deactivate: 'Inactivar', reactivate: 'Reactivar'
    };
    const label = labels[tipo] ?? tipo;
    const ok = await this.confirm.ask(`¿${label} a ${a.business_name}?`, label);
    if (!ok) return;
    this.http.post(`${environment.apiBaseUrl}/admin/allies/${a.id}/${tipo}`, {}).subscribe({
      next: () => { this.toast.success(`${label} ejecutado correctamente.`); this.cargar(); },
      error: (e) => this.toast.error(e.error?.detail ?? 'Error al ejecutar la acción.')
    });
  }
}
