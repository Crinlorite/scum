// Secciones del panel admin. Fuente única para la sub-nav (PanelLayout + el
// mapa privado en MapView). Añadir aquí una sección la propaga a todo el panel.
export const PANEL_NAV: { s: string; t: string; href: string }[] = [
  { s: 'mapa', t: 'Mapa', href: '/panel/mapa' },
  { s: 'jugadores', t: 'Jugadores', href: '/panel/jugadores' },
  { s: 'economia', t: 'Economía', href: '/panel/economia' },
  { s: 'squads', t: 'Squads', href: '/panel/squads' },
  { s: 'overview', t: 'Overview', href: '/panel/overview' },
  { s: 'actividad', t: 'Actividad', href: '/panel/actividad' },
  { s: 'rcon', t: 'RCON', href: '/panel/rcon' },
];
