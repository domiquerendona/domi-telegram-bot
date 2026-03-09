import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ElementRef,
  ViewChild,
  NgZone,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api';

declare const google: any;

@Component({
  selector: 'app-mapa',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="mapa-container">
      <div class="mapa-header">
        <h2>Repartidores en tiempo real</h2>
        <div class="mapa-meta">
          <span class="badge badge-green">● {{ couriers.length }} online</span>
          <span class="badge badge-red">● {{ orders.length }} sin courier</span>
          <span class="ultima-actualizacion" *ngIf="ultimaActualizacion">
            Actualizado: {{ ultimaActualizacion }}
          </span>
          <button class="btn-refresh" (click)="cargarDatos()">Actualizar</button>
        </div>
      </div>

      <div class="mapa-layout">
        <div #mapaCanvas class="mapa-canvas"></div>

        <div class="mapa-sidebar">
          <div class="sidebar-section">
            <h3>Repartidores online</h3>
            <div *ngIf="cargando" class="loading">Cargando...</div>
            <div *ngIf="!cargando && couriers.length === 0" class="empty">
              Ninguno activo ahora
            </div>
            <ul *ngIf="couriers.length > 0">
              <li *ngFor="let c of couriers" class="courier-item">
                <span class="courier-name">{{ c.full_name }}</span>
                <span class="courier-city">{{ c.admin_city }}</span>
                <a [href]="'tg://user?id=' + c.telegram_id" class="btn-contact">
                  Contactar
                </a>
              </li>
            </ul>
          </div>

          <div class="sidebar-section">
            <h3>Pedidos sin repartidor</h3>
            <div *ngIf="orders.length === 0" class="empty">
              Sin pedidos pendientes
            </div>
            <ul *ngIf="orders.length > 0">
              <li *ngFor="let o of orders" class="order-item">
                <span class="order-id">#{{ o.order_id }}</span>
                <span class="order-ally">{{ o.ally_name }}</span>
                <span class="order-address">{{ o.pickup_address }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .mapa-container {
      padding: 16px;
      height: 100%;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .mapa-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }

    .mapa-header h2 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .mapa-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .badge {
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 500;
    }

    .badge-green {
      background: #dcfce7;
      color: #15803d;
    }

    .badge-red {
      background: #fee2e2;
      color: #b91c1c;
    }

    .ultima-actualizacion {
      font-size: 0.8rem;
      color: #6b7280;
    }

    .btn-refresh {
      padding: 4px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      background: #fff;
      cursor: pointer;
      font-size: 0.85rem;
    }

    .btn-refresh:hover {
      background: #f3f4f6;
    }

    .mapa-layout {
      display: flex;
      gap: 12px;
      flex: 1;
      min-height: 0;
    }

      .mapa-canvas {
      flex: 1;
      height: 100%;
      border-radius: 10px;
      border: 1px solid #e5e7eb;
      background: #f9fafb;
    }

    .mapa-sidebar {
      width: 260px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
    }

    .sidebar-section {
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 12px;
    }

    .sidebar-section h3 {
      margin: 0 0 10px 0;
      font-size: 0.95rem;
      font-weight: 600;
      color: #374151;
    }

    .loading, .empty {
      font-size: 0.85rem;
      color: #9ca3af;
      text-align: center;
      padding: 8px 0;
    }

    ul {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .courier-item, .order-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 8px;
      border-radius: 6px;
      background: #f9fafb;
      border: 1px solid #f3f4f6;
    }

    .courier-name, .order-id {
      font-weight: 600;
      font-size: 0.9rem;
      color: #111827;
    }

    .courier-city, .order-ally, .order-address {
      font-size: 0.8rem;
      color: #6b7280;
    }

    .btn-contact {
      font-size: 0.78rem;
      color: #2563eb;
      text-decoration: none;
      margin-top: 4px;
      align-self: flex-start;
    }

    .btn-contact:hover {
      text-decoration: underline;
    }
  `]
})
export class MapaComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('mapaCanvas') mapaCanvas!: ElementRef;

  couriers: any[] = [];
  orders: any[] = [];
  cargando = true;
  ultimaActualizacion: string = '';

  private map: any = null;
  private markers: any[] = [];
  private intervalo: any = null;
  private readonly centroDefault = { lat: 4.711, lng: -74.0721 };

  constructor(private api: ApiService, private zone: NgZone) {}

  ngOnInit(): void {
    this.cargarDatos();
    this.intervalo = setInterval(() => this.cargarDatos(), 30000);
  }

  ngAfterViewInit(): void {
    this.initMapa();
  }

  ngOnDestroy(): void {
    if (this.intervalo) clearInterval(this.intervalo);
  }

  private initMapa(): void {
    if (typeof google === 'undefined' || !google.maps) {
      setTimeout(() => this.initMapa(), 1000);
      return;
    }

    this.map = new google.maps.Map(this.mapaCanvas.nativeElement, {
      center: this.centroDefault,
      zoom: 13,
      mapTypeId: 'roadmap',
    });
  }

  cargarDatos(): void {
    this.api.getActiveCourierLocations().subscribe({
      next: (couriers) => {
        this.zone.run(() => {
          this.couriers = couriers;
          this.actualizarMarcadores();
          this.cargando = false;
          this.ultimaActualizacion = new Date().toLocaleTimeString('es-CO');
        });
      },
      error: () => (this.cargando = false),
    });

    this.api.getUnassignedOrders().subscribe({
      next: (orders) => {
        this.zone.run(() => {
          this.orders = orders;
          this.actualizarMarcadores();
        });
      },
    });
  }

  private actualizarMarcadores(): void {
    if (!this.map) return;

    this.markers.forEach((m) => m.setMap(null));
    this.markers = [];

    for (const c of this.couriers) {
      if (!c.lat || !c.lng) continue;

      const marker = new google.maps.Marker({
        position: { lat: c.lat, lng: c.lng },
        map: this.map,
        title: c.full_name,
      });

      this.markers.push(marker);
    }
  }
}