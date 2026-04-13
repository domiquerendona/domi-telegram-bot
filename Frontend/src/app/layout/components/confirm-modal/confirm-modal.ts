import { Component, inject } from '@angular/core';
import { NgIf } from '@angular/common';
import { ConfirmService } from '../../../core/services/confirm.service';

@Component({
  selector: 'app-confirm-modal',
  standalone: true,
  imports: [NgIf],
  template: `
    <div class="overlay" *ngIf="confirm.current()" (click)="confirm.cancel()">
      <div class="modal" (click)="$event.stopPropagation()">
        <span class="material-icons modal-icon">help_outline</span>
        <p class="message">{{ confirm.current()?.message }}</p>
        <div class="btns">
          <button class="btn-cancel" (click)="confirm.cancel()">
            {{ confirm.current()?.cancelLabel ?? 'Cancelar' }}
          </button>
          <button class="btn-confirm" (click)="confirm.confirm()">
            {{ confirm.current()?.confirmLabel ?? 'Confirmar' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.45);
      z-index: 3000;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal {
      background: white;
      border-radius: 16px;
      padding: 32px 28px 24px;
      width: 360px;
      max-width: calc(100vw - 32px);
      text-align: center;
      box-shadow: 0 20px 60px rgba(0,0,0,0.25);
    }

    .modal-icon {
      font-size: 40px;
      color: #4338ca;
      margin-bottom: 12px;
    }

    .message {
      font-size: 16px;
      font-weight: 600;
      color: #111827;
      margin: 0 0 24px;
      line-height: 1.5;
    }

    .btns {
      display: flex;
      gap: 12px;
      justify-content: center;
    }

    .btn-cancel {
      padding: 10px 24px;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
      background: white;
      color: #374151;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background .15s;
    }

    .btn-cancel:hover { background: #f3f4f6; }

    .btn-confirm {
      padding: 10px 24px;
      border-radius: 8px;
      border: none;
      background: #4338ca;
      color: white;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background .15s;
    }

    .btn-confirm:hover { background: #3730a3; }
  `]
})
export class ConfirmModalComponent {
  confirm = inject(ConfirmService);
}
