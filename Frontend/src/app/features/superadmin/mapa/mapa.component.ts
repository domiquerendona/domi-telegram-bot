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
  templateUrl: './mapa.component.html',
  styleUrl: './mapa.component.css',
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
  // Colombia: Bogotá como centro por defecto
  private readonly centroDefault = { lat: 4.711, lng: -74.0721 };

  constructor(private api: ApiService, private zone: NgZone) {}

  ngOnInit(): void {
    // Carga inicial de datos
    this.cargarDatos();
    // Polling cada 30 segundos
    this.intervalo = setInterval(() => this.cargarDatos(), 30000);
  }

  ngAfterViewInit(): void {
    this.initMapa();
  }

  ngOnDestroy(): void {
    if (this.intervalo) {
      clearInterval(this.intervalo);
    }
  }

  private initMapa(): void {
    if (typeof google === 'undefined' || !google.maps) {
      // Google Maps aún no cargó — reintentar en 1 segundo
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
      error: () => {
        this.zone.run(() => {
          this.cargando = false;
        });
      },
    });

    this.api.getUnassignedOrders().subscribe({
      next: (orders) => {
        this.zone.run(() => {
          this.orders = orders;
          this.actualizarMarcadores();
        });
      },
      error: () {},
    });
  }

  private actualizarMarcadores(): void {
    if (!this.map) return;

    // Limpiar marcadores anteriores
    this.markers.forEach((m) => m.setMap(null));
    this.markers = [];

    // Marcadores verdes — repartidores ONLINE
    for (const c of this.couriers) {
      if (!c.lat || !c.lng) continue;
      const marker = new google.maps.Marker({
        position: { lat: c.lat, lng: c.lng },
        map: this.map,
        title: c.full_name,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 9,
          fillColor: '#22c55e',
          fillOpacity: 1,
          strokeColor: '#fff',
          strokeWeight: 2,
        },
      });
      const info = new google.maps.InfoWindow({
        content: `<b>${c.full_name}</b><br>${c.admin_city || ''}<br>Actualizado: ${c.last_updated || '?'}`,
      });
      marker.addListener('click', () => info.open(this.map, marker));
      this.markers.push(marker);
    }

    // Marcadores rojos — pedidos sin courier
    for (const o of this.orders) {
      if (!o.pickup_lat || !o.pickup_lng) continue;
      const marker = new google.maps.Marker({
        position: { lat: o.pickup_lat, lng: o.pickup_lng },
        map: this.map,
        title: `Pedido #${o.order_id}`,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 9,
          fillColor: '#ef4444',
          fillOpacity: 1,
          strokeColor: '#fff',
          strokeWeight: 2,
        },
      });
      const info = new google.maps.InfoWindow({
        content: `<b>Pedido #${o.order_id}</b><br>${o.ally_name || ''}<br>${o.pickup_address || ''}<br>Estado: ${o.status}`,
      });
      marker.addListener('click', () => info.open(this.map, marker));
      this.markers.push(marker);
    }
  }
}
