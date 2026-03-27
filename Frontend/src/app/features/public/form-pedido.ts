import {
  Component,
  OnInit,
  OnDestroy,
  signal,
  ViewChild,
  ElementRef,
  NgZone,
  PLATFORM_ID,
  Inject,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgIf, NgFor, isPlatformBrowser } from '@angular/common';
import { ApiService } from '../../core/services/api';

// ─── Interfaces ──────────────────────────────────────────────────────────────

interface AllyInfo {
  ally_id: number;
  ally_name: string;
  message: string;
  delivery_subsidy: number;
  min_purchase_for_subsidy: number | null;
}

interface SavedAddress {
  id: number;
  label: string | null;
  address_text: string;
  city: string | null;
  barrio: string | null;
}

interface LookupResult {
  exists: boolean;
  customer_name: string | null;
  addresses: SavedAddress[];
  message: string;
}

type Step =
  | 'validating'
  | 'invalid'
  | 'phone'
  | 'lookup'
  | 'existing'
  | 'fill'
  | 'map'
  | 'submitting'
  | 'success';

type FillContext = 'new_customer' | 'new_address' | 'saved_address';

// ─── Component ───────────────────────────────────────────────────────────────

@Component({
  selector: 'app-form-pedido',
  standalone: true,
  imports: [FormsModule, NgIf, NgFor],
  template: `
    <div class="bg">
      <div class="card">

        <!-- Header: visible una vez cargado el aliado -->
        <div class="brand" *ngIf="allyInfo()">
          <div class="brand-icon">🛵</div>
          <h1>{{ allyInfo()!.ally_name }}</h1>
          <p>Solicitud de domicilio</p>
        </div>

        <!-- PASO: validando token -->
        <div class="step" *ngIf="step() === 'validating'">
          <div class="loading">Verificando enlace...</div>
        </div>

        <!-- PASO: token inválido -->
        <div class="step" *ngIf="step() === 'invalid'">
          <div class="brand">
            <div class="brand-icon">❌</div>
            <h1>Enlace no válido</h1>
          </div>
          <div class="info-box error-box">
            Este enlace no es válido o el aliado no está activo.
            Por favor contacta directamente al negocio.
          </div>
        </div>

        <!-- PASO: ingresar teléfono -->
        <div class="step" *ngIf="step() === 'phone'">
          <div class="intro-msg">{{ allyInfo()!.message }}</div>
          <div class="section-label">¿Cuál es tu número de teléfono?</div>
          <div class="field">
            <label>Teléfono</label>
            <input
              type="tel"
              [(ngModel)]="phone"
              name="phone"
              placeholder="Ej: 3001234567"
              (keyup.enter)="doLookup()"
            />
          </div>
          <div class="error-msg" *ngIf="error()">{{ error() }}</div>
          <button class="btn-primary" (click)="doLookup()" [disabled]="!phone.trim()">
            Continuar
          </button>
        </div>

        <!-- PASO: buscando cliente -->
        <div class="step" *ngIf="step() === 'lookup'">
          <div class="loading">Buscando tus datos...</div>
        </div>

        <!-- PASO: cliente existente — seleccionar dirección -->
        <div class="step" *ngIf="step() === 'existing'">
          <div class="customer-greeting">
            Hola, <strong>{{ lookupResult()!.customer_name }}</strong>
          </div>
          <div class="info-box">{{ lookupResult()!.message }}</div>

          <div *ngIf="lookupResult()!.addresses.length > 0">
            <div class="section-label">Tus direcciones guardadas</div>
            <div class="addr-list">
              <div
                class="addr-item"
                *ngFor="let addr of lookupResult()!.addresses"
                (click)="selectSavedAddress(addr)"
              >
                <div class="addr-label">{{ addr.label || 'Dirección' }}</div>
                <div class="addr-text">{{ addr.address_text }}</div>
                <div class="addr-sub" *ngIf="addr.barrio">
                  {{ addr.barrio }}{{ addr.city ? ', ' + addr.city : '' }}
                </div>
              </div>
            </div>
          </div>

          <button class="btn-secondary" (click)="useNewAddress()">
            + Usar otra dirección
          </button>
        </div>

        <!-- PASO: completar datos (cliente nuevo / dirección nueva / guardada) -->
        <div class="step" *ngIf="step() === 'fill'">

          <!-- Badge de contexto -->
          <div class="context-badge" *ngIf="fillContext === 'new_customer'">Cliente nuevo</div>
          <div class="context-badge context-badge--saved" *ngIf="fillContext === 'saved_address'">Dirección guardada</div>
          <div class="context-badge context-badge--new-addr" *ngIf="fillContext === 'new_address'">Nueva dirección</div>

          <!-- Nombre: editable si es cliente nuevo, readonly si ya existe -->
          <div class="field" *ngIf="fillContext === 'new_customer'">
            <label>Tu nombre</label>
            <input
              type="text"
              [(ngModel)]="formName"
              name="formName"
              placeholder="Ej: María González"
            />
          </div>
          <div class="readonly-field" *ngIf="fillContext !== 'new_customer'">
            <label>Nombre</label>
            <div class="readonly-val">{{ formName }}</div>
          </div>

          <!-- Teléfono: siempre readonly (viene del paso 1) -->
          <div class="readonly-field">
            <label>Teléfono</label>
            <div class="readonly-val">{{ phone }}</div>
          </div>

          <!-- Dirección de entrega -->
          <div class="section-label">Dirección de entrega</div>
          <div class="field">
            <label>Dirección</label>
            <input
              type="text"
              [(ngModel)]="formAddress"
              name="formAddress"
              placeholder="Ej: Cra 5 #10-20"
              (ngModelChange)="onAddressChange()"
            />
          </div>

          <div class="row-fields">
            <div class="field">
              <label>Barrio</label>
              <input
                type="text"
                [(ngModel)]="formBarrio"
                name="formBarrio"
                placeholder="Ej: Chapinero"
                (ngModelChange)="onAddressChange()"
              />
            </div>
            <div class="field">
              <label>Ciudad</label>
              <input
                type="text"
                [(ngModel)]="formCity"
                name="formCity"
                placeholder="Ej: Bogotá"
                (ngModelChange)="onAddressChange()"
              />
            </div>
          </div>

          <div class="field">
            <label>
              Notas para el repartidor
              <span class="optional">(opcional)</span>
            </label>
            <input
              type="text"
              [(ngModel)]="formNotes"
              name="formNotes"
              placeholder="Ej: Edificio azul, piso 3, timbre 301"
            />
          </div>

          <div class="field">
            <label>
              Valor aproximado de tu compra
              <span class="optional">(opcional)</span>
            </label>
            <input
              type="number"
              [(ngModel)]="purchaseAmountDeclared"
              name="purchaseAmountDeclared"
              placeholder="Ej: 50000"
              min="0"
            />
            <div class="subsidy-hint"
              *ngIf="allyInfo()?.min_purchase_for_subsidy != null && allyInfo()!.delivery_subsidy > 0">
              Este aliado puede subsidiar {{ formatCOP(allyInfo()!.delivery_subsidy) }} del domicilio en compras desde {{ formatCOP(allyInfo()!.min_purchase_for_subsidy!) }}. El valor final se confirma al crear el pedido.
            </div>
          </div>

          <div class="error-msg" *ngIf="error()">{{ error() }}</div>

          <!-- saved_address: enviar directo; new_customer / new_address: ir al mapa -->
          <button
            class="btn-primary"
            (click)="fillContext === 'saved_address' ? doSubmit() : goToMap()"
            [disabled]="!canSubmit()"
          >
            {{ fillContext === 'saved_address' ? 'Enviar solicitud' : 'Continuar al mapa' }}
          </button>
          <button class="btn-ghost" (click)="goBack()">
            ← Volver
          </button>
        </div>

        <!-- PASO: confirmar ubicación en mapa -->
        <div class="step" *ngIf="step() === 'map'">

          <!-- Badge de contexto -->
          <div class="context-badge" *ngIf="fillContext === 'new_customer'">Cliente nuevo</div>
          <div class="context-badge context-badge--new-addr" *ngIf="fillContext === 'new_address'">Nueva dirección</div>

          <div class="section-label">Confirma el punto exacto de entrega</div>

          <!-- Indicador de estado de ubicación -->
          <div class="loc-status" [class.loc-confirmed]="locationConfirmed">
            <span *ngIf="!locationConfirmed">📍 Toca el mapa para fijar el punto de entrega</span>
            <span *ngIf="locationConfirmed">✅ Punto fijado — puedes arrastrarlo para ajustar</span>
          </div>

          <!-- Contenedor del mapa -->
          <div #pickerMap class="picker-map"></div>

          <!-- Cotización -->
          <div class="quote-loading" *ngIf="quoteLoading">
            Calculando valor del domicilio...
          </div>

          <!-- Desglose (cuando hay cotización) -->
          <div class="quote-breakdown" *ngIf="!quoteLoading && totalBase !== null">

            <!-- Fila tarifa base (solo si hay subsidio) -->
            <div class="breakdown-row" *ngIf="subsidioAliado > 0">
              <span>Tarifa del domicilio</span>
              <span>{{ formatCOP(quotedPrice!) }}</span>
            </div>

            <!-- Fila descuento (solo si hay subsidio) -->
            <div class="breakdown-row breakdown-discount" *ngIf="subsidioAliado > 0">
              <span>Descuento del aliado</span>
              <span>- {{ formatCOP(subsidioAliado) }}</span>
            </div>

            <!-- Fila costo base -->
            <div class="breakdown-row breakdown-base">
              <span>{{ subsidioAliado > 0 ? 'Tu costo base' : 'Valor del domicilio' }}</span>
              <span>{{ formatCOP(totalBase) }}</span>
            </div>

            <!-- Selector de incentivo -->
            <div class="incentivo-label">¿Agregar un incentivo al repartidor?</div>
            <div class="incentivo-options">
              <button
                class="inc-btn"
                [class.inc-active]="incentivoCliente === 0"
                (click)="setIncentivo(0)"
              >Sin extra</button>
              <button
                class="inc-btn"
                [class.inc-active]="incentivoCliente === 1000"
                (click)="setIncentivo(1000)"
              >+$1.000</button>
              <button
                class="inc-btn"
                [class.inc-active]="incentivoCliente === 2000"
                (click)="setIncentivo(2000)"
              >+$2.000</button>
              <button
                class="inc-btn"
                [class.inc-active]="incentivoCliente === 3000"
                (click)="setIncentivo(3000)"
              >+$3.000</button>
            </div>

            <!-- Total final -->
            <div class="breakdown-total">
              <span>Total a pagar</span>
              <span>{{ formatCOP(totalCliente!) }}</span>
            </div>

            <!-- Nota subsidio condicional: se muestra cuando subsidio no está descontado -->
            <div class="subsidy-conditional-note" *ngIf="subsidyConditional && quoteMessage">
              {{ quoteMessage }}
            </div>
          </div>

          <!-- Sin cotización disponible -->
          <div class="quote-unavailable" *ngIf="!quoteLoading && locationConfirmed && totalBase === null && quoteMessage">
            {{ quoteMessage }}
          </div>

          <div class="error-msg" *ngIf="error()">{{ error() }}</div>

          <button
            class="btn-primary"
            (click)="confirmLocation()"
            [disabled]="!locationConfirmed"
          >
            Confirmar y enviar
          </button>
          <button class="btn-secondary" (click)="skipMap()">
            Enviar sin confirmar mapa
          </button>
          <button class="btn-ghost" (click)="goBack()">
            ← Volver a dirección
          </button>
        </div>

        <!-- PASO: enviando -->
        <div class="step" *ngIf="step() === 'submitting'">
          <div class="loading">Enviando solicitud...</div>
        </div>

        <!-- PASO: éxito -->
        <div class="step" *ngIf="step() === 'success'">
          <div class="success-icon">✅</div>
          <div class="info-box success-box">{{ successMessage() }}</div>
          <p class="success-sub">
            El aliado revisará tu solicitud y se pondrá en contacto contigo pronto.
          </p>
        </div>

      </div>
    </div>
  `,
  styles: [`
    .bg {
      min-height: 100vh;
      background: linear-gradient(135deg, #065f46 0%, #059669 60%, #34d399 100%);
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 32px 16px 48px;
    }

    .card {
      background: white;
      border-radius: 20px;
      padding: 36px 28px;
      width: 100%;
      max-width: 480px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
    }

    /* ── Brand header ── */
    .brand {
      text-align: center;
      margin-bottom: 28px;
    }
    .brand-icon { font-size: 40px; margin-bottom: 8px; }
    .brand h1 { font-size: 22px; font-weight: 800; color: #111827; margin: 0 0 4px; }
    .brand p  { font-size: 13px; color: #6b7280; margin: 0; }

    /* ── Loading ── */
    .loading {
      text-align: center;
      padding: 48px 0;
      color: #6b7280;
      font-size: 15px;
    }

    /* ── Intro message ── */
    .intro-msg {
      font-size: 14px;
      color: #374151;
      line-height: 1.6;
      margin-bottom: 24px;
      padding: 14px;
      background: #f0fdf4;
      border-radius: 10px;
      border-left: 3px solid #059669;
    }

    /* ── Section labels ── */
    .section-label {
      font-size: 12px;
      font-weight: 700;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: 20px 0 10px;
    }

    /* ── Fields ── */
    .field { margin-bottom: 16px; }

    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #374151;
      margin-bottom: 6px;
    }
    .optional { font-weight: 400; color: #9ca3af; }

    input {
      width: 100%;
      padding: 11px 13px;
      border: 1.5px solid #d1d5db;
      border-radius: 10px;
      font-size: 15px;
      color: #111827;
      outline: none;
      box-sizing: border-box;
      transition: border-color 0.2s;
    }
    input:focus { border-color: #059669; }

    .readonly-field { margin-bottom: 16px; }
    .readonly-val {
      padding: 11px 13px;
      background: #f3f4f6;
      border-radius: 10px;
      font-size: 15px;
      color: #374151;
    }

    .row-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    /* ── Info boxes ── */
    .info-box {
      padding: 14px;
      background: #f0fdf4;
      border-radius: 10px;
      font-size: 14px;
      color: #065f46;
      margin-bottom: 20px;
      line-height: 1.5;
    }
    .error-box   { background: #fef2f2; color: #991b1b; }
    .success-box { background: #f0fdf4; color: #065f46; font-weight: 500; font-size: 15px; }

    /* ── Error message inline ── */
    .error-msg {
      background: #fef2f2;
      border: 1px solid #fca5a5;
      color: #dc2626;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 13px;
      margin-bottom: 16px;
    }

    /* ── Customer greeting ── */
    .customer-greeting {
      font-size: 18px;
      color: #111827;
      margin-bottom: 12px;
    }

    /* ── Saved addresses list ── */
    .addr-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 16px;
    }
    .addr-item {
      padding: 14px;
      border: 1.5px solid #d1d5db;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .addr-item:hover { border-color: #059669; background: #f0fdf4; }
    .addr-label { font-size: 12px; font-weight: 700; color: #374151; margin-bottom: 3px; }
    .addr-text  { font-size: 14px; color: #111827; }
    .addr-sub   { font-size: 12px; color: #6b7280; margin-top: 3px; }

    /* ── Buttons ── */
    .btn-primary {
      width: 100%;
      padding: 13px;
      background: linear-gradient(135deg, #059669, #047857);
      color: white;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
      margin-bottom: 10px;
    }
    .btn-primary:hover:not(:disabled) { opacity: 0.9; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      width: 100%;
      padding: 11px;
      background: white;
      color: #059669;
      border: 1.5px solid #059669;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      margin-bottom: 10px;
    }
    .btn-secondary:hover { background: #f0fdf4; }

    .btn-ghost {
      width: 100%;
      padding: 10px;
      background: transparent;
      color: #6b7280;
      border: none;
      border-radius: 10px;
      font-size: 13px;
      cursor: pointer;
    }
    .btn-ghost:hover { color: #374151; }

    /* ── Context badge ── */
    .context-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
      background: #d1fae5;
      color: #065f46;
      margin-bottom: 18px;
    }
    .context-badge--saved    { background: #dbeafe; color: #1e3a8a; }
    .context-badge--new-addr { background: #fef3c7; color: #92400e; }

    /* ── Location status indicator ── */
    .loc-status {
      padding: 12px 14px;
      border-radius: 10px;
      font-size: 14px;
      background: #fef3c7;
      color: #92400e;
      margin-bottom: 14px;
      line-height: 1.4;
      transition: background 0.2s, color 0.2s;
    }
    .loc-status.loc-confirmed {
      background: #d1fae5;
      color: #065f46;
    }

    /* ── Picker map container ── */
    .picker-map {
      width: 100%;
      height: 300px;
      border-radius: 12px;
      border: 1.5px solid #d1d5db;
      margin-bottom: 16px;
      background: #f1f5f9;
    }

    /* ── Quote ── */
    .quote-loading {
      text-align: center;
      font-size: 13px;
      color: #6b7280;
      padding: 10px 0;
      margin-bottom: 12px;
    }
    .quote-unavailable {
      padding: 10px 14px;
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 14px;
    }

    /* ── Desglose de cotización ── */
    .quote-breakdown {
      background: #f0fdf4;
      border: 1.5px solid #6ee7b7;
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 14px;
    }
    .breakdown-row {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: #374151;
      padding: 4px 0;
    }
    .breakdown-discount {
      color: #059669;
    }
    .breakdown-base {
      font-weight: 600;
      font-size: 14px;
      color: #111827;
      border-top: 1px solid #a7f3d0;
      margin-top: 6px;
      padding-top: 8px;
    }
    .breakdown-total {
      display: flex;
      justify-content: space-between;
      font-size: 16px;
      font-weight: 800;
      color: #065f46;
      border-top: 2px solid #34d399;
      margin-top: 10px;
      padding-top: 10px;
    }

    /* ── Incentivo selector ── */
    .incentivo-label {
      font-size: 11px;
      font-weight: 700;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin: 12px 0 8px;
    }
    .incentivo-options {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 4px;
    }
    .inc-btn {
      flex: 1;
      min-width: 0;
      padding: 7px 4px;
      font-size: 12px;
      font-weight: 600;
      border: 1.5px solid #d1d5db;
      border-radius: 8px;
      background: white;
      color: #374151;
      cursor: pointer;
      transition: all 0.15s;
      white-space: nowrap;
    }
    .inc-btn:hover { border-color: #059669; color: #059669; }
    .inc-btn.inc-active {
      background: #059669;
      border-color: #059669;
      color: white;
    }

    /* ── Subsidio condicional — nota dentro del breakdown ── */
    .subsidy-conditional-note {
      margin-top: 10px;
      padding: 8px 10px;
      background: #fefce8;
      border: 1px solid #fde68a;
      border-radius: 8px;
      font-size: 12px;
      color: #92400e;
      line-height: 1.5;
    }

    /* ── Subsidio condicional — hint debajo del campo de compra ── */
    .subsidy-hint {
      margin-top: 6px;
      font-size: 12px;
      color: #065f46;
      line-height: 1.5;
      padding: 6px 10px;
      background: #f0fdf4;
      border-radius: 6px;
    }

    /* ── Success ── */
    .success-icon { font-size: 48px; text-align: center; margin-bottom: 20px; }
    .success-sub  { font-size: 13px; color: #6b7280; text-align: center; margin-top: 12px; line-height: 1.5; }
  `],
})
export class FormPedidoComponent implements OnInit, OnDestroy {
  @ViewChild('pickerMap') pickerMapEl?: ElementRef;

