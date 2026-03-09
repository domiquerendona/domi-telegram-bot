import { Component } from '@angular/core';

@Component({
  selector: 'app-contacto',
  standalone: true,
  template: `

<div class="contacto-wrapper">

  <div class="contacto-card">

    <h1>Contáctanos</h1>
    <p class="subtitle">
      Completa el formulario y nos comunicaremos contigo lo antes posible
    </p>

    <form class="form">

      <input type="text" placeholder="Juan Pérez">

      <input type="email" placeholder="juan@ejemplo.com">

      <input type="tel" placeholder="+57 300 123 4567">

      <select>
        <option selected disabled>Selecciona una opción</option>
        <option>Soporte técnico</option>
        <option>Problema con un pedido</option>
        <option>Información comercial</option>
        <option>Registro en la plataforma</option>
        <option>Otro</option>
      </select>

      <input type="text" placeholder="Breve descripción del motivo">

      <textarea rows="5" placeholder="Cuéntanos en detalle cómo podemos ayudarte..."></textarea>

      <button type="button">Enviar Mensaje</button>

    </form>

  </div>

</div>

  `,
  styles: [`

.contacto-wrapper{
  display:flex;
  justify-content:center;
  padding:40px 20px;
}

.contacto-card{
  max-width:700px;
  width:100%;
  background:white;
  padding:40px;
  border-radius:12px;
  border:1px solid #e5e7eb;
}

h1{
  font-size:30px;
  margin-bottom:5px;
}

.subtitle{
  color:#6b7280;
  margin-bottom:30px;
}

.form{
  display:flex;
  flex-direction:column;
  gap:12px;
}

input, select, textarea{
  padding:12px;
  border-radius:6px;
  border:1px solid #d1d5db;
  font-size:14px;
}

textarea{
  resize:vertical;
}

button{
  margin-top:10px;
  background:#2563eb;
  color:white;
  border:none;
  padding:12px;
  border-radius:6px;
  cursor:pointer;
  font-size:15px;
}

button:hover{
  background:#1d4ed8;
}

  `]
})
export class ContactoComponent {}