import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ElementRef,
  ViewChild,
  NgZone,
  PLATFORM_ID,
  Inject,
} from '@angular/core';
import { isPlatformBrowser, NgIf, NgFor } from '@angular/common';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-mapa',
  standalone: true,
  imports: [NgIf, NgFor],
  template: `
    <div class="mapa-container">
      <div class="mapa-header">
        <h2>Repartidores en tiempo real</h2>
        <div class="mapa-meta">
          <span class="badge badge-green">● {{ couriers.length }} online</span>
          <span class="badge badge-orange">● {{ orders.length }} sin courier</span>
          <span class="ultima" *ngIf="ultimaActualizacion">Actualizado: {{ ultimaActualizacion }}</span>
          <button class="btn-refresh" (click)="cargarDatos()">↻ Actualizar</button>
        </div>
      </div>

      <div class="mapa-layout">
        <div #mapaCanvas class="mapa-canvas"></div>

        <div class="mapa-sidebar">

          <div class="sidebar-section">
            <h3>
              <span class="material-symbols-outlined">delivery_dining</span>
              Repartidores online
            </h3>
            <div *ngIf="cargando" class="empty">Cargando...</div>
            <div *ngIf="!cargando && couriers.length === 0" class="empty">
              Ninguno activo ahora
            </div>
            <div *ngFor="let c of couriers" class="courier-item" (click)="centrarEnCourier(c)">
              <div class="item-name">{{ c.full_name }}</div>
              <div class="item-sub">{{ c.admin_city || '—' }}</div>
              <div class="item-sub" *ngIf="!c.lat">Sin ubicación GPS</div>
              <a *ngIf="c.telegram_id" [href]="'tg://user?id=' + c.telegram_id" class="btn-contact">Contactar</a>
            </div>
          </div>

          <div class="sidebar-section">
            <h3>
              <span class="material-symbols-outlined">inventory_2</span>
              Pedidos sin courier
            </h3>
            <div *ngIf="orders.length === 0" class="empty">Sin pedidos pendientes</div>
            <div *ngFor="let o of orders" class="order-item">
              <div class="item-name">#{{ o.order_id }} — {{ o.ally_name || 'Admin' }}</div>
              <div class="item-sub">{{ o.pickup_address }}</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  `,
  styles: [`
    .mapa-container { padding: 20px; }

    .mapa-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .mapa-header h2 { margin: 0; font-size: 20px; font-weight: 700; }
    .mapa-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

    .badge { padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    .badge-green  { background: #dcfce7; color: #15803d; }
    .badge-orange { background: #fef3c7; color: #92400e; }
    .ultima { font-size: 12px; color: #9ca3af; }

    .btn-refresh { padding: 5px 14px; border: 1px solid #d1d5db; border-radius: 8px; background: white; cursor: pointer; font-size: 13px; color: #374151; }
    .btn-refresh:hover { border-color: #4338ca; color: #4338ca; }

    .mapa-layout { display: flex; gap: 14px; }
    .mapa-canvas { flex: 1; min-width: 0; height: 520px; border-radius: 12px; border: 1px solid #e5e7eb; background: #f1f5f9; }

    .mapa-sidebar { width: 260px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
    .sidebar-section { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }
    .sidebar-section h3 { margin: 0 0 12px 0; font-size: 13px; font-weight: 700; color: #374151; display: flex; align-items: center; gap: 6px; }
    .sidebar-section h3 .material-symbols-outlined { font-size: 17px; color: #4338ca; }

    .empty { font-size: 12px; color: #9ca3af; text-align: center; padding: 10px 0; }

    .courier-item, .order-item { padding: 8px 10px; border-radius: 8px; background: #f9fafb; border: 1px solid #f3f4f6; margin-bottom: 6px; cursor: pointer; }
    .courier-item:hover { border-color: #c7d2fe; background: #eef2ff; }
    .order-item { cursor: default; }
    .item-name { font-weight: 600; font-size: 13px; color: #111827; }
    .item-sub { font-size: 11px; color: #9ca3af; margin-top: 2px; }
    .btn-contact { display: inline-block; margin-top: 5px; font-size: 11px; color: #4338ca; text-decoration: none; font-weight: 600; }
    .btn-contact:hover { text-decoration: underline; }

    @media (max-width: 768px) {
      .mapa-layout { flex-direction: column; }
      .mapa-sidebar { width: 100%; flex-direction: row; overflow-x: auto; }
      .sidebar-section { min-width: 220px; }
    }
  `]
})
export class MapaComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('mapaCanvas') mapaCanvas!: ElementRef;

  couriers: any[] = [];
  orders: any[] = [];
  cargando = true;
  ultimaActualizacion = '';

  private map: any = null;
  private courierMarkers: any[] = [];
  private orderMarkers: any[] = [];
  private intervalo: any = null;
  private resizeObserver: ResizeObserver | null = null;
  private readonly centroDefault: [number, number] = [4.711, -74.0721];
  private readonly isBrowser: boolean;

  constructor(
    private api: ApiService,
    private zone: NgZone,
    @Inject(PLATFORM_ID) platformId: object
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  ngOnInit(): void {
    this.cargarDatos();
    this.intervalo = setInterval(() => this.cargarDatos(), 30000);
  }

  ngAfterViewInit(): void {
    if (!this.isBrowser) return;
    // Doble rAF: garantiza que el browser completó layout y paint antes de inicializar Leaflet
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.initMapa();
      });
    });
  }

  ngOnDestroy(): void {
    if (this.intervalo) clearInterval(this.intervalo);
    if (this.resizeObserver) this.resizeObserver.disconnect();
    if (this.map) this.map.remove();
  }

  private async initMapa(): Promise<void> {
    const L = await import('leaflet');

    // Fix default icon paths broken by webpack
    const iconDefault = L.icon({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
    });
    L.Marker.prototype.options.icon = iconDefault;

    this.map = L.map(this.mapaCanvas.nativeElement, { zoomControl: true }).setView(this.centroDefault, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(this.map);

    // ResizeObserver: llama invalidateSize cada vez que el contenedor cambia de tamaño
    this.resizeObserver = new ResizeObserver(() => {
      this.zone.run(() => this.map?.invalidateSize());
    });
    this.resizeObserver.observe(this.mapaCanvas.nativeElement);

    this.actualizarMarcadores();
  }

  cargarDatos(): void {
    this.api.getActiveCourierLocations().subscribe({
      next: (data) => {
        this.zone.run(() => {
          this.couriers = data;
          this.cargando = false;
          this.ultimaActualizacion = new Date().toLocaleTimeString('es-CO');
          this.actualizarMarcadores();
        });
      },
      error: () => { this.cargando = false; },
    });

    this.api.getUnassignedOrders().subscribe({
      next: (data) => {
        this.zone.run(() => {
          this.orders = data;
          this.actualizarMarcadores();
        });
      },
    });
  }

  centrarEnCourier(c: any): void {
    if (this.map && c.lat && c.lng) {
      this.map.setView([c.lat, c.lng], 15);
    }
  }

  private async actualizarMarcadores(): Promise<void> {
    if (!this.map || !this.isBrowser) return;

    const L = await import('leaflet');

    // Limpiar marcadores previos
    this.courierMarkers.forEach(m => m.remove());
    this.orderMarkers.forEach(m => m.remove());
    this.courierMarkers = [];
    this.orderMarkers = [];

    // Icono repartidor (azul)
    const courierIcon = L.divIcon({
      className: '',
      html: `<div style="background:#4338ca;width:28px;height:28px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;">
               <span style="font-family:'Material Symbols Outlined';font-size:16px;color:white;">delivery_dining</span>
             </div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    // Icono pedido (naranja)
    const orderIcon = L.divIcon({
      className: '',
      html: `<div style="background:#d97706;width:24px;height:24px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;">
               <span style="font-family:'Material Symbols Outlined';font-size:13px;color:white;">inventory_2</span>
             </div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    for (const c of this.couriers) {
      if (!c.lat || !c.lng) continue;
      const marker = L.marker([c.lat, c.lng], { icon: courierIcon })
        .addTo(this.map)
        .bindPopup(`<b>${c.full_name}</b><br>${c.admin_city || ''}`);
      this.courierMarkers.push(marker);
    }

    for (const o of this.orders) {
      if (!o.pickup_lat || !o.pickup_lng) continue;
      const marker = L.marker([o.pickup_lat, o.pickup_lng], { icon: orderIcon })
        .addTo(this.map)
        .bindPopup(`<b>#${o.order_id}</b><br>${o.ally_name || 'Admin'}<br>${o.pickup_address}`);
      this.orderMarkers.push(marker);
    }
  }
}
