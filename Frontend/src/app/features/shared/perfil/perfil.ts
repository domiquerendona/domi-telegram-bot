import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../../environments/environment';

interface ProfileDetail {
  id?: number;
  full_name?: string;
  phone?: string;
  city?: string;
  vehicle_type?: string;
  status?: string;
}

interface ProfileResponse {
  username: string;
  role: string;
  created_at: string | null;
  detail: ProfileDetail | null;
}

interface ActivityItem {
  tipo?: string;
  full_name: string;
  status: string;
  updated_at: string;
  order_id?: number;
  total_fee?: number;
  incentivo?: number;
  delivered_at?: string;
  ally_name?: string;
  dropoff_city?: string;
}

@Component({
  selector: 'app-perfil',
  standalone: true,
  imports: [FormsModule],
  template: `
  <div class="page">
    <h2 class="title">Mi Perfil</h2>

    @if (cargando()) { <div class="loading">Cargando...</div> }
    @if (errorMsg()) { <div class="error-banner">{{ errorMsg() }}</div> }

    @if (data()) {
    <div class="layout">

      <!-- ===== TARJETA PRINCIPAL ===== -->
      <div class="card">

        <div class="card-top">
          <div class="avatar" [class]="avatarClass()">
            <span class="initials">{{ initials() }}</span>
          </div>

          @if (!editando()) {
            <h3 class="display-name">{{ data()!.detail?.full_name ?? data()!.username }}</h3>
          } @else {
            <input class="name-input" [(ngModel)]="editNombre" placeholder="Nombre completo" />
          }

          <span class="role-badge" [class]="roleBadgeClass()">{{ roleLabel() }}</span>

          @if (data()!.detail?.status) {
          <div class="status-row">
            <span class="status-dot" [class]="'dot-' + data()!.detail!.status!.toLowerCase()"></span>
            <span class="status-text">{{ statusLabel() }}</span>
          </div>
          }
        </div>

        <!-- Campos -->
        <div class="fields">
          <div class="field">
            <span class="field-label">Usuario</span>
            <span class="field-value">{{ data()!.username }}</span>
          </div>

          @if (data()!.detail?.phone || editando()) {
          <div class="field">
            <span class="field-label">Teléfono</span>
            @if (!editando()) {
              <span class="field-value">{{ data()!.detail!.phone }}</span>
            } @else {
              <input class="field-input" [(ngModel)]="editTelefono" placeholder="Teléfono" />
            }
          </div>
          }

          @if (data()!.detail?.vehicle_type) {
          <div class="field">
            <span class="field-label">Vehículo</span>
            <span class="field-value">{{ data()!.detail!.vehicle_type }}</span>
          </div>
          }

          @if (data()!.created_at) {
          <div class="field">
            <span class="field-label">Miembro desde</span>
            <span class="field-value muted">{{ formatDate(data()!.created_at!) }}</span>
          </div>
          }
        </div>

        <!-- Acciones edición -->
        <div class="actions">
          @if (!editando()) {
            <button class="btn-outline" (click)="iniciarEdicion()">
              <span class="material-symbols-outlined">edit</span> Editar datos
            </button>
            <button class="btn-outline" (click)="mostrarPassword.set(!mostrarPassword())">
              <span class="material-symbols-outlined">lock</span> Cambiar contraseña
            </button>
          } @else {
            <button class="btn-primary" (click)="guardarEdicion()" [disabled]="guardando()">
              {{ guardando() ? 'Guardando...' : 'Guardar cambios' }}
            </button>
            <button class="btn-ghost" (click)="cancelarEdicion()">Cancelar</button>
          }
        </div>

        @if (okMsg()) { <div class="ok-banner">{{ okMsg() }}</div> }
      </div>

      <!-- ===== CAMBIAR CONTRASEÑA ===== -->
      @if (mostrarPassword()) {
      <div class="card">
        <h4 class="section-title">
          <span class="material-symbols-outlined">lock</span> Cambiar contraseña
        </h4>
        <div class="pw-form">
          <div class="pw-field">
            <label>Contraseña actual</label>
            <input [type]="verPw() ? 'text' : 'password'" [(ngModel)]="pwActual" placeholder="••••••" />
          </div>
          <div class="pw-field">
            <label>Nueva contraseña</label>
            <input [type]="verPw() ? 'text' : 'password'" [(ngModel)]="pwNueva" placeholder="Mínimo 6 caracteres" />
          </div>
          <div class="pw-field">
            <label>Confirmar nueva</label>
            <input [type]="verPw() ? 'text' : 'password'" [(ngModel)]="pwConfirm" placeholder="Repite la nueva" />
          </div>
          <label class="toggle-ver">
            <input type="checkbox" (change)="verPw.set(!verPw())" /> Mostrar contraseñas
          </label>
          @if (pwError()) { <div class="error-banner small">{{ pwError() }}</div> }
          <div class="pw-actions">
            <button class="btn-primary" (click)="cambiarPassword()" [disabled]="cambiandoPw()">
              {{ cambiandoPw() ? 'Guardando...' : 'Actualizar contraseña' }}
            </button>
            <button class="btn-ghost" (click)="mostrarPassword.set(false)">Cancelar</button>
          </div>
        </div>
      </div>
      }

      <!-- ===== ACTIVIDAD RECIENTE ===== -->
      @if (actividad().length > 0) {
      <div class="card">
        <h4 class="section-title">
          <span class="material-symbols-outlined">history</span> Actividad reciente
        </h4>
        <div class="activity-list">
          @for (item of actividad(); track $index) {
          <div class="activity-item">
            <div class="activity-icon" [class]="activityIconClass(item)">
              <span class="material-symbols-outlined">{{ activityIcon(item) }}</span>
            </div>
            <div class="activity-info">
              <span class="activity-name">{{ activityName(item) }}</span>
              <span class="activity-sub">{{ activitySub(item) }}</span>
            </div>
            <div class="activity-meta">
              <span class="activity-badge" [class]="activityBadgeClass(item)">{{ activityBadge(item) }}</span>
              <span class="activity-date">{{ formatShortDate(activityDate(item)) }}</span>
            </div>
          </div>
          }
        </div>
      </div>
      }

    </div>
    }
  </div>
  `,
  styles: [`
  .page { max-width: 580px; }
  .title { font-size: 22px; font-weight: 700; color: #1f2937; margin-bottom: 24px; }
  .layout { display: flex; flex-direction: column; gap: 16px; }
  .loading { color: #6b7280; }

  .error-banner {
    color: #dc2626; background: #fef2f2; padding: 10px 14px;
    border-radius: 8px; font-size: 13px; margin-bottom: 8px;
  }
  .error-banner.small { margin-top: 8px; }
  .ok-banner {
    color: #059669; background: #d1fae5; padding: 10px 14px;
    border-radius: 8px; font-size: 13px; margin-top: 12px;
  }

  /* ---- CARD ---- */
  .card {
    background: white; border-radius: 20px;
    overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  }

  .card-top {
    display: flex; flex-direction: column; align-items: center;
    padding: 36px 32px 24px;
    background: linear-gradient(160deg, #f5f3ff 0%, #ede9fe 100%);
    border-bottom: 1px solid #e9d5ff;
    gap: 10px;
  }

  /* ---- AVATAR con iniciales ---- */
  .avatar {
    width: 80px; height: 80px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 4px; box-shadow: 0 4px 14px rgba(109,40,217,0.22);
  }
  .avatar-admin   { background: linear-gradient(135deg, #7c3aed, #4f46e5); }
  .avatar-local   { background: linear-gradient(135deg, #2563eb, #6366f1); }
  .avatar-courier { background: linear-gradient(135deg, #059669, #0891b2); }

  .initials { color: white; font-size: 26px; font-weight: 800; letter-spacing: -1px; }

  .display-name { font-size: 20px; font-weight: 700; color: #111827; margin: 0; text-align: center; }

  .name-input {
    font-size: 17px; font-weight: 600; text-align: center;
    border: 2px solid #7c3aed; border-radius: 8px; padding: 6px 12px;
    width: 100%; max-width: 280px; outline: none;
  }

  .role-badge {
    padding: 4px 14px; border-radius: 20px;
    font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
  }
  .badge-admin    { background: #ede9fe; color: #6d28d9; }
  .badge-local    { background: #dbeafe; color: #2563eb; }
  .badge-courier  { background: #d1fae5; color: #059669; }

  /* ---- INDICADOR DE ESTADO ---- */
  .status-row { display: flex; align-items: center; gap: 6px; margin-top: -2px; }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    animation: pulse 2s infinite;
  }
  .dot-approved { background: #10b981; box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
  .dot-inactive { background: #9ca3af; animation: none; }
  .dot-pending  { background: #f59e0b; box-shadow: 0 0 0 0 rgba(245,158,11,0.4); }

  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
    70%  { box-shadow: 0 0 0 6px rgba(16,185,129,0); }
    100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
  }

  .status-text { font-size: 12px; color: #6b7280; }

  /* ---- CAMPOS ---- */
  .fields { display: flex; flex-direction: column; padding: 4px 0; }
  .field {
    display: flex; justify-content: space-between; align-items: center;
    padding: 13px 28px; border-bottom: 1px solid #f9fafb;
  }
  .field:last-child { border-bottom: none; }
  .field-label { font-size: 13px; color: #6b7280; }
  .field-value { font-size: 14px; font-weight: 600; color: #111827; }
  .field-value.muted { color: #6b7280; font-weight: 500; }
  .field-input {
    font-size: 14px; font-weight: 600; border: 1.5px solid #7c3aed;
    border-radius: 6px; padding: 4px 8px; text-align: right; outline: none; width: 160px;
  }

  /* ---- BOTONES ---- */
  .actions {
    display: flex; gap: 10px; padding: 16px 28px;
    border-top: 1px solid #f3f4f6; flex-wrap: wrap;
  }
  .btn-primary {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 9px 18px; font-size: 13px; font-weight: 600; cursor: pointer;
    display: flex; align-items: center; gap: 6px;
  }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-outline {
    background: white; color: #7c3aed; border: 1.5px solid #7c3aed; border-radius: 8px;
    padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
    display: flex; align-items: center; gap: 6px;
  }
  .btn-outline span { font-size: 16px; }
  .btn-ghost {
    background: transparent; color: #6b7280; border: none;
    padding: 8px 12px; font-size: 13px; cursor: pointer;
  }

  /* ---- CAMBIAR CONTRASEÑA ---- */
  .section-title {
    display: flex; align-items: center; gap: 8px;
    font-size: 15px; font-weight: 700; color: #1f2937;
    padding: 20px 28px 0; margin: 0;
  }
  .section-title span { font-size: 18px; color: #7c3aed; }

  .pw-form { display: flex; flex-direction: column; gap: 14px; padding: 16px 28px 24px; }
  .pw-field { display: flex; flex-direction: column; gap: 5px; }
  .pw-field label { font-size: 12px; color: #6b7280; font-weight: 600; }
  .pw-field input {
    border: 1.5px solid #e5e7eb; border-radius: 8px; padding: 9px 12px;
    font-size: 14px; outline: none;
  }
  .pw-field input:focus { border-color: #7c3aed; }

  .toggle-ver { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #6b7280; cursor: pointer; }
  .pw-actions { display: flex; gap: 10px; margin-top: 4px; }

  /* ---- ACTIVIDAD ---- */
  .activity-list { display: flex; flex-direction: column; padding: 12px 0 8px; }

  .activity-item {
    display: flex; align-items: center; gap: 14px;
    padding: 12px 28px; border-bottom: 1px solid #f9fafb;
  }
  .activity-item:last-child { border-bottom: none; }

  .activity-icon {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  }
  .activity-icon span { font-size: 18px; }
  .icon-courier  { background: #d1fae5; color: #059669; }
  .icon-ally     { background: #dbeafe; color: #2563eb; }
  .icon-delivery { background: #ede9fe; color: #7c3aed; }

  .activity-info { flex: 1; display: flex; flex-direction: column; gap: 2px; overflow: hidden; }
  .activity-name { font-size: 13px; font-weight: 600; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .activity-sub  { font-size: 12px; color: #6b7280; }

  .activity-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
  .activity-badge {
    padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 600;
  }
  .badge-approved  { background: #d1fae5; color: #065f46; }
  .badge-inactive  { background: #f3f4f6; color: #4b5563; }
  .badge-pending   { background: #fef3c7; color: #92400e; }
  .badge-delivered { background: #ede9fe; color: #6d28d9; }
  .activity-date { font-size: 11px; color: #9ca3af; }
  `]
})
export class PerfilComponent implements OnInit {
  data        = signal<ProfileResponse | null>(null);
  actividad   = signal<ActivityItem[]>([]);
  cargando    = signal(true);
  errorMsg    = signal('');
  okMsg       = signal('');

