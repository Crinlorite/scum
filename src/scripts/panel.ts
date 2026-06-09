// Helpers compartidos del panel admin. Los importan PanelLayout (gate) y cada
// página de dashboard. TODAS las horas en Europe/Madrid (España, CEST/UTC+2 con DST).
export const TZ = 'Europe/Madrid';

export const esc = (s: unknown): string =>
  (s == null ? '' : String(s)).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string));

export const nf = new Intl.NumberFormat('es-ES');

const D = (d: unknown) => new Date(d as string | number | Date);

export const fmtTime = (d: unknown): string => {
  const x = D(d); return isNaN(+x) ? '—' : x.toLocaleTimeString('es-ES', { timeZone: TZ, hour: '2-digit', minute: '2-digit' });
};
export const fmtDateTime = (d: unknown): string => {
  const x = D(d); return isNaN(+x) ? '—' : x.toLocaleString('es-ES', { timeZone: TZ, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
};
export const nowTime = (): string =>
  new Date().toLocaleTimeString('es-ES', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit' });

export const fmtRel = (iso: unknown): string => {
  const x = D(iso); if (isNaN(+x)) return '—';
  const s = (Date.now() - x.getTime()) / 1000;
  if (s < 60) return 'hace segundos';
  if (s < 3600) return 'hace ' + Math.floor(s / 60) + ' min';
  if (s < 86400) return 'hace ' + Math.floor(s / 3600) + ' h';
  return 'hace ' + Math.floor(s / 86400) + ' d';
};

// Identidad del usuario (una sola llamada, compartida por gate + requireAdmin).
export const me: Promise<{ discord_id: string; username: string; is_admin: boolean } | null> =
  fetch('/panel/api/auth/me').then((r) => (r.ok ? r.json() : null)).catch(() => null);

// Gate compartido: si no es admin, oculta #pnl-content y muestra #pnl-gate.
export function gate(): void {
  me.then((m) => {
    if (!m || !m.is_admin) {
      const g = document.getElementById('pnl-gate'); const c = document.getElementById('pnl-content');
      if (g) g.hidden = false; if (c) c.hidden = true;
    }
  });
}

// Ejecuta load() solo si es admin (la página no pide datos si está gateada).
export function requireAdmin(load: () => void): void {
  me.then((m) => { if (m && m.is_admin) load(); });
}
