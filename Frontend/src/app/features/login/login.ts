import { Component, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, NgIf],
  template: `
    <div class="login-bg">
      <div class="login-card">
        <div class="brand">
          <span class="material-symbols-outlined brand-icon">local_shipping</span>
          <h1>Domiquerendona</h1>
          <p>Panel Administrativo</p>
        </div>

        <form (ngSubmit)="login()" #f="ngForm">
          <div class="field">
            <label>Usuario</label>
            <input
              type="text"
              [(ngModel)]="username"
              name="username"
              placeholder="admin"
              autocomplete="username"
              required
              [disabled]="cargando()"
            />
          </div>

          <div class="field">
            <label>Contraseña</label>
            <input
              type="password"
              [(ngModel)]="password"
              name="password"
              placeholder="••••••••"
              autocomplete="current-password"
              required
              [disabled]="cargando()"
            />
          </div>

          <div class="error-msg" *ngIf="error()">{{ error() }}</div>

          <button type="submit" [disabled]="cargando()">
            {{ cargando() ? 'Ingresando...' : 'Ingresar' }}
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-bg {
      min-height: 100vh;
      background: linear-gradient(135deg, #3730a3 0%, #4338ca 50%, #6366f1 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }

    .login-card {
      background: white;
      border-radius: 20px;
      padding: 48px 40px;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.25);
    }

    .brand {
      text-align: center;
      margin-bottom: 36px;
    }

    .brand-icon {
      font-size: 48px;
      color: #4338ca;
    }

    .brand h1 {
      font-size: 22px;
      font-weight: 800;
      color: #1e1b4b;
      margin: 8px 0 4px;
    }

    .brand p {
      font-size: 13px;
      color: #6b7280;
      margin: 0;
    }

    .field {
      margin-bottom: 20px;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #374151;
      margin-bottom: 6px;
    }

    input {
      width: 100%;
      padding: 12px 14px;
      border: 1.5px solid #d1d5db;
      border-radius: 10px;
      font-size: 15px;
      color: #111827;
      outline: none;
      box-sizing: border-box;
      transition: border-color 0.2s;
    }

    input:focus {
      border-color: #4338ca;
    }

    input:disabled {
      background: #f9fafb;
      color: #9ca3af;
    }

    .error-msg {
      background: #fef2f2;
      border: 1px solid #fca5a5;
      color: #dc2626;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 13px;
      margin-bottom: 16px;
    }

    button[type="submit"] {
      width: 100%;
      padding: 13px;
      background: linear-gradient(135deg, #4338ca, #6366f1);
      color: white;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button[type="submit"]:hover:not(:disabled) {
      opacity: 0.9;
    }

    button[type="submit"]:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `]
})
export class LoginComponent {
  username = '';
  password = '';
  cargando = signal(false);
  error = signal('');

  constructor(private http: HttpClient, private router: Router) {}

  login() {
    if (!this.username || !this.password) return;
    this.cargando.set(true);
    this.error.set('');

    this.http.post<{ token: string; username: string }>(
      'http://localhost:8000/auth/login',
      { username: this.username, password: this.password }
    ).subscribe({
      next: (res) => {
        localStorage.setItem('admin_token', res.token);
        localStorage.setItem('admin_username', res.username);
        this.router.navigate(['/superadmin']);
      },
      error: (e) => {
        this.error.set(e.error?.detail ?? 'Error al conectar con el servidor');
        this.cargando.set(false);
      }
    });
  }
}
