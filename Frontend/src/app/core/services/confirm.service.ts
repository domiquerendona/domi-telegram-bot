import { Injectable, signal } from '@angular/core';

export interface ConfirmRequest {
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  resolve: (value: boolean) => void;
}

@Injectable({ providedIn: 'root' })
export class ConfirmService {
  current = signal<ConfirmRequest | null>(null);

  ask(message: string, confirmLabel = 'Confirmar', cancelLabel = 'Cancelar'): Promise<boolean> {
    return new Promise(resolve => {
      this.current.set({ message, confirmLabel, cancelLabel, resolve });
    });
  }

  confirm() {
    this.current()?.resolve(true);
    this.current.set(null);
  }

  cancel() {
    this.current()?.resolve(false);
    this.current.set(null);
  }
}
