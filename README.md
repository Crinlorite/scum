# scumwiki.crintech.pro

Wiki y fuente de información de **SCUM**, sin anuncios, sin tracking, mantenida por la comunidad.

- Idioma por defecto: **español** (sin prefijo de URL)
- Idioma secundario: **inglés** (`/en/...`)
- Stack: Astro 5 + MDX + content collections, sin JS de cliente.
- Despliegue: estático en Coolify, dominio `scumwiki.crintech.pro`.

> Sitio fan no oficial. SCUM® es marca registrada de Gamepipe Studios / Croteam. Este proyecto no está afiliado, patrocinado ni respaldado por ellos.

## Desarrollo

Requiere Node 18.17+ o 20.3+ o 22+.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # astro check + astro build (a dist/)
npm run preview  # sirve dist/ localmente
```

## Estructura

```
src/
  i18n/
    languages.ts   # códigos de idioma
    ui.ts          # strings traducidos (UI estática)
    utils.ts       # t(), localizedPath(), alternateHref()
    wiki.ts        # helpers de la colección 'wiki'
  content/
    config.ts      # schema Zod
    wiki/
      es/<category>/<slug>.mdx
      en/<category>/<slug>.mdx
  components/      # Nav, Footer, Hero, Categories, Server, etc.
  layouts/         # BaseLayout
  pages/
    index.astro                              # ES landing
    [lang]/index.astro                       # EN+ landings
    wiki/                                    # ES wiki
    [lang]/wiki/                             # EN+ wiki
    404.astro
  styles/global.css
```

## Añadir un artículo

1. Crea `src/content/wiki/<lang>/<category>/<slug>.mdx`.
2. Frontmatter mínimo:

```mdx
---
title: Título del artículo
description: Resumen para SEO y para la card del listado.
updated: 2026-05-28
---

Contenido MDX...
```

Categorías válidas (en el schema): `guides`, `mechanics`, `maps`, `items`, `bases`, `server`. Añadir una nueva implica tocar `src/i18n/wiki.ts`, `src/content/config.ts` y `src/i18n/ui.ts` (`cat.<nueva>.title` y `.desc`).

## Añadir un idioma

1. Añade el código en `src/i18n/languages.ts` y `astro.config.mjs` (`i18n.locales`).
2. Añade el diccionario en `src/i18n/ui.ts`.
3. Crea `src/content/wiki/<lang>/<category>/...` con los MDX traducidos.

No hace falta tocar páginas — los `getStaticPaths` los recogen automáticamente.

## Despliegue en Coolify

Recurso tipo **Static**, build desde este repo:

| Campo | Valor |
| --- | --- |
| Build command | `npm install && npm run build` |
| Output directory | `dist` |
| Install command | (vacío, ya está en build) |
| Dominio | `scumwiki.crintech.pro` |
| HTTPS | activado (Let's Encrypt automático) |

Headers recomendados (en Coolify → "Custom Nginx config" o equivalent):

```
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "interest-cohort=()" always;
```

Sin CSP estricta de momento porque MDX puede inyectar HTML inline. Si quieres CSP, hay que mover el CSS inline de los componentes Astro a hojas externas y revisar `astro check`.

## Roadmap corto

- [ ] Ping live del server (cuando A2S deje de estar roto bajo Wine o añadir ping HTTP propio).
- [ ] Sitemap automático (`@astrojs/sitemap`).
- [ ] OG image generada por página (Astro built-in o Satori).
- [ ] Buscador local (Pagefind, sin backend).
- [ ] Más idiomas según contribuciones.
