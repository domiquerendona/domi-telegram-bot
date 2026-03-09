
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dashboard-wrapper">

      <!-- TOP STATS CARDS -->
      <div class="stats-grid">

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-title">Repartidores Activos</span>
            <span class="stat-icon green-icon">
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="#22c55e" stroke-width="2" stroke-linecap="round"/>
                <circle cx="9" cy="7" r="4" stroke="#22c55e" stroke-width="2"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="#22c55e" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </span>
          </div>
          <div class="stat-number">2</div>
          <div class="stat-sub green-text">+2 esta semana</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-title">Aliados Activos</span>
            <span class="stat-icon blue-icon">
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="#3b82f6" stroke-width="2" stroke-linecap="round"/>
                <polyline points="9 22 9 12 15 12 15 22" stroke="#3b82f6" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </span>
          </div>
          <div class="stat-number">2</div>
          <div class="stat-sub blue-text">+1 esta semana</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-title">Administradores</span>
            <span class="stat-icon purple-icon">
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="#a855f7" stroke-width="2" stroke-linecap="round"/>
                <circle cx="9" cy="7" r="4" stroke="#a855f7" stroke-width="2"/>
                <line x1="19" y1="8" x2="19" y2="14" stroke="#a855f7" stroke-width="2" stroke-linecap="round"/>
                <line x1="22" y1="11" x2="16" y2="11" stroke="#a855f7" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </span>
          </div>
          <div class="stat-number">1</div>
          <div class="stat-sub gray-text">Sistema operativo</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-title">Ganancia del Día</span>
            <span class="stat-icon orange-icon">
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <polyline points="17 6 23 6 23 12" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </div>
          <div class="stat-number money">\$43.500</div>
          <div class="stat-sub green-text">+12% vs ayer</div>
        </div>

      </div>

      <!-- ORDER STATUS CARDS -->
      <div class="status-grid">

        <div class="status-card yellow-card">
          <div class="status-header">
            <span class="status-title">Pendientes</span>
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="#f59e0b" stroke-width="2"/>
              <polyline points="12 6 12 12 16 14" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="status-number yellow-num">2</div>
          <div class="status-bar">
            <div class="bar-track">
              <div class="bar-fill yellow-bar" style="width: 40%"></div>
            </div>
          </div>
          <div class="status-label yellow-label">Esperando asignación</div>
        </div>

        <div class="status-card blue-card">
          <div class="status-header">
            <span class="status-title">En Curso</span>
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="#3b82f6" stroke-width="2"/>
              <path d="M12 8v4l3 3" stroke="#3b82f6" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="status-number blue-num">2</div>
          <div class="status-bar">
            <div class="bar-track">
              <div class="bar-fill blue-bar" style="width: 40%"></div>
            </div>
          </div>
          <div class="status-label blue-label">En camino</div>
        </div>

        <div class="status-card green-card">
          <div class="status-header">
            <span class="status-title">Entregados</span>
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="#22c55e" stroke-width="2"/>
              <polyline points="9 12 11 14 15 10" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="status-number green-num">3</div>
          <div class="status-bar">
            <div class="bar-track">
              <div class="bar-fill green-bar" style="width: 60%"></div>
            </div>
          </div>
          <div class="status-label green-label">Hoy 3 entregados</div>
        </div>

      </div>

      <!-- PENDING REGISTRATIONS -->
      <div class="section-card">
        <h2 class="section-title">Últimos Registros Pendientes</h2>

        <div class="registration-item">
          <div class="reg-info">
            <div class="reg-name">Carlos Rodríguez</div>
            <div class="reg-tags">
              <span class="tag tag-role">Repartidor</span>
              <span class="tag tag-pending">pendiente</span>
              <span class="tag tag-date">2024-02-25</span>
            </div>
          </div>
          <div class="reg-actions">
            <button class="btn-approve">Aprobar</button>
            <button class="btn-reject">Rechazar</button>
          </div>
        </div>

        <div class="divider"></div>

        <div class="registration-item">
          <div class="reg-info">
            <div class="reg-name">Farmacia Central</div>
            <div class="reg-tags">
              <span class="tag tag-role">Aliado</span>
              <span class="tag tag-pending">pendiente</span>
              <span class="tag tag-date">2024-02-24</span>
            </div>
          </div>
          <div class="reg-actions">
            <button class="btn-approve">Aprobar</button>
            <button class="btn-reject">Rechazar</button>
          </div>
        </div>
      </div>

      <!-- RECENT ORDERS -->
      <div class="section-card">
        <h2 class="section-title">Pedidos Recientes</h2>

        <div class="order-item" *ngFor="let order of recentOrders">
          <div class="order-info">
            <div class="order-id">{{ order.id }}</div>
            <div class="order-people">{{ order.people }}</div>
            <div class="order-date">{{ order.date }}</div>
          </div>
          <div class="order-right">
            <div class="order-amount">
              <div class="order-price">{{ order.price }}</div>
              <div class="order-commission">Comisión: {{ order.commission }}</div>
            </div>
            <span class="order-status" [ngClass]="order.statusClass">{{ order.status }}</span>
          </div>
        </div>

      </div>

    </div>
  `,
  styles: [`
    :host {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      display: block;
      background: #f4f6fb;
      min-height: 100vh;
      color: #1e293b;
    }

    .dashboard-wrapper {
      padding: 24px;
      max-width: 1100px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* ── STATS GRID ─────────────────────────────── */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }

    .stat-card {
      background: #fff;
      border-radius: 14px;
      padding: 20px 22px 18px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    }

    .stat-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .stat-title {
      font-size: 13px;
      color: #64748b;
      font-weight: 500;
    }

    .stat-icon {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .green-icon  { background: #f0fdf4; }
    .blue-icon   { background: #eff6ff; }
    .purple-icon { background: #faf5ff; }
    .orange-icon { background: #fff7ed; }

    .stat-number {
      font-size: 30px;
      font-weight: 700;
      color: #0f172a;
      line-height: 1;
      margin-bottom: 6px;
    }

    .stat-number.money { font-size: 24px; }

    .stat-sub {
      font-size: 12px;
      font-weight: 500;
    }

    .green-text  { color: #22c55e; }
    .blue-text   { color: #3b82f6; }
    .gray-text   { color: #94a3b8; }

    /* ── STATUS GRID ─────────────────────────────── */
    .status-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    .status-card {
      border-radius: 14px;
      padding: 22px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    }

    .yellow-card { background: #fffbeb; border: 1px solid #fef3c7; }
    .blue-card   { background: #eff6ff; border: 1px solid #dbeafe; }
    .green-card  { background: #f0fdf4; border: 1px solid #dcfce7; }

    .status-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }

    .status-title {
      font-size: 14px;
      font-weight: 600;
      color: #374151;
    }

    .status-number {
      font-size: 38px;
      font-weight: 800;
      line-height: 1;
      margin-bottom: 14px;
    }

    .yellow-num { color: #f59e0b; }
    .blue-num   { color: #3b82f6; }
    .green-num  { color: #22c55e; }

    .status-bar { margin-bottom: 10px; }

    .bar-track {
      height: 6px;
      background: rgba(0,0,0,0.08);
      border-radius: 99px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      border-radius: 99px;
      transition: width 0.6s ease;
    }

    .yellow-bar { background: #f59e0b; }
    .blue-bar   { background: #3b82f6; }
    .green-bar  { background: #22c55e; }

    .status-label {
      font-size: 12px;
      font-weight: 500;
    }

    .yellow-label { color: #f59e0b; }
    .blue-label   { color: #3b82f6; }
    .green-label  { color: #22c55e; }

    /* ── SECTION CARDS ───────────────────────────── */
    .section-card {
      background: #fff;
      border-radius: 14px;
      padding: 24px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    }

    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: #0f172a;
      margin: 0 0 20px;
    }

    /* ── REGISTRATIONS ───────────────────────────── */
    .registration-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
    }

    .reg-name {
      font-size: 15px;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 8px;
    }

    .reg-tags {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .tag {
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
    }

    .tag-role    { background: #e0e7ff; color: #4338ca; }
    .tag-pending { background: #fef9c3; color: #b45309; }
    .tag-date    { background: #f1f5f9; color: #64748b; }

    .reg-actions {
      display: flex;
      gap: 10px;
    }

    .btn-approve {
      padding: 9px 20px;
      background: #1e293b;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-approve:hover { background: #0f172a; }

    .btn-reject {
      padding: 9px 20px;
      background: #ef4444;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-reject:hover { background: #dc2626; }

    .divider {
      height: 1px;
      background: #f1f5f9;
      margin: 4px 0;
    }

    /* ── ORDERS ──────────────────────────────────── */
    .order-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 0;
      border-bottom: 1px solid #f1f5f9;
    }

    .order-item:last-child { border-bottom: none; }

    .order-id {
      font-size: 14px;
      font-weight: 700;
      color: #1e293b;
      margin-bottom: 4px;
    }

    .order-people {
      font-size: 13px;
      color: #475569;
      margin-bottom: 3px;
    }

    .order-date {
      font-size: 12px;
      color: #94a3b8;
    }

    .order-right {
      display: flex;
      align-items: center;
      gap: 20px;
    }

    .order-price {
      font-size: 16px;
      font-weight: 700;
      color: #0f172a;
      text-align: right;
    }

    .order-commission {
      font-size: 12px;
      color: #94a3b8;
      text-align: right;
    }

    .order-status {
      padding: 5px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
    }

    .status-en-curso  { background: #dbeafe; color: #1d4ed8; }
    .status-entregado { background: #dcfce7; color: #15803d; }
    .status-pendiente { background: #fef9c3; color: #a16207; }

    /* ── RESPONSIVE ──────────────────────────────── */
    @media (max-width: 900px) {
      .stats-grid { grid-template-columns: repeat(2, 1fr); }
      .status-grid { grid-template-columns: repeat(2, 1fr); }
    }

    @media (max-width: 600px) {
      .stats-grid  { grid-template-columns: 1fr; }
      .status-grid { grid-template-columns: 1fr; }
      .registration-item { flex-direction: column; align-items: flex-start; gap: 12px; }
      .order-item { flex-direction: column; align-items: flex-start; gap: 8px; }
    }
  `]
})
export class DashboardComponent {
  recentOrders = [
    {
      id: 'PED-001',
      people: 'Ana López • Juan Pérez',
      date: '2024-02-25 10:30',
      price: '$45.000',
      commission: '$4.500',
      status: 'En Curso',
      statusClass: 'status-en-curso'
    },
    {
      id: 'PED-002',
      people: 'Pedro Sánchez • María González',
      date: '2024-02-25 09:15',
      price: '$120.000',
      commission: '$12.000',
      status: 'Entregado',
      statusClass: 'status-entregado'
    },
    {
      id: 'PED-003',
      people: 'Laura Martínez • Carlos López',
      date: '2024-02-25 08:45',
      price: '$67.500',
      commission: '$6.750',
      status: 'Pendiente',
      statusClass: 'status-pendiente'
    }
  ];
}
