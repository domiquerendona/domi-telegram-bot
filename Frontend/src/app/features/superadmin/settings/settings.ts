import { Component, OnInit, signal } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

interface PricingField {
  key: string;
  label: string;
  desc: string;
  unit: string;
  tipo: 'money' | 'km';
}

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule],
  template: `
    <div class="page">
      <div class="page-header">
        <h1>Configuración</h1>
        <button class="btn-refresh" (click)="cargar()">↻ Actualizar</button>
      </div>

      <div class="estado" *ngIf="cargando()">Cargando...</div>
      <div class="estado error" *ngIf="error()">{{ error() }}</div>

      <div *ngIf="!cargando() && !error()">

        <div class="seccion">
          <div class="seccion-header">
            <span class="material-symbols-outlined">payments</span>
            <h2>Tarifas de envío</h2>
          </div>
          <div class="panel">
            <div class="grid">
              <div class="campo" *ngFor="let f of campos">
                <label>{{ f.label }}</label>
                <div class="desc">{{ f.desc }}</div>
                <div class="input-wrap">
                  <span class="prefix" *ngIf="f.unit === '$'">$</span>
                  <input
                    type="number"
                    [(ngModel)]="values[f.key]"
                    [class.with-prefix]="f.unit === '$'"
                    min="0"
                    step="{{ f.tipo === 'km' ? '0.1' : '100' }}"
                  />
                  <span class="suffix" *ngIf="f.unit !== '$'">{{ f.unit }}</span>
                </div>
              </div>
            </div>

            <div class="acciones">
              <div class="guardado" *ngIf="guardado()">✓ Cambios guardados</div>
              <button class="btn-guardar" (click)="guardar()" [disabled]="guardando()">
                {{ guardando() ? 'Guardando...' : 'Guardar cambios' }}
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  `,
  styles: [`
    .page { padding: 24px; }
    .page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
    .btn-refresh { padding: 6px 14px; border-radius: 8px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 13px; color: #374151; }
    .btn-refresh:hover { border-color: #4338ca; color: #4338ca; }

    .seccion { margin-bottom: 32px; }
    .seccion-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
    .seccion-header .material-symbols-outlined { font-size: 22px; color: #4338ca; }
    h2 { font-size: 17px; font-weight: 700; margin: 0; color: #111827; }

    .panel { background: white; border-radius: 14px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }

    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }

    .campo label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 4px; }
    .desc { font-size: 11px; color: #9ca3af; margin-bottom: 8px; }

    .input-wrap { display: flex; align-items: center; border: 1px solid #d1d5db; border-radius: 8px; overflow: hidden; background: white; }
    .input-wrap:focus-within { border-color: #4338ca; box-shadow: 0 0 0 2px rgba(67,56,202,0.1); }
    .prefix { padding: 0 10px; font-size: 14px; color: #6b7280; background: #f9fafb; border-right: 1px solid #e5e7eb; height: 38px; display: flex; align-items: center; }
    .suffix { padding: 0 10px; font-size: 13px; color: #6b7280; background: #f9fafb; border-left: 1px solid #e5e7eb; height: 38px; display: flex; align-items: center; white-space: nowrap; }
    input { flex: 1; padding: 8px 12px; border: none; outline: none; font-size: 14px; color: #111827; min-width: 0; }
    input.with-prefix { padding-left: 8px; }

    .acciones { display: flex; align-items: center; justify-content: flex-end; gap: 16px; padding-top: 16px; border-top: 1px solid #f3f4f6; }
    .guardado { font-size: 13px; color: #059669; font-weight: 600; }
    .btn-guardar { padding: 9px 24px; background: #4338ca; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
    .btn-guardar:hover { background: #3730a3; }
    .btn-guardar:disabled { background: #a5b4fc; cursor: not-allowed; }

    .estado { padding: 20px; color: #6b7280; }
    .estado.error { color: #ef4444; }

    @media (max-width: 900px) { .grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 560px) { .grid { grid-template-columns: 1fr; } }
  `]
})
export class SettingsComponent implements OnInit {
  cargando = signal(true);
  error = signal('');
  guardando = signal(false);
  guardado = signal(false);

  values: Record<string, number> = {};

  campos: PricingField[] = [
    { key: 'pricing_precio_0_2km',        label: 'Tarifa 0–2 km',         desc: 'Precio base para distancias cortas',             unit: '$',  tipo: 'money' },
    { key: 'pricing_precio_2_3km',        label: 'Tarifa 2–3 km',         desc: 'Precio para distancias medias cortas',           unit: '$',  tipo: 'money' },
    { key: 'pricing_base_distance_km',    label: 'Distancia base',        desc: 'Km incluidos en la tarifa base',                unit: 'km', tipo: 'km'    },
    { key: 'pricing_km_extra_normal',     label: 'Km extra (normal)',     desc: 'Precio por km adicional en zona normal',        unit: '$',  tipo: 'money' },
    { key: 'pricing_umbral_km_largo',     label: 'Umbral largo plazo',    desc: 'A partir de este km aplica tarifa larga',       unit: 'km', tipo: 'km'    },
    { key: 'pricing_km_extra_largo',      label: 'Km extra (largo)',      desc: 'Precio por km adicional en zona larga',         unit: '$',  tipo: 'money' },
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<Record<string, string>>('http://localhost:8000/admin/settings/pricing').subscribe({
      next: (d) => {
        for (const k of Object.keys(d)) {
          this.values[k] = parseFloat(d[k]) || 0;
        }
        this.cargando.set(false);
      },
      error: () => { this.error.set('No se pudo conectar con el servidor.'); this.cargando.set(false); }
    });
  }

  guardar() {
    this.guardando.set(true);
    this.guardado.set(false);
    this.http.post('http://localhost:8000/admin/settings/pricing', this.values).subscribe({
      next: () => {
        this.guardando.set(false);
        this.guardado.set(true);
        setTimeout(() => this.guardado.set(false), 3000);
      },
      error: () => {
        this.guardando.set(false);
        alert('Error al guardar los cambios.');
      }
    });
  }
}
