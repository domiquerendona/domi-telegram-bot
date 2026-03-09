import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NgIf } from '@angular/common';

interface Stats {
  total_users: number;
  pending_users: number;
  active_users: number;
  blocked_users: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NgIf],
  template: `
    <div class="dashboard">
      <h1>Dashboard</h1>

      <div class="cards" *ngIf="stats()">
        <div class="card blue">
          <span class="material-symbols-outlined">group</span>
          <div>
            <h3>Total Usuarios</h3>
            <p>{{ stats()!.total_users }}</p>
          </div>
        </div>

        <div class="card green">
          <span class="material-symbols-outlined">check_circle</span>
          <div>
            <h3>Usuarios Activos</h3>
            <p>{{ stats()!.active_users }}</p>
          </div>
        </div>

        <div class="card orange">
          <span class="material-symbols-outlined">schedule</span>
          <div>
            <h3>Pendientes de Aprobación</h3>
            <p>{{ stats()!.pending_users }}</p>
          </div>
        </div>

        <div class="card red">
          <span class="material-symbols-outlined">block</span>
          <div>
            <h3>Bloqueados / Inactivos</h3>
            <p>{{ stats()!.blocked_users }}</p>
          </div>
        </div>
      </div>

      <div class="loading" *ngIf="!stats() && !error()">Cargando...</div>
      <div class="error" *ngIf="error()">{{ error() }}</div>
    </div>
  `,
  styles: [`
    .dashboard {
      padding: 24px;
    }

    h1 {
      margin-bottom: 24px;
      font-size: 24px;
      font-weight: 700;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 20px;
    }

    .card {
      padding: 24px;
      border-radius: 12px;
      color: white;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .card span.material-symbols-outlined {
      font-size: 40px;
      opacity: 0.85;
    }

    .card h3 {
      font-size: 13px;
      font-weight: 500;
      opacity: 0.9;
    }

    .card p {
      font-size: 32px;
      font-weight: 700;
      margin-top: 4px;
    }

    .blue   { background: #3b82f6; }
    .green  { background: #10b981; }
    .orange { background: #f59e0b; }
    .red    { background: #ef4444; }

    .loading { color: #6b7280; padding: 20px; }
    .error   { color: #ef4444; padding: 20px; }
  `]
})
export class DashboardComponent implements OnInit {
  stats = signal<Stats | null>(null);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<Stats>('http://localhost:8000/dashboard/stats').subscribe({
      next: (data) => this.stats.set(data),
      error: () => this.error.set('No se pudo conectar con el servidor.')
    });
  }
}