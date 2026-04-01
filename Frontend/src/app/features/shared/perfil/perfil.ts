import { Component, OnInit, signal } from '@angular/core';
import { NgIf } from '@angular/common';
import { HttpClient } from '@angular/common/http';
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
  detail: ProfileDetail | null;
}

@Component({
  selector: 'app-perfil',
  standalone: true,
  imports: [NgIf],
  template: `
  <div class="page">
    <h2 class="title">Mi Perfil</h2>

    <div *ngIf="cargando()" class="loading">Cargando...</div>
    <div *ngIf="error()" class="error">{{ error() }}</div>

    <div *ngIf="data()" class="card">
      <div class="avatar">
        <span class="material-symbols-outlined">{{ roleIcon() }}</span>
      </div>

      <div class="info-section">
        <h3>{{ data()!.detail?.full_name ?? data()!.username }}</h3>
        <span class="role-badge" [class]="roleBadgeClass()">{{ roleLabel() }}</span>
      </div>

      <div class="fields">
        <div class="field">
          <span class="field-label">Usuario del sistema</span>
          <span class="field-value">{{ data()!.username }}</span>
        </div>

        <div *ngIf="data()!.detail?.phone" class="field">
          <span class="field-label">Teléfono</span>
          <span class="field-value">{{ data()!.detail!.phone }}</span>
        </div>

        <div *ngIf="data()!.detail?.city" class="field">
          <span class="field-label">Ciudad</span>
          <span class="field-value">{{ data()!.detail!.city }}</span>
        </div>

        <div *ngIf="data()!.detail?.vehicle_type" class="field">
          <span class="field-label">Vehículo</span>
          <span class="field-value">{{ data()!.detail!.vehicle_type }}</span>
        </div>

        <div *ngIf="data()!.detail?.status" class="field">
          <span class="field-label">Estado</span>
          <span class="field-value status" [class]="'status-' + data()!.detail!.status?.toLowerCase()">
            {{ data()!.detail!.status }}
          </span>
        </div>
      </div>
    </div>
  </div>
  `,
  styles: [`
  .page { max-width: 560px; }
  .title { font-size: 22px; font-weight: 700; color: #1f2937; margin-bottom: 24px; }
  .loading { color: #6b7280; }
  .error { color: #dc2626; background: #fef2f2; padding: 12px; border-radius: 8px; }

  .card {
    background: white;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }

  .avatar {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: linear-gradient(135deg, #059669, #2563eb);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }

  .avatar span {
    color: white;
    font-size: 36px;
  }

  .info-section {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }

  .info-section h3 {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }

  .role-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .badge-admin    { background: #ede9fe; color: #7c3aed; }
  .badge-local    { background: #dbeafe; color: #2563eb; }
  .badge-courier  { background: #d1fae5; color: #059669; }

  .fields {
    display: flex;
    flex-direction: column;
    gap: 16px;
    border-top: 1px solid #f3f4f6;
    padding-top: 20px;
  }

  .field {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .field-label { font-size: 13px; color: #6b7280; }
  .field-value { font-size: 14px; font-weight: 600; color: #111827; }

  .status { padding: 3px 10px; border-radius: 20px; font-size: 12px; }
  .status-approved  { background: #d1fae5; color: #065f46; }
  .status-inactive  { background: #f3f4f6; color: #4b5563; }
  .status-pending   { background: #fef3c7; color: #92400e; }
  `]
})
export class PerfilComponent implements OnInit {
  data = signal<ProfileResponse | null>(null);
  cargando = signal(true);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() {
    const token = localStorage.getItem('admin_token');
    this.http.get<ProfileResponse>(`${environment.apiBaseUrl}/profile`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => { this.data.set(res); this.cargando.set(false); },
      error: (e) => { this.error.set(e.error?.detail ?? 'Error al cargar perfil'); this.cargando.set(false); }
    });
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

  roleIcon(): string {
    const r = this.data()?.role ?? '';
    if (r === 'COURIER') return 'delivery_dining';
    return 'manage_accounts';
  }
}
