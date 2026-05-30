// Static info about the community server. No live ping yet; update by hand.
export const SERVER_INFO = {
  name: 'Familia Ruiz',
  address: 'server.scumcodex.com',
  // Set to null to render "Sin datos" / "No data"
  status: 'online' as 'online' | 'offline' | null,
  rulesUrl: 'https://github.com/Crinlorite/scum',
} as const;