  step = signal<Step>('validating');
  error = signal('');
  allyInfo = signal<AllyInfo | null>(null);
  lookupResult = signal<LookupResult | null>(null);
  successMessage = signal('');

  token = '';
  phone = '';

  // Campos del formulario de entrega
  formName = '';
  formAddress = '';
  formCity = '';
  formBarrio = '';
  formNotes = '';

  fillContext: FillContext = 'new_customer';

  // Ubicación seleccionada en mapa
  selectedLat: number | null = null;
  selectedLng: number | null = null;
  locationConfirmed = false;

  // Cotización y desglose
  quotedPrice: number | null = null;
  subsidioAliado = 0;
  subsidyConditional = false;
  totalBase: number | null = null;
  incentivoCliente = 0;
  totalCliente: number | null = null;
  purchaseAmountDeclared: number | null = null;
  quoteMessage = '';
  quoteLoading = false;

  private mapInstance: any = null;
  private mapMarker: any = null;
  private readonly isBrowser: boolean;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private zone: NgZone,
    @Inject(PLATFORM_ID) platformId: object,
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    this.loadAlly();
  }

  ngOnDestroy() {
    if (this.mapInstance) this.mapInstance.remove();
  }

  // ─── Paso 1: validar token ─────────────────────────────────────────────────

  loadAlly() {
    this.step.set('validating');
    this.error.set('');
    this.lookupResult.set(null);
    this.successMessage.set('');
    this.api.getFormInfo(this.token).subscribe({
      next: (info) => {
        this.subsidioAliado = info.delivery_subsidy ?? 0;
        this.subsidyConditional = false;
        this.allyInfo.set({
          ally_id: info.ally_id,
          ally_name: info.ally_name,
          message: info.message,
          delivery_subsidy: info.delivery_subsidy ?? 0,
          min_purchase_for_subsidy: info.min_purchase_for_subsidy ?? null,
        });
        this.step.set('phone');
      },
      error: () => {
        this.step.set('invalid');
      },
    });
  }

  // ─── Paso 2: lookup por teléfono ──────────────────────────────────────────

  doLookup() {
    const p = this.phone.trim();
    if (!p) { this.error.set('Ingresa tu número de teléfono.'); return; }
    this.error.set('');
    this.lookupResult.set(null);
    this.fillContext = 'new_customer';
    this.step.set('lookup');

    this.api.lookupPhone(this.token, p).subscribe({
      next: (res: LookupResult) => {
        this.lookupResult.set(res);
        if (res.exists) {
          this.formName = res.customer_name ?? '';
          this.step.set('existing');
        } else {
          this.fillContext = 'new_customer';
          this.formName = '';
          this.clearAddressFields();
          this.step.set('fill');
        }
      },
      error: () => {
        this.error.set('No se pudo verificar el teléfono. Intenta de nuevo.');
        this.step.set('phone');
      },
    });
  }

  // ─── Paso 3a: cliente existente elige dirección guardada ──────────────────

  selectSavedAddress(addr: SavedAddress) {
    this.fillContext = 'saved_address';
    this.formAddress = addr.address_text;
    this.formCity    = addr.city ?? '';
    this.formBarrio  = addr.barrio ?? '';
    this.formNotes   = '';
    this.step.set('fill');
  }

  // ─── Paso 3b: cliente existente quiere nueva dirección ────────────────────

  useNewAddress() {
    this.fillContext = 'new_address';
    this.clearAddressFields();
    this.step.set('fill');
  }

  clearAddressFields() {
    this.formAddress = '';
    this.formCity    = '';
    this.formBarrio  = '';
    this.formNotes   = '';
    this.selectedLat = null;
    this.selectedLng = null;
    this.locationConfirmed = false;
    this.quotedPrice = null;
    this.subsidyConditional = false;
    this.totalBase = null;
    this.incentivoCliente = 0;
    this.totalCliente = null;
    this.quoteMessage = '';
    this.quoteLoading = false;
    this.purchaseAmountDeclared = null;
  }

  // ─── Invalidar ubicación si el usuario cambia la dirección escrita ─────────

  onAddressChange() {
    if (this.locationConfirmed) {
      this.locationConfirmed = false;
      this.selectedLat = null;
      this.selectedLng = null;
      this.quotedPrice = null;
      this.totalBase = null;
      this.incentivoCliente = 0;
      this.totalCliente = null;
      this.quoteMessage = '';
      this.quoteLoading = false;
    }
  }

  // ─── Cotización ───────────────────────────────────────────────────────────

  private fetchQuote(lat: number, lng: number) {
    this.quoteLoading = true;
    this.quotedPrice = null;
    this.subsidyConditional = false;
    this.totalBase = null;
    this.incentivoCliente = 0;
    this.totalCliente = null;
    this.quoteMessage = '';
    this.api.quoteForm(this.token, lat, lng).subscribe({
      next: (res) => {
        this.zone.run(() => {
          this.quotedPrice = res.quoted_price ?? null;
          this.subsidioAliado = res.subsidio_aliado ?? 0;
          this.subsidyConditional = res.subsidy_conditional ?? false;
          this.totalBase = res.total_base ?? null;
          this.totalCliente = this.totalBase;
          this.incentivoCliente = 0;
          this.quoteMessage = res.message ?? '';
          this.quoteLoading = false;
        });
      },
      error: () => {
        this.zone.run(() => {
          this.subsidyConditional = false;
          this.quoteMessage = 'No disponible en este momento.';
          this.quoteLoading = false;
        });
      },
    });
  }

  setIncentivo(amount: number) {
    this.incentivoCliente = amount;
    this.totalCliente = this.totalBase !== null ? this.totalBase + amount : null;
  }

  formatCOP(amount: number): string {
    return '$' + amount.toLocaleString('es-CO');
  }

  // ─── Ir al paso de mapa ───────────────────────────────────────────────────

  goToMap() {
    if (!this.isBrowser) { this.doSubmit(); return; }
    this.step.set('map');
    // setTimeout garantiza que Angular procese el *ngIf antes de inicializar Leaflet
    setTimeout(() => this.initPickerMap(), 50);
  }

  private async initPickerMap(): Promise<void> {
    if (!this.pickerMapEl) return;

    // Destruir instancia anterior si existe (ej. usuario vuelve y avanza al mapa)
    if (this.mapInstance) {
      this.mapInstance.remove();
      this.mapInstance = null;
      this.mapMarker = null;
    }

    const L = await import('leaflet');

    const iconDefault = L.icon({
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
    });
    L.Marker.prototype.options.icon = iconDefault;

    const center: [number, number] = [4.711, -74.0721]; // Bogotá por defecto
    this.mapInstance = L.map(this.pickerMapEl.nativeElement).setView(center, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(this.mapInstance);

    // Click en el mapa: colocar/mover marker
    this.mapInstance.on('click', (e: any) => {
      this.zone.run(() => {
        const { lat, lng } = e.latlng;
        this.selectedLat = lat;
        this.selectedLng = lng;
        this.locationConfirmed = true;
        this.fetchQuote(lat, lng);

        if (this.mapMarker) {
          this.mapMarker.setLatLng([lat, lng]);
        } else {
          this.mapMarker = L.marker([lat, lng], { icon: iconDefault, draggable: true })
            .addTo(this.mapInstance);

          // Arrastrar el marker también actualiza coordenadas y recalcula cotización
          this.mapMarker.on('dragend', (ev: any) => {
            this.zone.run(() => {
              const pos = ev.target.getLatLng();
              this.selectedLat = pos.lat;
              this.selectedLng = pos.lng;
              this.fetchQuote(pos.lat, pos.lng);
            });
          });
        }
      });
    });
  }

  confirmLocation() {
    this.doSubmit();
  }

  skipMap() {
    this.selectedLat = null;
    this.selectedLng = null;
    this.locationConfirmed = false;
    this.doSubmit();
  }

  // ─── Navegación hacia atrás ───────────────────────────────────────────────

  goBack() {
    this.error.set('');
    if (this.step() === 'map') {
      this.step.set('fill');
      return;
    }
    if (this.fillContext === 'saved_address' || this.fillContext === 'new_address') {
      this.step.set('existing');
    } else {
      this.step.set('phone');
    }
  }

  // ─── Validación antes de enviar ───────────────────────────────────────────

  canSubmit(): boolean {
    if (!this.phone.trim()) return false;
    if (!this.formAddress.trim()) return false;
    const resolvedName =
      this.fillContext === 'new_customer'
        ? this.formName.trim()
        : (this.lookupResult()?.customer_name ?? '').trim();
    if (!resolvedName) return false;
    return true;
  }

  // ─── Paso 4: enviar solicitud ─────────────────────────────────────────────

  doSubmit() {
    if (!this.canSubmit()) return;
    this.error.set('');
    this.step.set('submitting');

    const resolvedName =
      this.fillContext === 'new_customer'
        ? this.formName.trim()
        : (this.lookupResult()?.customer_name ?? this.formName.trim());

    const payload: Record<string, any> = {
      customer_name:  resolvedName,
      customer_phone: this.phone.trim(),
    };
    if (this.formAddress.trim()) payload['delivery_address'] = this.formAddress.trim();
    if (this.formCity.trim())    payload['delivery_city']    = this.formCity.trim();
    if (this.formBarrio.trim())  payload['delivery_barrio']  = this.formBarrio.trim();
    if (this.formNotes.trim())   payload['notes']            = this.formNotes.trim();
    if (this.selectedLat !== null && this.selectedLng !== null) {
      payload['lat'] = this.selectedLat;
      payload['lng'] = this.selectedLng;
    }
    if (this.quotedPrice !== null) {
      payload['quoted_price'] = this.quotedPrice;
    }
    if (this.incentivoCliente > 0) {
      payload['incentivo_cliente'] = this.incentivoCliente;
    }
    if (this.purchaseAmountDeclared !== null && this.purchaseAmountDeclared >= 0) {
      payload['purchase_amount_declared'] = this.purchaseAmountDeclared;
    }

    this.api.submitForm(this.token, payload).subscribe({
      next: (res) => {
        this.successMessage.set(res.message);
        this.step.set('success');
      },
      error: () => {
        this.error.set('No se pudo enviar la solicitud. Intenta de nuevo.');
        this.step.set('fill');
      },
    });
  }
}
