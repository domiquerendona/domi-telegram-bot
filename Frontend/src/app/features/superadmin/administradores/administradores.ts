import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { NgFor, NgIf, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmService } from '../../../core/services/confirm.service';

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

interface WebPanelUser {
  id: number;
  username: string;
  role: string;
  status: string;
  admin_id: number | null;
  courier_id?: number | null;
}

interface Courier {
  id: number;
  full_name: string;
  phone: string;
  city: string;
  status: string;
}

@Component({
  selector: 'app-administradores',
  standalone: true,
  imports: [NgFor, NgIf, NgClass, FormsModule],
  template: `
    <div class="page">

      <!-- Encabezado -->
      <div class="page-header">
        <h1>Administradores</h1>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button [class.activo]="vista() === 'bot'" (click)="cambiarVista('bot')">Admins Bot</button>
        <button [class.activo]="vista() === 'panel'" (click)="cambiarVista('panel')">Usuarios Panel</button>
      </div>

      <!-- ===== VISTA: ADMINS BOT ===== -->
      <ng-container *ngIf="vista() === 'bot'">

        <div class="filtros">
          <button
            *ngFor="let f of filtroOpciones"
            [class.activo]="filtroActivo() === f.valor"
            (click)="filtroActivo.set(f.valor)">
            {{ f.label }}
          </button>
          <span class="total">{{ filtrados().length }} registros</span>
        </div>

        <div class="estado" *ngIf="cargando()">Cargando...</div>
        <div class="estado error" *ngIf="errorBot()">{{ errorBot() }}</div>

        <div class="tabla-wrapper" *ngIf="!cargando() && !errorBot()">
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
                  <button *ngIf="a.status === 'PENDING'" class="btn aprobar" (click)="accionBot(a, 'approve')">Aprobar</button>
                  <button *ngIf="a.status === 'PENDING'" class="btn rechazar" (click)="accionBot(a, 'reject')">Rechazar</button>
                  <button *ngIf="a.status === 'APPROVED'" class="btn inactivar" (click)="accionBot(a, 'deactivate')">Inactivar</button>
                  <button *ngIf="a.status === 'INACTIVE'" class="btn reactivar" (click)="accionBot(a, 'reactivate')">Reactivar</button>
                  <span *ngIf="a.status === 'REJECTED'" class="sin-accion">—</span>
                </td>
              </tr>
              <tr *ngIf="filtrados().length === 0">
                <td colspan="6" class="vacio">No hay administradores en este estado.</td>
              </tr>
            </tbody>
          </table>
        </div>

      </ng-container>

      <!-- ===== VISTA: USUARIOS PANEL ===== -->
      <ng-container *ngIf="vista() === 'panel'">

        <!-- Toolbar con botón crear -->
        <div class="toolbar">
          <span class="total">{{ webUsers().length }} usuarios</span>
          <button class="btn-crear" (click)="toggleCrear()">
            {{ creandoVisible() ? 'Cancelar' : '+ Nuevo usuario' }}
          </button>
        </div>

        <!-- Formulario de creación -->
        <div class="form-crear" *ngIf="creandoVisible()">
          <h3>Nuevo usuario del panel</h3>
          <div class="form-fila">
            <label>Usuario</label>
            <input type="text" [(ngModel)]="nuevoUsername" placeholder="nombre_usuario" autocomplete="off" />
          </div>
          <div class="form-fila">
            <label>Contraseña</label>
            <div class="password-wrapper">
              <input [type]="mostrarPassword() ? 'text' : 'password'" [(ngModel)]="nuevoPassword" placeholder="••••••••" autocomplete="new-password" />
              <button type="button" class="toggle-password" (click)="mostrarPassword.set(!mostrarPassword())">
                <span class="material-symbols-outlined">{{ mostrarPassword() ? 'visibility_off' : 'visibility' }}</span>
              </button>
            </div>
          </div>
          <div class="form-fila">
            <label>Rol</label>
            <select [(ngModel)]="nuevoRole">
              <option value="ADMIN_PLATFORM">Admin Plataforma</option>
              <option value="ADMIN_LOCAL">Admin Local</option>
              <option value="COURIER">Repartidor</option>
            </select>
          </div>
          <div class="form-fila" *ngIf="nuevoRole === 'ADMIN_LOCAL'">
            <label>Admin Bot vinculado</label>
            <select [(ngModel)]="nuevoAdminId">
              <option value="">— Sin vincular —</option>
              <option *ngFor="let a of adminsAprobados()" [value]="a.id">
                {{ a.full_name }} ({{ a.city }})
              </option>
            </select>
            <small>El ID del admin del bot al que pertenece este usuario.</small>
          </div>
          <div class="form-fila" *ngIf="nuevoRole === 'COURIER'">
            <label>Repartidor vinculado</label>
            <select [(ngModel)]="nuevoCourierId">
              <option value="">— Selecciona un repartidor —</option>
              <option *ngFor="let c of couriersAprobados()" [value]="c.id">
                {{ c.full_name }} — {{ c.phone }} ({{ c.city }})
              </option>
            </select>
            <small>El repartidor del bot que usará este acceso al panel.</small>
          </div>
          <div class="form-error" *ngIf="errorCrear()">{{ errorCrear() }}</div>
          <div class="form-acciones">
            <button class="btn aprobar" [disabled]="creando()" (click)="crearUsuario()">
              {{ creando() ? 'Creando...' : 'Crear usuario' }}
            </button>
          </div>
        </div>

        <!-- Carga / error -->
        <div class="estado" *ngIf="cargandoPanel()">Cargando...</div>
        <div class="estado error" *ngIf="errorPanel()">{{ errorPanel() }}</div>

        <!-- Tabla de usuarios del panel -->
        <div class="tabla-wrapper" *ngIf="!cargandoPanel() && !errorPanel()">
          <table>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Vínculo</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let u of webUsers()">
                <td><div class="nombre">{{ u.username }}</div></td>
                <td>
                  <span class="badge" [ngClass]="roleBadgeClass(u.role)">
                    {{ roleLabel(u.role) }}
                  </span>
                </td>
                <td>{{ vinculoLabel(u) }}</td>
                <td>
                  <span class="badge" [ngClass]="u.status.toLowerCase()">
                    {{ u.status === 'APPROVED' ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td class="acciones">
                  <button
                    *ngIf="u.status === 'APPROVED'"
                    class="btn inactivar"
                    (click)="cambiarEstadoPanel(u, 'INACTIVE')">
                    Inactivar
                  </button>
                  <button
                    *ngIf="u.status === 'INACTIVE'"
                    class="btn reactivar"
                    (click)="cambiarEstadoPanel(u, 'APPROVED')">
                    Activar
                  </button>
                </td>
              </tr>
              <tr *ngIf="webUsers().length === 0">
                <td colspan="5" class="vacio">No hay usuarios del panel registrados.</td>
              </tr>
            </tbody>
          </table>
        </div>

      </ng-container>

    </div>
  `,
  styles: [`
    .page { padding: 24px; }

    .page-header {
      display: flex;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 20px;
    }

    h1 { font-size: 24px; font-weight: 700; margin: 0; }

    /* Tabs */
    .tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 20px;
      border-bottom: 2px solid #e5e7eb;
    }

    .tabs button {
      padding: 8px 20px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: #6b7280;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: all 0.15s;
    }

    .tabs button.activo {
      color: #4338ca;
      border-bottom-color: #4338ca;
    }

    .tabs button:hover:not(.activo) { color: #374151; }

    /* Filtros */
    .filtros {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      flex-wrap: wrap;
      align-items: center;
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

    .filtros button:hover { border-color: #4338ca; color: #4338ca; }
    .filtros button.activo { background: #4338ca; color: white; border-color: #4338ca; }

    /* Toolbar panel */
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .btn-crear {
      padding: 8px 20px;
      background: #4338ca;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      transition: opacity 0.15s;
    }
    .btn-crear:hover { opacity: 0.88; }

    /* Formulario crear */
    .form-crear {
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 20px;
    }

    .form-crear h3 { margin: 0 0 16px; font-size: 15px; font-weight: 700; color: #111827; }

    .form-fila {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 14px;
    }

    .form-fila label { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; }

    .form-fila input,
    .form-fila select {
      padding: 9px 12px;
      border: 1.5px solid #d1d5db;
      border-radius: 8px;
      font-size: 14px;
      color: #111827;
      max-width: 380px;
      outline: none;
    }

    .form-fila input:focus,
    .form-fila select:focus { border-color: #4338ca; }

    .form-fila small { font-size: 11px; color: #9ca3af; }

    .password-wrapper { position: relative; display: flex; align-items: center; max-width: 380px; }
    .password-wrapper input { width: 100%; max-width: 100%; padding-right: 44px; }
    .toggle-password {
      position: absolute; right: 10px;
      background: none; border: none; padding: 4px; margin: 0;
      cursor: pointer; color: #6b7280; display: flex; align-items: center;
      width: auto;
    }
    .toggle-password:hover { color: #4338ca; }
    .toggle-password span { font-size: 20px; }

    .form-error {
      background: #fef2f2;
      border: 1px solid #fca5a5;
      color: #dc2626;
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 13px;
      margin-bottom: 12px;
    }

    .form-acciones { display: flex; gap: 8px; }

    /* Tabla */
    .tabla-wrapper {
      background: white;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

    table { width: 100%; border-collapse: collapse; }
    thead { background: #f9fafb; }

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

    .nombre { font-weight: 600; }
    .doc { font-size: 12px; color: #9ca3af; margin-top: 2px; }

    .total { font-size: 14px; color: #6b7280; }

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
    .badge.plataforma { background: #ede9fe; color: #5b21b6; }
    .badge.local      { background: #dbeafe; color: #1e40af; }
    .badge.courier    { background: #d1fae5; color: #065f46; }

    .acciones { display: flex; gap: 8px; align-items: center; }

    .btn {
      padding: 5px 12px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: opacity 0.15s;
    }

    .btn:hover:not(:disabled) { opacity: 0.85; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

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
export class AdministradoresComponent implements OnInit {
  // Bot admins
  admins = signal<Admin[]>([]);
  cargando = signal(true);
  errorBot = signal('');
  filtroActivo = signal('PENDING');

  filtroOpciones = [
    { label: 'Pendientes', valor: 'PENDING' },
    { label: 'Aprobados', valor: 'APPROVED' },
    { label: 'Inactivos', valor: 'INACTIVE' },
    { label: 'Rechazados', valor: 'REJECTED' },
    { label: 'Todos', valor: 'TODOS' },
  ];

  // Web panel users
  webUsers = signal<WebPanelUser[]>([]);
  cargandoPanel = signal(false);
  errorPanel = signal('');

  // Couriers (para vinculación)
  couriers = signal<Courier[]>([]);

  // Vista activa
  vista = signal<'bot' | 'panel'>('bot');

  // Formulario crear
  creandoVisible = signal(false);
  creando = signal(false);
  errorCrear = signal('');
  mostrarPassword = signal(false);
  nuevoUsername = '';
  nuevoPassword = '';
  nuevoRole = 'ADMIN_LOCAL';
  nuevoAdminId: string | number = '';
  nuevoCourierId: string | number = '';

  adminsAprobados = computed(() => this.admins().filter(a => a.status === 'APPROVED'));
  couriersAprobados = computed(() => this.couriers().filter(c => c.status === 'APPROVED'));

  private adminMap = computed<Record<number, string>>(() =>
    Object.fromEntries(this.admins().map(a => [a.id, a.full_name]))
  );
  private courierMap = computed<Record<number, string>>(() =>
    Object.fromEntries(this.couriers().map(c => [c.id, c.full_name]))
  );

  private toast   = inject(ToastService);
  private confirm = inject(ConfirmService);
  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.cargarBot();
  }

  cambiarVista(v: 'bot' | 'panel') {
    this.vista.set(v);
    if (v === 'panel') {
      if (this.webUsers().length === 0 && !this.cargandoPanel()) this.cargarPanel();
      if (this.couriers().length === 0) this.cargarCouriers();
    }
  }

  // ── Bot admins ──────────────────────────────────────────────────────────────

  cargarBot() {
    this.cargando.set(true);
    this.errorBot.set('');
    this.http.get<Admin[]>(`${environment.apiBaseUrl}/admin/admins`).subscribe({
      next: (data) => { this.admins.set(data); this.cargando.set(false); },
      error: () => {
        this.errorBot.set('No se pudo conectar con el servidor.');
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
      PENDING: 'Pendiente', APPROVED: 'Aprobado', INACTIVE: 'Inactivo', REJECTED: 'Rechazado',
    };
    return map[status] ?? status;
  }

  async accionBot(a: Admin, tipo: string) {
    const labels: Record<string, string> = {
      approve: 'Aprobar', reject: 'Rechazar', deactivate: 'Inactivar', reactivate: 'Reactivar'
    };
    const label = labels[tipo] ?? tipo;
    const ok = await this.confirm.ask(`¿${label} a ${a.full_name}?`, label);
    if (!ok) return;
    this.http.post(`${environment.apiBaseUrl}/admin/admins/${a.id}/${tipo}`, {}).subscribe({
      next: () => { this.toast.success(`${label} ejecutado correctamente.`); this.cargarBot(); },
      error: (e) => this.toast.error(e.error?.detail ?? 'Error al ejecutar la acción.')
    });
  }

  // ── Couriers ────────────────────────────────────────────────────────────────

  cargarCouriers() {
    this.http.get<Courier[]>(`${environment.apiBaseUrl}/admin/couriers`).subscribe({
      next: (data) => this.couriers.set(data),
      error: () => {}
    });
  }

  // ── Web panel users ─────────────────────────────────────────────────────────

  cargarPanel() {
    this.cargandoPanel.set(true);
    this.errorPanel.set('');
    this.http.get<WebPanelUser[]>(`${environment.apiBaseUrl}/admin/web-users`).subscribe({
      next: (data) => { this.webUsers.set(data); this.cargandoPanel.set(false); },
      error: () => {
        this.errorPanel.set('No se pudo cargar la lista de usuarios del panel.');
        this.cargandoPanel.set(false);
      }
    });
  }

  toggleCrear() {
    this.creandoVisible.update(v => !v);
    this.errorCrear.set('');
    this.mostrarPassword.set(false);
    this.nuevoUsername = '';
    this.nuevoPassword = '';
    this.nuevoRole = 'ADMIN_LOCAL';
    this.nuevoAdminId = '';
    this.nuevoCourierId = '';
    if (this.couriers().length === 0) this.cargarCouriers();
  }

  crearUsuario() {
    const username = this.nuevoUsername.trim();
    const password = this.nuevoPassword.trim();
    if (!username || !password) {
      this.errorCrear.set('El usuario y la contraseña son obligatorios.');
      return;
    }
    if (this.nuevoRole === 'COURIER' && !this.nuevoCourierId) {
      this.errorCrear.set('Debes seleccionar un repartidor.');
      return;
    }
    this.creando.set(true);
    this.errorCrear.set('');
    const body: Record<string, unknown> = {
      username,
      password,
      role: this.nuevoRole,
      admin_id: this.nuevoRole === 'ADMIN_LOCAL' && this.nuevoAdminId ? Number(this.nuevoAdminId) : null,
      courier_id: this.nuevoRole === 'COURIER' && this.nuevoCourierId ? Number(this.nuevoCourierId) : null,
    };
    this.http.post(`${environment.apiBaseUrl}/admin/web-users`, body).subscribe({
      next: () => {
        this.creando.set(false);
        this.creandoVisible.set(false);
        this.cargarPanel();
      },
      error: (e) => {
        this.errorCrear.set(e.error?.detail ?? 'Error al crear el usuario.');
        this.creando.set(false);
      }
    });
  }

  async cambiarEstadoPanel(u: WebPanelUser, status: string) {
    const accion = status === 'INACTIVE' ? 'inactivar' : 'activar';
    const ok = await this.confirm.ask(`¿${accion} al usuario "${u.username}"?`, accion === 'inactivar' ? 'Inactivar' : 'Activar');
    if (!ok) return;
    this.http.patch(`${environment.apiBaseUrl}/admin/web-users/${u.id}/status`, { status }).subscribe({
      next: () => { this.toast.success(`Usuario ${accion === 'inactivar' ? 'inactivado' : 'activado'} correctamente.`); this.cargarPanel(); },
      error: (e) => this.toast.error(e.error?.detail ?? 'Error al cambiar el estado.')
    });
  }

  roleLabel(role: string): string {
    const map: Record<string, string> = {
      ADMIN_PLATFORM: 'Plataforma',
      ADMIN_LOCAL: 'Local',
      COURIER: 'Repartidor',
    };
    return map[role] ?? role;
  }

  roleBadgeClass(role: string): string {
    const map: Record<string, string> = {
      ADMIN_PLATFORM: 'badge plataforma',
      ADMIN_LOCAL: 'badge local',
      COURIER: 'badge courier',
    };
    return map[role] ?? 'badge';
  }

  vinculoLabel(u: WebPanelUser): string {
    if (u.role === 'COURIER') {
      if (!u.courier_id) return '—';
      return this.courierMap()[u.courier_id] ?? `#${u.courier_id}`;
    }
    if (!u.admin_id) return '—';
    return this.adminMap()[u.admin_id] ?? `#${u.admin_id}`;
  }
}
