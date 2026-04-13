import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  toasts = signal<Toast[]>([]);
  private next = 0;

  show(message: string, type: 'success' | 'error' | 'info' = 'info', duration = 4000) {
    const id = ++this.next;
    this.toasts.update(t => [...t, { id, message, type }]);
    setTimeout(() => this.remove(id), duration);
  }

  success(message: string) { this.show(message, 'success'); }
  error(message: string)   { this.show(message, 'error'); }
  info(message: string)    { this.show(message, 'info'); }

  remove(id: number) {
    this.toasts.update(t => t.filter(x => x.id !== id));
  }
}