  editando    = signal(false);
  guardando   = signal(false);
  editNombre  = '';
  editTelefono = '';

  mostrarPassword = signal(false);
  verPw       = signal(false);
  pwActual    = '';
  pwNueva     = '';
  pwConfirm   = '';
  pwError     = signal('');
  cambiandoPw = signal(false);

  constructor(private http: HttpClient) {}

  get token() { return localStorage.getItem('admin_token') ?? ''; }
  get headers() { return { Authorization: `Bearer ${this.token}` }; }

  ngOnInit() {
    this.http.get<ProfileResponse>(`${environment.apiBaseUrl}/profile`, { headers: this.headers })
      .subscribe({
        next: (res) => { this.data.set(res); this.cargando.set(false); this.cargarActividad(); },
        error: (e) => { this.errorMsg.set(e.error?.detail ?? 'Error al cargar perfil'); this.cargando.set(false); }
      });
  }

  cargarActividad() {
    this.http.get<{ items: ActivityItem[] }>(`${environment.apiBaseUrl}/profile/activity`, { headers: this.headers })
      .subscribe({ next: (r) => this.actividad.set(r.items), error: () => {} });
  }

  iniciarEdicion() {
    this.editNombre   = this.data()?.detail?.full_name ?? '';
    this.editTelefono = this.data()?.detail?.phone ?? '';
    this.editando.set(true);
    this.okMsg.set('');
  }

