import { Component, OnInit, signal } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { fmtFecha } from '../../../core/utils/fecha';

interface UserRow {
  id: number;
  telegram_id: number;
  username: string;
  role: string;
  created_at: string;
  nombre: string;
  phone: string;
  ciudad: string;
  status: string;
}

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [NgFor, NgIf, NgClass],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Usuarios</h1>
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
              <th>#</th>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Ciudad</th>
              <th>Rol</th>
              <th>Estado</th>
              <th>Registrado</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let u of filtrados()">
              <td class="id-cell">{{ u.id }}</td>
              <td>
                <div class="nombre">{{ u.nombre || u.username || '—' }}</div>
                <div class="sub">@{{ u.username || u.telegram_id }}</div>
              </td>
              <td>{{ u.phone || '—' }}</td>
              <td>{{ u.ciudad || '—' }}</td>
              <td>
                <span class="role-badge" [ngClass]="roleClass(u.role)">
                  {{ rolLabel(u.role) }}
                </span>
              </td>
              <td>
                <span class="badge" [ngClass]="u.status ? u.status.toLowerCase() : 'sin-estado'">
                  {{ etiqueta(u.status) }}
                </span>
              </td>
              <td class="fecha">{{ fmtFecha(u.created_at) }}</td>
            </tr>
            <tr *ngIf="filtrados().length === 0">
              <td colspan="7" class="vacio">No hay usuarios en este filtro.</td>
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
    table { width: 100%; border-collapse: collapse; min-width: 800px; }
    thead { background: #f9fafb; }
    th { padding: 12px 16px; text-align: left; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
    td { padding: 13px 16px; font-size: 14px; color: #111827; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
    .id-cell { color: #9ca3af; font-size: 13px; font-weight: 600; }
    .nombre { font-weight: 600; }
    .sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
    .fecha { font-size: 12px; color: #6b7280; white-space: nowrap; }

    .badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    .badge.approved { background: #d1fae5; color: #065f46; }
    .badge.inactive { background: #f3f4f6; color: #6b7280; }
    .badge.pending  { background: #fef3c7; color: #92400e; }
    .badge.rejected { background: #fee2e2; color: #991b1b; }
    .badge.sin-estado { background: #f3f4f6; color: #9ca3af; }

    .role-badge { padding: 3px 9px; border-radius: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .role-badge.platform { background: #1e1b4b; color: white; }
    .role-badge.admin    { background: #4338ca; color: white; }
    .role-badge.courier  { background: #0891b2; color: white; }
    .role-badge.ally     { background: #059669; color: white; }
    .role-badge.unknown  { background: #e5e7eb; color: #6b7280; }

    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }
    .vacio { text-align: center; color: #9ca3af; padding: 40px; }
  `]
})
export class UsersComponent implements OnInit {
  users = signal<UserRow[]>([]);
  cargando = signal(true);
  error = signal('');
  filtroActivo = signal('TODOS');

  filtroOpciones = [
    { label: 'Todos', valor: 'TODOS' },
    { label: 'Plataforma', valor: 'PLATFORM_ADMIN' },
    { label: 'Admin Local', valor: 'ADMIN_LOCAL' },
    { label: 'Repartidores', valor: 'COURIER' },
    { label: 'Aliados', valor: 'ALLY' },
    { label: 'Sin rol', valor: '' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<UserRow[]>(`${environment.apiBaseUrl}/admin/users`).subscribe({
      next: (d) => { this.users.set(d); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  filtrados() {
    const f = this.filtroActivo();
    return f === 'TODOS' ? this.users() : this.users().filter(u => u.role === f);
  }

  rolLabel(role: string) {
    return {
      PLATFORM_ADMIN: 'Plataforma',
      ADMIN_LOCAL: 'Admin',
      COURIER: 'Repartidor',
      ALLY: 'Aliado',
    }[role] ?? role ?? '—';
  }

  roleClass(role: string) {
    return {
      PLATFORM_ADMIN: 'platform',
      ADMIN_LOCAL: 'admin',
      COURIER: 'courier',
      ALLY: 'ally',
    }[role] ?? 'unknown';
  }

  etiqueta(s: string) {
    return {
      APPROVED: 'Aprobado', INACTIVE: 'Inactivo',
      PENDING: 'Pendiente', REJECTED: 'Rechazado',
    }[s] ?? (s ? s : 'Sin estado');
  }

  fmtFecha = fmtFecha;
}
