import { Component, inject } from '@angular/core';
import { NgFor, NgClass } from '@angular/common';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [NgFor, NgClass],
  template: `
    <div class="toast-container">
      <div
        *ngFor="let t of toast.toasts()"
        class="toast"
        [ngClass]="t.type"
        (click)="toast.remove(t.id)"
      >
        <span class="material-icons icon">
          {{ t.type === 'success' ? 'check_circle' : t.type === 'error' ? 'error' : 'info' }}
        </span>
        <span class="msg">{{ t.message }}</span>
        <span class="material-icons close">close</span>
      </div>
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      bottom: 28px;
      right: 28px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    }
    .toast {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 18px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 500;
      min-width: 280px;
      max-width: 420px;
      box-shadow: 0 8px 24px rgba(0,0,0,.15);
      cursor: pointer;
      pointer-events: all;
      animation: slideIn .25s ease;
    }
    @keyframes slideIn {
      from { transform: translateX(60px); opacity: 0; }
      to   { transform: translateX(0);    opacity: 1; }
    }
    .success { background: #f0fdf4; border: 1px solid #86efac; color: #166534; }
    .error   { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
    .info    { background: #eff6ff; border: 1px solid #93c5fd; color: #1e40af; }
    .icon    { font-size: 20px; flex-shrink: 0; }
    .msg     { flex: 1; line-height: 1.4; }
    .close   { font-size: 16px; opacity: .5; flex-shrink: 0; }
  `]
})
export class ToastComponent {
  toast = inject(ToastService);
}
