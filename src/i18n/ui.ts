import type { LangCode } from './languages';

type Dict = Record<string, string>;

// Partial on purpose: not every supported lang ships with a dictionary.
// `t()` walks lang → en → es → key, so untranslated keys still render.
export const UI: Partial<Record<LangCode, Dict>> = {
  es: {
    'site.name': 'SCUM · Crintech',
    'site.tagline': 'Wiki y guía de SCUM, sin anuncios.',
    'site.description':
      'Fuente de información sobre SCUM: mecánicas, mapas, loot, bases y guías. Sin anuncios, sin tracking, sostenible por la comunidad.',

    'nav.home': 'Inicio',
    'nav.wiki': 'Wiki',
    'nav.items': 'Ítems',
    'nav.server': 'Servidor',
    'nav.contribute': 'Contribuir',
    'nav.skipToContent': 'Saltar al contenido',

    'hero.eyebrow': 'Comunidad · Sin anuncios · Open Source',
    'hero.title': 'Sobrevivir es más fácil con información clara.',
    'hero.subtitle':
      'Mecánicas, mapas, loot y guías de SCUM en español. Sin pop-ups, sin trackers, sin redirecciones a wikis con 14 banners.',
    'hero.ctaPrimary': 'Abrir la wiki',
    'hero.ctaSecondary': 'Ver el servidor',

    'categories.title': 'Explora la wiki',
    'categories.subtitle': 'Empezamos con lo esencial y vamos creciendo con la comunidad.',
    'cat.guides.title': 'Guías',
    'cat.guides.desc': 'Cómo empezar, supervivencia y consejos para no morir el primer día.',
    'cat.mechanics.title': 'Mecánicas',
    'cat.mechanics.desc': 'Hambre, sed, metabolismo, fama, daño, stamina y todo lo que la UI no explica.',
    'cat.maps.title': 'Mapas',
    'cat.maps.desc': 'Puntos de interés, zonas militares, búnkers y rutas seguras.',
    'cat.items.title': 'Loot e ítems',
    'cat.items.desc': 'Armas, munición, comida, medicina y crafteo.',
    'cat.bases.title': 'Bases y raideo',
    'cat.bases.desc': 'Construcción, defensa y cómo no perder horas de trabajo en una noche.',
    'cat.server.title': 'Servidores',
    'cat.server.desc': 'Cómo conectarte al nuestro y al resto. Reglas y configuración.',

    'server.title': 'Nuestro servidor SCUM',
    'server.subtitle': 'Servidor comunitario alojado por Crintech. Estable, sin admins tóxicos.',
    'server.name': 'Nombre del servidor',
    'server.status': 'Estado',
    'server.statusOnline': 'En línea',
    'server.statusOffline': 'Caído',
    'server.statusUnknown': 'Sin datos',
    'server.connect': 'Cómo conectar',
    'server.howToJoin':
      'Abre SCUM → Multiplayer → Community → busca por nombre. Si no aparece, conexión directa por IP en la pestaña "Direct".',
    'server.rules': 'Reglas del servidor',
    'server.note':
      'El query A2S está roto bajo Wine; la lista pública puede tardar en refrescar, pero el server admite conexiones.',

    'contribute.title': '¿Por qué este sitio existe?',
    'contribute.body':
      'Las wikis grandes están saturadas de anuncios, vídeos autoplay y popups de cookies. Esta no. Sin tracking, sin afiliados, sin pop-ups. Si la mantenemos entre varias personas, dura para siempre.',
    'contribute.howTitle': 'Cómo ayudar',
    'contribute.howBody':
      'El sitio es open source. Si juegas SCUM y sabes algo que no está documentado, abre un PR o un issue.',
    'contribute.cta': 'Repositorio en GitHub',

    'footer.disclaimer':
      'Sitio fan no oficial. SCUM® es marca registrada de Gamepipe Studios / Croteam. Este proyecto no está afiliado, patrocinado ni respaldado por ellos.',
    'footer.builtBy': 'Hecho por',
    'footer.opensource': 'Código abierto',

    'wiki.title': 'Wiki',
    'wiki.intro': 'Documentación de SCUM mantenida por la comunidad.',
    'wiki.empty': 'Aún no hay artículos en esta categoría. ¿Quieres ser la primera persona en escribir uno?',
    'wiki.articleCountOne': '{n} artículo',
    'wiki.articleCountOther': '{n} artículos',
    'wiki.backToCategory': '← Volver a la categoría',
    'wiki.backToWiki': '← Volver a la wiki',
    'wiki.contributeLink': 'Editar esta página en GitHub',

    'items.title': 'Ítems',
    'items.intro': 'Catálogo de objetos de SCUM con sus nombres oficiales del juego, en tu idioma.',
    'items.search': 'Buscar ítem…',
    'items.searchNoResults': 'Ningún ítem coincide con tu búsqueda.',
    'items.countOne': '{n} ítem',
    'items.countOther': '{n} ítems',
    'items.backToItems': '← Volver a ítems',
    'items.description': 'Descripción',
    'items.noDescription': 'Este objeto no tiene descripción en el juego.',
    'items.otherLanguages': 'En otros idiomas',
    'items.category': 'Categoría',
    'items.officialName': 'Nombre oficial del juego',

    'beta.badge': 'Beta',
    'beta.notice': 'Traducción en Beta: parte del contenido puede estar incompleto o aparecer en inglés.',
    'beta.readIn': 'Disponible en',

    'common.readMore': 'Leer más',
    'common.lastUpdated': 'Última actualización',
    'common.404title': 'Página no encontrada',
    'common.404body': 'La página que buscas no existe o se ha movido.',
    'common.404cta': 'Volver al inicio',
  },

  en: {
    'site.name': 'SCUM · Crintech',
    'site.tagline': 'SCUM wiki and guide, ad-free.',
    'site.description':
      'Community-run SCUM info source: mechanics, maps, loot, bases and guides. No ads, no tracking, sustainable.',

    'nav.home': 'Home',
    'nav.wiki': 'Wiki',
    'nav.items': 'Items',
    'nav.server': 'Server',
    'nav.contribute': 'Contribute',
    'nav.skipToContent': 'Skip to content',

    'hero.eyebrow': 'Community · Ad-free · Open Source',
    'hero.title': 'Surviving is easier with clear information.',
    'hero.subtitle':
      'SCUM mechanics, maps, loot and guides. No pop-ups, no trackers, no redirects to wikis with 14 banners.',
    'hero.ctaPrimary': 'Open the wiki',
    'hero.ctaSecondary': 'See the server',

    'categories.title': 'Explore the wiki',
    'categories.subtitle': 'Starting with the essentials and growing with the community.',
    'cat.guides.title': 'Guides',
    'cat.guides.desc': 'How to start, survival basics and tips to not die on day one.',
    'cat.mechanics.title': 'Mechanics',
    'cat.mechanics.desc': 'Hunger, thirst, metabolism, fame, damage, stamina and everything the UI hides.',
    'cat.maps.title': 'Maps',
    'cat.maps.desc': 'Points of interest, military zones, bunkers and safe routes.',
    'cat.items.title': 'Loot & items',
    'cat.items.desc': 'Weapons, ammo, food, medicine and crafting.',
    'cat.bases.title': 'Bases & raiding',
    'cat.bases.desc': 'Building, defense and how not to lose hours of work in one night.',
    'cat.server.title': 'Servers',
    'cat.server.desc': 'How to join ours and others. Rules and configuration.',

    'server.title': 'Our SCUM server',
    'server.subtitle': 'Community server hosted by Crintech. Stable, no toxic admins.',
    'server.name': 'Server name',
    'server.status': 'Status',
    'server.statusOnline': 'Online',
    'server.statusOffline': 'Down',
    'server.statusUnknown': 'No data',
    'server.connect': 'How to connect',
    'server.howToJoin':
      'Open SCUM → Multiplayer → Community → search by name. If it does not show up, use direct IP connection in the "Direct" tab.',
    'server.rules': 'Server rules',
    'server.note':
      'A2S query is broken under Wine; public listing may take time to refresh, but the server accepts connections.',

    'contribute.title': 'Why does this site exist?',
    'contribute.body':
      'Big wikis are bloated with ads, autoplay videos and cookie pop-ups. This one is not. No tracking, no affiliates, no pop-ups. Maintained by a few people, it can last forever.',
    'contribute.howTitle': 'How to help',
    'contribute.howBody':
      'The site is open source. If you play SCUM and know something undocumented, open a PR or an issue.',
    'contribute.cta': 'GitHub repository',

    'footer.disclaimer':
      'Unofficial fan site. SCUM® is a trademark of Gamepipe Studios / Croteam. This project is not affiliated with, sponsored by, or endorsed by them.',
    'footer.builtBy': 'Made by',
    'footer.opensource': 'Open source',

    'wiki.title': 'Wiki',
    'wiki.intro': 'Community-maintained SCUM documentation.',
    'wiki.empty': 'No articles in this category yet. Want to be the first to write one?',
    'wiki.articleCountOne': '{n} article',
    'wiki.articleCountOther': '{n} articles',
    'wiki.backToCategory': '← Back to category',
    'wiki.backToWiki': '← Back to wiki',
    'wiki.contributeLink': 'Edit this page on GitHub',

    'items.title': 'Items',
    'items.intro': 'SCUM item catalog with their official in-game names, in your language.',
    'items.search': 'Search item…',
    'items.searchNoResults': 'No item matches your search.',
    'items.countOne': '{n} item',
    'items.countOther': '{n} items',
    'items.backToItems': '← Back to items',
    'items.description': 'Description',
    'items.noDescription': 'This item has no in-game description.',
    'items.otherLanguages': 'In other languages',
    'items.category': 'Category',
    'items.officialName': 'Official in-game name',

    'beta.badge': 'Beta',
    'beta.notice': 'Beta translation: some content may be incomplete or shown in English.',
    'beta.readIn': 'Available in',

    'common.readMore': 'Read more',
    'common.lastUpdated': 'Last updated',
    'common.404title': 'Page not found',
    'common.404body': 'The page you are looking for does not exist or has been moved.',
    'common.404cta': 'Back to home',
  },
};

// UI keys are derived from ES (the canonical reference dict). EN must
// mirror them; new locales may ship partial dicts and fall back via t().
export type UIKey = keyof NonNullable<(typeof UI)['es']>;
