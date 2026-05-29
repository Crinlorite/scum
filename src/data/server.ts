// Static info about the community server. No live ping yet — A2S query
// is broken under Wine, so we don't even try. Update by hand for now.
export const SERVER_INFO = {
  name: 'Crintech Community SCUM',
  // Set to null to render "Sin datos" / "No data"
  status: 'online' as 'online' | 'offline' | null,
  rulesUrl: 'https://github.com/Crinlorite/scum-crintech',
} as const;