  cancelarEdicion() { this.editando.set(false); }

  guardarEdicion() {
    if (!this.editNombre.trim()) { this.okMsg.set(''); this.errorMsg.set('El nombre no puede estar vacío'); return; }
    this.guardando.set(true);
    this.errorMsg.set('');
    this.http.patch(`${environment.apiBaseUrl}/profile/detail`,
      { full_name: this.editNombre.trim(), phone: this.editTelefono.trim() },
      { headers: this.headers }
    ).subscribe({
      next: () => {
        this.guardando.set(false);
        this.editando.set(false);
        this.okMsg.set('Datos actualizados correctamente');
        // Actualizar datos localmente
        const d = this.data();
        if (d) {
          this.data.set({ ...d, detail: { ...d.detail, full_name: this.editNombre.trim(), phone: this.editTelefono.trim() } });
        }
      },
      error: (e) => { this.guardando.set(false); this.errorMsg.set(e.error?.detail ?? 'Error al guardar'); }
    });
  }

  cambiarPassword() {
    this.pwError.set('');
    if (!this.pwActual || !this.pwNueva || !this.pwConfirm) { this.pwError.set('Completa todos los campos'); return; }
    if (this.pwNueva.length < 6) { this.pwError.set('La nueva contraseña debe tener al menos 6 caracteres'); return; }
    if (this.pwNueva !== this.pwConfirm) { this.pwError.set('Las contraseñas nuevas no coinciden'); return; }
    this.cambiandoPw.set(true);
    this.http.patch(`${environment.apiBaseUrl}/profile/password`,
      { current_password: this.pwActual, new_password: this.pwNueva },
      { headers: this.headers }
    ).subscribe({
      next: () => {
        this.cambiandoPw.set(false);
        this.mostrarPassword.set(false);
        this.pwActual = this.pwNueva = this.pwConfirm = '';
        this.okMsg.set('Contraseña actualizada correctamente');
      },
      error: (e) => { this.cambiandoPw.set(false); this.pwError.set(e.error?.detail ?? 'Error al cambiar contraseña'); }
    });
  }

