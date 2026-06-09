// Secciones del panel admin. Fuente única para la sub-nav (PanelLayout + el
// mapa privado en MapView). Añadir aquí una sección la propaga a todo el panel.
export const PANEL_NAV: { s: string; t: string; href: string }[] = [
  { s: 'mapa', t: 'Mapa', href: '/panel/mapa' },
  { s: 'jugadores', t: 'Jugadores', href: '/panel/jugadores' },
  { s: 'economia', t: 'Economía', href: '/panel/economia' },
  { s: 'squads', t: 'Squads', href: '/panel/squads' },
  { s: 'overview', t: 'Overview', href: '/panel/overview' },
  { s: 'actividad', t: 'Actividad', href: '/panel/actividad' },
  { s: 'vehiculos', t: 'Vehículos', href: '/panel/vehiculos' },
  { s: 'bases', t: 'Bases', href: '/panel/bases' },
  { s: 'bancos', t: 'Bancos', href: '/panel/bancos' },
  { s: 'muertes', t: 'Muertes', href: '/panel/muertes' },
  { s: 'rankings', t: 'Rankings', href: '/panel/rankings' },
  { s: 'cultivos', t: 'Cultivos', href: '/panel/cultivos' },
  { s: 'bunkers', t: 'Búnkers', href: '/panel/bunkers' },
  { s: 'fauna', t: 'Fauna', href: '/panel/fauna' },
  { s: 'historico', t: 'Histórico', href: '/panel/historico' },
  { s: 'rcon', t: 'RCON', href: '/panel/rcon' },
];
