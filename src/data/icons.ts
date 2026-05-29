// Official inventory icons available as /icons/<slug>.webp (built by
// tools/locres-import/build_icons.mjs). Only items with a real exported icon
// are listed; the rest have none (the game's icon export was partial).
import iconsData from './icons.json';

const ICON_SLUGS = new Set(iconsData as string[]);

export const hasIcon = (slug: string): boolean => ICON_SLUGS.has(slug);
export const iconUrl = (slug: string): string | null => (ICON_SLUGS.has(slug) ? `/icons/${slug}.webp` : null);
