import { Component, OnInit, signal } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { HttpClient } from '@angular/common/http';

interface Admin {
  id: number;
  full_name: string;
  phone: string;
  city: string;
  barrio: string;
  status: string;
  team_name: string;
  document_number: string;
  created_at: string;
}

@Component({
  selector: 'app-administradores',
  standalone: true,
  imports: [NgFor, NgIf, NgClass],
  template: `
    <div class="page">

      <!-- Encabezado -->
      <div class="page-header">
        <h1>Administradores</h1>
        <span class="total">{{ filtrados().length }} registros</span>
      </div>

      <!-- Filtros por estado -->
      <div class="filtros">
        <button
          *ngFor="let f of filtroOpciones"
          [class.activo]="filtroActivo() === f.valor"
          (click)="filtroActivo.set(f.valor)">
          {{ f.label }}
        </button>
      </div>

      <!-- Estado de carga -->
      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <!-- Tabla -->
      <div class="tabla-wrapper" *ngIf="!cargando() && !error()">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Ciudad</th>
              <th>Equipo</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let a of filtrados()">
              <td>
                <div class="nombre">{{ a.full_name }}</div>
                <div class="doc">CC {{ a.document_number }}</div>
              </td>
              <td>{{ a.phone }}</td>
              <td>{{ a.city }}, {{ a.barrio }}</td>
              <td>{{ a.team_name }}</td>
              <td>
                <span class="badge" [ngClass]="a.status.toLowerCase()">
                  {{ etiquetaEstado(a.status) }}
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
              <td colspan="6" class="vacio">No hay administradores en este estado.</td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  `,
  styles: [`
    .page {
      padding: 24px;
    }

    .page-header {
      display: flex;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 20px;
    }

    h1 {
      font-size: 24px;
      font-weight: 700;
      margin: 0;
    }

    .total {
      font-size: 14px;
      color: #6b7280;
    }

    .filtros {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .filtros button {
      padding: 6px 16px;
      border-radius: 20px;
      border: 1px solid #d1d5db;
      background: white;
      cursor: pointer;
      font-size: 13px;
      color: #374151;
      transition: all 0.15s;
    }

    .filtros button:hover {
      border-color: #4338ca;
      color: #4338ca;
    }

    .filtros button.activo {
      background: #4338ca;
      color: white;
      border-color: #4338ca;
    }

    .tabla-wrapper {
      background: white;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead {
      background: #f9fafb;
    }

    th {
      padding: 12px 16px;
      text-align: left;
      font-size: 12px;
      font-weight: 600;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid #e5e7eb;
    }

    td {
      padding: 14px 16px;
      font-size: 14px;
      color: #111827;
      border-bottom: 1px solid #f3f4f6;
    }

    .nombre {
      font-weight: 600;
    }

    .doc {
      font-size: 12px;
      color: #9ca3af;
      margin-top: 2px;
    }

    .badge {
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }

    .badge.pending   { background: #fef3c7; color: #92400e; }
    .badge.approved  { background: #d1fae5; color: #065f46; }
    .badge.inactive  { background: #f3f4f6; color: #6b7280; }
    .badge.rejected  { background: #fee2e2; color: #991b1b; }

    .acciones {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .btn {
      padding: 5px 12px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: opacity 0.15s;
    }

    .btn:hover { opacity: 0.85; }

    .aprobar   { background: #10b981; color: white; }
    .rechazar  { background: #ef4444; color: white; }
    .inactivar { background: #f59e0b; color: white; }
    .reactivar { background: #3b82f6; color: white; }

    .sin-accion { color: #d1d5db; }

    .estado {
      padding: 20px;
      color: #6b7280;
    }

    .estado.error { color: #ef4444; }

    .vacio {
      text-align: center;
      color: #9ca3af;
      padding: 40px;
    }
  `]
})
export class AdministradoresComponent implements OnInit {
  admins = signal<Admin[]>([]);
  cargando = signal(true);
  error = signal('');
  filtroActivo = signal('PENDING');

  filtroOpciones = [
    { label: 'Pendientes', valor: 'PENDING' },
    { label: 'Aprobados', valor: 'APPROVED' },
    { label: 'Inactivos', valor: 'INACTIVE' },
    { label: 'Rechazados', valor: 'REJECTED' },
    { label: 'Todos', valor: 'TODOS' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.cargar();
  }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<Admin[]>('http://localhost:8000/admin/admins').subscribe({
      next: (data) => {
        this.admins.set(data);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo conectar con el servidor. ¿Está corriendo el backend?');
        this.cargando.set(false);
      }
    });
  }

  filtrados() {
    const f = this.filtroActivo();
    if (f === 'TODOS') return this.admins();
    return this.admins().filter(a => a.status === f);
  }

  etiquetaEstado(status: string): string {
    const map: Record<string, string> = {
      PENDING: 'Pendiente',
      APPROVED: 'Aprobado',
      INACTIVE: 'Inactivo',
      REJECTED: 'Rechazado',
    };
    return map[status] ?? status;
  }

  accion(a: Admin, tipo: string) {
    const labels: Record<string, string> = {
      approve: 'aprobar', reject: 'rechazar', deactivate: 'inactivar', reactivate: 'reactivar'
    };
    if (!confirm(`¿${labels[tipo] ?? tipo} a ${a.full_name}?`)) return;
    this.http.post(`http://localhost:8000/admin/admins/${a.id}/${tipo}`, {}).subscribe({
      next: () => this.cargar(),
      error: (e) => alert(e.error?.detail ?? 'Error al ejecutar la acción.')
    });
  }
}
