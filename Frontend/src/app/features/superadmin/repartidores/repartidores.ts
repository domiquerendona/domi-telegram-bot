import { Component, OnInit, signal } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { HttpClient } from '@angular/common/http';

interface Courier {
  id: number;
  full_name: string;
  phone: string;
  city: string;
  barrio: string;
  status: string;
  id_number: string;
  plate: string;
  bike_type: string;
}

@Component({
  selector: 'app-repartidores',
  standalone: true,
  imports: [NgFor, NgIf, NgClass],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Repartidores</h1>
        <span class="total">{{ filtrados().length }} registros</span>
      </div>

      <div class="filtros">
        <button *ngFor="let f of filtroOpciones"
          [class.activo]="filtroActivo() === f.valor"
          (click)="filtroActivo.set(f.valor)">
          {{ f.label }}
        </button>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div class="tabla-wrapper" *ngIf="!cargando() && !error()">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Ciudad</th>
              <th>Vehículo</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let c of filtrados()">
              <td>
                <div class="nombre">{{ c.full_name }}</div>
                <div class="sub">CC {{ c.id_number }}</div>
              </td>
              <td>{{ c.phone }}</td>
              <td>{{ c.city }}, {{ c.barrio }}</td>
              <td>
                <span *ngIf="c.plate">{{ c.plate }}</span>
                <span *ngIf="c.bike_type" class="sub"> · {{ c.bike_type }}</span>
                <span *ngIf="!c.plate && !c.bike_type" class="sub">—</span>
              </td>
              <td>
                <span class="badge" [ngClass]="c.status.toLowerCase()">
                  {{ etiqueta(c.status) }}
                </span>
              </td>
              <td class="acciones">
                <button *ngIf="c.status === 'PENDING'" class="btn aprobar" (click)="accion(c.id, 'approve')">Aprobar</button>
                <button *ngIf="c.status === 'PENDING'" class="btn rechazar" (click)="accion(c.id, 'reject')">Rechazar</button>
                <button *ngIf="c.status === 'APPROVED'" class="btn inactivar" (click)="accion(c.id, 'deactivate')">Inactivar</button>
                <button *ngIf="c.status === 'INACTIVE'" class="btn reactivar" (click)="accion(c.id, 'reactivate')">Reactivar</button>
                <span *ngIf="c.status === 'REJECTED'" class="sin-accion">—</span>
              </td>
            </tr>
            <tr *ngIf="filtrados().length === 0">
              <td colspan="6" class="vacio">No hay repartidores en este estado.</td>
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
    .aprobar  { background: #10b981; color: white; }
    .rechazar { background: #ef4444; color: white; }
    .inactivar { background: #f59e0b; color: white; }
    .reactivar { background: #3b82f6; color: white; }
    .sin-accion { color: #d1d5db; }
    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 40px; }
  `]
})
export class RepartidoresComponent implements OnInit {
  couriers = signal<Courier[]>([]);
  cargando = signal(true);
  error = signal('');
  filtroActivo = signal('TODOS');

  filtroOpciones = [
    { label: 'Todos', valor: 'TODOS' },
    { label: 'Pendientes', valor: 'PENDING' },
    { label: 'Aprobados', valor: 'APPROVED' },
    { label: 'Inactivos', valor: 'INACTIVE' },
    { label: 'Rechazados', valor: 'REJECTED' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<Courier[]>('http://localhost:8000/admin/couriers').subscribe({
      next: (data) => { this.couriers.set(data); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  filtrados() {
    const f = this.filtroActivo();
    return f === 'TODOS' ? this.couriers() : this.couriers().filter(c => c.status === f);
  }

  etiqueta(s: string) {
    return { PENDING: 'Pendiente', APPROVED: 'Aprobado', INACTIVE: 'Inactivo', REJECTED: 'Rechazado' }[s] ?? s;
  }

  accion(id: number, tipo: string) {
    this.http.post(`http://localhost:8000/admin/couriers/${id}/${tipo}`, {}).subscribe({
      next: () => this.cargar(),
      error: () => alert('Error al ejecutar la acción.')
    });
  }
}
