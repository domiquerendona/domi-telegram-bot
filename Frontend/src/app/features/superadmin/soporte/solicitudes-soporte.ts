import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../core/services/toast.service';

interface SupportRequest {
  id: number;
  order_id: number;
  courier_id: number;
  courier_name: string;
  courier_telegram_id: number;
  courier_live_lat: number | null;
  courier_live_lng: number | null;
  customer_address: string;
  customer_city: string;
  customer_barrio: string;
  dropoff_lat: number | null;
  dropoff_lng: number | null;
  order_status: string;
  created_at: string;
  status: string;
}

@Component({
  selector: 'app-solicitudes-soporte',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Soporte — Pin mal ubicado</h1>
        <span class="total">{{ solicitudes().length }} pendiente(s)</span>
        <span class="auto-badge">↻ auto</span>
        <button class="btn-refresh" (click)="cargar()">↻ Actualizar</button>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div class="vacio-card" *ngIf="!cargando() && !error() && solicitudes().length === 0">
        <span class="material-symbols-outlined">check_circle</span>
        <p>Sin solicitudes pendientes</p>
      </div>

      <div class="cards" *ngIf="!cargando() && !error() && solicitudes().length > 0">
        <div class="card" *ngFor="let s of solicitudes()">

          <div class="card-header">
            <span class="badge pedido">#{{ s.order_id }}</span>
            <span class="fecha">{{ formatDate(s.created_at) }}</span>
          </div>

          <div class="info-grid">
            <div class="info-row">
              <span class="label">Repartidor</span>
              <span class="valor">{{ s.courier_name }}</span>
            </div>
            <div class="info-row">
              <span class="label">Destino</span>
              <span class="valor">{{ s.customer_address }}<span *ngIf="s.customer_barrio">, {{ s.customer_barrio }}</span><span *ngIf="s.customer_city">, {{ s.customer_city }}</span></span>
            </div>
            <div class="info-row">
              <span class="label">Estado pedido</span>
              <span class="valor badge-estado" [class]="s.order_status.toLowerCase()">{{ etiqueta(s.order_status) }}</span>
            </div>
          </div>

          <div class="links">
            <a *ngIf="s.dropoff_lat && s.dropoff_lng"
               [href]="mapsLink(s.dropoff_lat, s.dropoff_lng)"
               target="_blank" class="link-map pin">
              <span class="material-symbols-outlined">location_on</span> Pin de entrega
            </a>
            <a *ngIf="s.courier_live_lat && s.courier_live_lng"
               [href]="mapsLink(s.courier_live_lat, s.courier_live_lng)"
               target="_blank" class="link-map courier">
              <span class="material-symbols-outlined">delivery_dining</span> Ubicación courier
            </a>
            <a [href]="telegramLink(s.courier_telegram_id)"
               target="_blank" class="link-tg">
              <span class="material-symbols-outlined">chat</span> Hablar con {{ s.courier_name }}
            </a>
          </div>

          <div class="acciones" *ngIf="!resolviendoId() || resolviendoId() !== s.id">
            <button class="btn btn-fin" (click)="resolver(s, 'fin')">
              Finalizar entrega
            </button>
            <button class="btn btn-courier" (click)="resolver(s, 'cancel_courier')">
              Cancelar — falla courier
            </button>
            <button class="btn btn-ally" (click)="resolver(s, 'cancel_ally')">
              Cancelar — falla aliado/admin
            </button>
          </div>

          <div class="resolviendo" *ngIf="resolviendoId() === s.id">
            Procesando...
          </div>

        </div>
      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
    .total { font-size: 14px; color: #6b7280; }
    .auto-badge { font-size: 11px; color: #10b981; font-weight: 600; background: #d1fae5; padding: 2px 8px; border-radius: 10px; }
    .btn-refresh { margin-left: auto; padding: 6px 14px; border-radius: 8px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 13px; color: #374151; }
    .btn-refresh:hover { border-color: #4338ca; color: #4338ca; }

    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }

    .vacio-card {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 60px 24px; background: white; border-radius: 12px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08); color: #9ca3af; gap: 8px;
    }
    .vacio-card .material-symbols-outlined { font-size: 48px; color: #10b981; }
    .vacio-card p { font-size: 16px; margin: 0; }

    .cards { display: flex; flex-direction: column; gap: 16px; }

    .card {
      background: white; border-radius: 12px; padding: 20px 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-left: 4px solid #f59e0b;
    }

    .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
    .badge.pedido { background: #ede9fe; color: #5b21b6; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 700; }
    .fecha { font-size: 12px; color: #9ca3af; }

    .info-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
    .info-row { display: flex; gap: 12px; font-size: 14px; }
    .label { color: #6b7280; min-width: 110px; font-weight: 500; flex-shrink: 0; }
    .valor { color: #111827; }

    .badge-estado { padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; }
    .badge-estado.accepted { background: #ede9fe; color: #5b21b6; }
    .badge-estado.picked_up { background: #fce7f3; color: #9d174d; }

    .links { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
    .link-map, .link-tg {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
      text-decoration: none; transition: opacity 0.15s;
    }
    .link-map:hover, .link-tg:hover { opacity: 0.8; }
    .link-map.pin { background: #fef3c7; color: #92400e; }
    .link-map.courier { background: #dbeafe; color: #1e40af; }
    .link-tg { background: #e0f2fe; color: #0369a1; }
    .link-map .material-symbols-outlined, .link-tg .material-symbols-outlined { font-size: 18px; }

    .acciones { display: flex; flex-wrap: wrap; gap: 10px; }
    .btn {
      padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
      font-size: 13px; font-weight: 600; transition: opacity 0.15s;
    }
    .btn:hover { opacity: 0.85; }
    .btn-fin { background: #d1fae5; color: #065f46; }
    .btn-courier { background: #fee2e2; color: #991b1b; }
    .btn-ally { background: #fef3c7; color: #92400e; }

    .resolviendo { color: #6b7280; font-size: 14px; padding: 8px 0; }
  `]
})
export class SolicitudesSoporteComponent implements OnInit, OnDestroy {
  solicitudes = signal<SupportRequest[]>([]);
  cargando = signal(true);
  error = signal('');
  resolviendoId = signal<number | null>(null);

  private intervalo: any = null;

  private toast = inject(ToastService);
  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.cargar();
    this.intervalo = setInterval(() => this.cargar(), 30000);
  }

  ngOnDestroy() {
    if (this.intervalo) clearInterval(this.intervalo);
  }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<SupportRequest[]>(`${environment.apiBaseUrl}/admin/support-requests`).subscribe({
      next: (data) => { this.solicitudes.set(data); this.cargando.set(false); },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  resolver(s: SupportRequest, action: string) {
    const labels: Record<string, string> = {
      fin: 'Finalizar la entrega',
      cancel_courier: 'Cancelar con falla del courier',
      cancel_ally: 'Cancelar con falla del aliado/admin',
    };
    if (!window.confirm(`¿${labels[action]} para el pedido #${s.order_id}?`)) return;

    this.resolviendoId.set(s.id);
    this.http.post(`${environment.apiBaseUrl}/admin/support-requests/${s.id}/resolve`, { action }).subscribe({
      next: () => { this.resolviendoId.set(null); this.toast.success('Solicitud resuelta.'); this.cargar(); },
      error: (e) => {
        this.resolviendoId.set(null);
        this.toast.error(e.error?.detail ?? 'Error al procesar la solicitud.');
      }
    });
  }

  mapsLink(lat: number, lng: number) {
    return `https://www.google.com/maps?q=${lat},${lng}`;
  }

  telegramLink(telegramId: number) {
    return `https://t.me/${telegramId}`;
  }

  etiqueta(s: string) {
    const map: Record<string, string> = {
      ACCEPTED: 'Aceptado', PICKED_UP: 'Recogido',
    };
    return map[s] ?? s;
  }

  formatDate(dt: string) {
    if (!dt) return '—';
    return dt.slice(0, 16).replace('T', ' ');
  }
}
