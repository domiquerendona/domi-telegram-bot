import { Component, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgIf } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { environment } from '../../../environments/environment';

type Vista = 'login' | 'forgot';

@Component({
selector: 'app-login',
standalone: true,
imports: [FormsModule, NgIf],

template: `

<div class="login-bg">

<div class="login-card">

<div class="brand">
  <div class="icon-box">
    <span class="material-symbols-outlined">local_shipping</span>
  </div>

  <h1>Domiquerendona</h1>
  <p>Panel Administrativo</p>
</div>

<!-- ===== VISTA LOGIN ===== -->
<ng-container *ngIf="vista() === 'login'">
<form (ngSubmit)="login()" #f="ngForm">

  <div class="field">
    <label>Usuario</label>
    <input
      type="text"
      [(ngModel)]="username"
      name="username"
      placeholder="Ingresa tu usuario"
      autocomplete="username"
      required
      [disabled]="cargando()"
    />
  </div>

  <div class="field">
    <label>Contraseña</label>
    <div class="password-wrapper">
      <input
        [type]="mostrarPassword() ? 'text' : 'password'"
        [(ngModel)]="password"
        name="password"
        placeholder="Ingresa tu contraseña"
        autocomplete="current-password"
        required
        [disabled]="cargando()"
      />
      <button type="button" class="toggle-password" (click)="mostrarPassword.set(!mostrarPassword())">
        <span class="material-symbols-outlined">{{ mostrarPassword() ? 'visibility_off' : 'visibility' }}</span>
      </button>
    </div>
  </div>

  <div class="error-msg" *ngIf="error()">
    {{ error() }}
  </div>

  <button type="submit" [disabled]="cargando()">
    {{ cargando() ? 'Ingresando...' : 'Ingresar' }}
  </button>

  <a class="forgot" (click)="irForgot()">¿Olvidaste tu contraseña?</a>

</form>
</ng-container>

<!-- ===== VISTA RECUPERAR CONTRASEÑA ===== -->
<ng-container *ngIf="vista() === 'forgot'">
<form (ngSubmit)="solicitarReset()">

  <p class="forgot-hint">
    Ingresa tu usuario y te enviaremos una contraseña temporal a tu cuenta de Telegram.
  </p>

  <div class="field">
    <label>Usuario</label>
    <input
      type="text"
      [(ngModel)]="forgotUsername"
      name="forgotUsername"
      placeholder="Ingresa tu usuario"
      autocomplete="username"
      required
      [disabled]="forgotCargando()"
    />
  </div>

  <div class="error-msg" *ngIf="forgotError()">{{ forgotError() }}</div>

  <div class="success-msg" *ngIf="forgotExito()">{{ forgotExito() }}</div>

  <button type="submit" [disabled]="forgotCargando() || !!forgotExito()">
    {{ forgotCargando() ? 'Enviando...' : 'Enviar contraseña temporal' }}
  </button>

  <a class="forgot" (click)="irLogin()">← Volver al inicio de sesión</a>

</form>
</ng-container>

<div class="version">
  v1.0.0 – Sistema Seguro
</div>

</div>
</div>
`,

styles: [`

.login-bg{
min-height:100vh;
display:flex;
align-items:center;
justify-content:center;
background:linear-gradient(110deg,#4338ca,#9C38CA);
padding:20px;
font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto;
}

.login-card{
width:100%;
max-width:420px;
background:white;
border-radius:22px;
padding:50px 40px;
box-shadow:0 30px 70px rgba(0,0,0,.25);
text-align:center;
}

.brand{
margin-bottom:35px;
}

.icon-box{
width:60px;
height:60px;
border-radius:14px;
background:linear-gradient(140deg,#4338ca,#9C38CA);
display:flex;
align-items:center;
justify-content:center;
margin:0 auto 15px auto;
}

.icon-box span{
color:white;
font-size:30px;
}

.brand h1{
font-size:24px;
font-weight:800;
color:#1f2937;
margin:5px 0;
}

.brand p{
font-size:14px;
color:#6b7280;
}

.field{
text-align:left;
margin-bottom:18px;
}

label{
display:block;
font-size:13px;
font-weight:600;
color:#374151;
margin-bottom:6px;
}

input{
width:100%;
padding:13px 14px;
border-radius:10px;
border:1.5px solid #d1d5db;
font-size:14px;
outline:none;
transition:all .2s;
}

input:focus{
border-color:#4338ca;
box-shadow:0 0 0 2px rgba(67,56,202,0.15);
}

button{ 
width:100%;
padding:14px;
border:none;
border-radius:10px;
background:linear-gradient(140deg,#4338ca,#9C38CA);
color:white;
font-size:15px;
font-weight:700;
cursor:pointer;
margin-top:10px;
transition:all .2s;
}

button:hover:not(:disabled){
transform:translateY(-1px);
box-shadow:0 8px 20px rgba(67,56,202,.35);
}

button:disabled{
opacity:.6;
cursor:not-allowed;
}

.error-msg{
background:#fef2f2;
border:1px solid #fca5a5;
color:#dc2626;
border-radius:8px;
padding:10px;
font-size:13px;
margin-bottom:10px;
}

.password-wrapper{
position:relative;
display:flex;
align-items:center;
}

.password-wrapper input{
padding-right:44px;
}

.toggle-password{
position:absolute;
right:10px;
width:auto;
padding:4px;
margin-top:0;
background:none;
border:none;
color:#6b7280;
cursor:pointer;
display:flex;
align-items:center;
}

.toggle-password:hover:not(:disabled){
transform:none;
box-shadow:none;
color:#4338ca;
}

.toggle-password span{
font-size:20px;
}

.forgot{
display:block;
margin-top:14px;
font-size:13px;
color:#4338ca;
cursor:pointer;
user-select:none;
}

.forgot-hint{
font-size:13px;
color:#6b7280;
text-align:left;
margin-bottom:18px;
line-height:1.5;
}

.success-msg{
background:#f0fdf4;
border:1px solid #86efac;
color:#166534;
border-radius:8px;
padding:10px;
font-size:13px;
margin-bottom:10px;
}

.version{
margin-top:25px;
font-size:12px;
color:#9ca3af;
}

`]

})
export class LoginComponent {

// ── Login ────────────────────────────────────────────────────────────────
username = '';
password = '';
cargando = signal(false);
error = signal('');
mostrarPassword = signal(false);

// ── Recuperar contraseña ─────────────────────────────────────────────────
vista = signal<Vista>('login');
forgotUsername = '';
forgotCargando = signal(false);
forgotError = signal('');
forgotExito = signal('');

constructor(
private http: HttpClient,
private router: Router,
private authService: AuthService,
) {}

irForgot() {
  this.vista.set('forgot');
  this.forgotUsername = this.username;
  this.forgotError.set('');
  this.forgotExito.set('');
}

irLogin() {
  this.vista.set('login');
  this.error.set('');
}

login() {
if (!this.username && !this.password) {
  this.error.set('El usuario y la contraseña son obligatorios.');
  return;
}
if (!this.username) {
  this.error.set('El usuario es obligatorio.');
  return;
}
if (!this.password) {
  this.error.set('La contraseña es obligatoria.');
  return;
}

this.cargando.set(true);
this.error.set('');

this.http.post<{ token: string; username: string; role: string }>(
`${environment.apiBaseUrl}/auth/login`,
{ username: this.username, password: this.password }
).subscribe({
next: (res) => {

if (typeof localStorage !== 'undefined') {
localStorage.setItem('admin_token', res.token);
localStorage.setItem('admin_username', res.username);
}

this.authService.setUser(res.role);
this.router.navigate([this.authService.homeRoute()]);
},

error: (e) => {
this.error.set(e.error?.detail ?? 'Error al conectar con el servidor');
this.cargando.set(false);
}
});
}

solicitarReset() {
  const u = this.forgotUsername.trim();
  if (!u) {
    this.forgotError.set('Ingresa tu nombre de usuario.');
    return;
  }
  this.forgotCargando.set(true);
  this.forgotError.set('');
  this.forgotExito.set('');

  this.http.post<{ message: string }>(
    `${environment.apiBaseUrl}/auth/forgot-password`,
    { username: u }
  ).subscribe({
    next: (res) => {
      this.forgotExito.set(res.message);
      this.forgotCargando.set(false);
    },
    error: (e) => {
      this.forgotError.set(e.error?.detail ?? 'Error al conectar con el servidor.');
      this.forgotCargando.set(false);
    }
  });
}
}