  // ---- Helpers de presentación ----

  initials(): string {
    const name = this.data()?.detail?.full_name ?? this.data()?.username ?? '';
    return name.split(' ').slice(0, 2).map((w: string) => w[0]?.toUpperCase() ?? '').join('');
  }

  avatarClass(): string {
    const r = this.data()?.role ?? '';
    if (r === 'ADMIN_PLATFORM') return 'avatar avatar-admin';
    if (r === 'ADMIN_LOCAL') return 'avatar avatar-local';
    return 'avatar avatar-courier';
  }

  roleLabel(): string {
    const r = this.data()?.role ?? '';
    if (r === 'ADMIN_PLATFORM') return 'Admin Plataforma';
    if (r === 'ADMIN_LOCAL') return 'Admin Local';
    if (r === 'COURIER') return 'Repartidor';
    return r;
  }

  roleBadgeClass(): string {
    const r = this.data()?.role ?? '';
    if (r === 'ADMIN_PLATFORM') return 'role-badge badge-admin';
    if (r === 'ADMIN_LOCAL') return 'role-badge badge-local';
    return 'role-badge badge-courier';
  }

  statusLabel(): string {
    const s = this.data()?.detail?.status ?? '';
    if (s === 'APPROVED') return 'Activo';
    if (s === 'INACTIVE') return 'Inactivo';
    if (s === 'PENDING') return 'Pendiente';
    return s;
  }

