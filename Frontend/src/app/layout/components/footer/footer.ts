import { Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  standalone: true,
  template: `
    <footer class="footer">
      <div class="left">
        © 2026 DOMIUI. Todos los derechos reservados.
      </div>
      <div class="right">
        <a href="#">Términos</a>
        <span>|</span>
        <a href="#">Privacidad</a>
        <span>|</span>
        <a href="#">Soporte</a>
      </div>
    </footer>
  `,
  styles: [`
    .footer {
      height: 60px;
      background: white;
      border-top: 1px solid #e5e7eb;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 30px;
      font-size: 13px;
      color: #6b7280;
      flex-shrink: 0;
    }

    .footer a {
      text-decoration: none;
      color: #6b7280;
      transition: color 0.2s;
    }

    .footer a:hover {
      color: #3b82f6;
    }

    .footer span {
      margin: 0 8px;
    }

    @media (max-width: 768px) {
      .footer {
        flex-direction: column;
        justify-content: center;
        gap: 5px;
        font-size: 12px;
      }
    }
  `]
})
export class FooterComponent {}