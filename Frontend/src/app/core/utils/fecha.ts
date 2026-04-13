const MESES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];

/**
 * Formatea un timestamp ISO a "12 abr 2026, 3:45 pm"
 */
export function fmtFecha(dt: string | null | undefined): string {
  if (!dt) return '—';
  const d = new Date(dt);
  if (isNaN(d.getTime())) return '—';
  const dia  = d.getDate();
  const mes  = MESES[d.getMonth()];
  const anio = d.getFullYear();
  let h      = d.getHours();
  const min  = d.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${dia} ${mes} ${anio}, ${h}:${min} ${ampm}`;
}

/**
 * Retorna texto relativo: "hace X seg", "hace X min", "hace X h"
 */
export function fmtRelativo(desde: Date): string {
  const seg = Math.floor((Date.now() - desde.getTime()) / 1000);
  if (seg < 60)  return `hace ${seg} seg`;
  if (seg < 3600) return `hace ${Math.floor(seg / 60)} min`;
  return `hace ${Math.floor(seg / 3600)} h`;
}