  formatDate(raw: string): string {
    if (!raw) return '';
    const d = new Date(raw.replace(' ', 'T'));
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString('es-CO', { year: 'numeric', month: 'long' });
  }

  formatShortDate(raw: string): string {
    if (!raw) return '';
    const d = new Date(raw.replace(' ', 'T'));
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
  }

  // ---- Helpers de actividad ----

  activityIcon(item: ActivityItem): string {
    if (item.tipo === 'courier') return 'delivery_dining';
    if (item.tipo === 'ally') return 'storefront';
    return 'check_circle';
  }

  activityIconClass(item: ActivityItem): string {
    if (item.tipo === 'courier') return 'activity-icon icon-courier';
    if (item.tipo === 'ally') return 'activity-icon icon-ally';
    return 'activity-icon icon-delivery';
  }

  activityName(item: ActivityItem): string {
    return item.full_name || item.ally_name || 'Sin nombre';
  }

  activitySub(item: ActivityItem): string {
    if (item.order_id) {
      const total = (item.total_fee ?? 0) + (item.incentivo ?? 0);
      return `+$${total.toLocaleString('es-CO')} · ${item.dropoff_city || ''}`;
    }
    return item.tipo === 'courier' ? 'Repartidor' : 'Aliado';
  }

  activityBadge(item: ActivityItem): string {
    if (item.order_id) return 'Entregado';
    const s = item.status ?? '';
    if (s === 'APPROVED') return 'Activo';
    if (s === 'INACTIVE') return 'Inactivo';
    if (s === 'PENDING') return 'Pendiente';
    return s;
  }

  activityBadgeClass(item: ActivityItem): string {
    if (item.order_id) return 'activity-badge badge-delivered';
    const s = (item.status ?? '').toLowerCase();
    return `activity-badge badge-${s}`;
  }

  activityDate(item: ActivityItem): string {
    return item.delivered_at ?? item.updated_at ?? '';
  }
}
