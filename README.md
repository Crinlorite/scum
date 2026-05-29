# scumwiki.crintech.pro

Wiki y fuente de información de **SCUM**, sin anuncios, sin tracking, mantenida por la comunidad.

- Idioma por defecto: **español** (sin prefijo de URL); secundario **inglés** (`/en/...`).
- **10 idiomas** oficiales del juego: es, en, de, ru, zh, fr, pt, zh-tw, th, pl.
- Stack: **Astro 5** + MDX + content collections. JS de cliente mínimo (solo el buscador de ítems).
- Repo: `github.com/Crinlorite/scum` · Despliegue: estático en **Coolify** (nginx), dominio `scumwiki.crintech.pro`.

> Sitio fan no oficial. SCUM® es marca registrada de Gamepipe Studios / Croteam. Este proyecto no está afiliado, patrocinado ni respaldado por ellos.

## Contenido

Dos tipos de contenido:

1. **Wiki editorial** — artículos MDX en `src/content/wiki/<lang>/<category>/<slug>.mdx`
   (categorías: `guides`, `mechanics`, `maps`, `items`, `bases`, `server`).
2. **Catálogo de ítems** — ~1983 ítems del juego con su **nombre y descripción oficiales**
   en los 10 idiomas, extraídos de la propia localización del juego (no traducciones literales).
   Páginas en `/[lang]/items` (índice con buscador + categorías) y `/[lang]/items/<slug>`
   (ficha por ítem). Datos en `src/data/items.json`, consumidos vía `src/data/items.ts`.

## Desarrollo

Requiere Node 18.17+ / 20.3+ / 22+.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # astro check + astro build (a dist/) — genera ~20k páginas
npm run preview  # sirve dist/ localmente
```

## Estructura

```
src/
  i18n/            # languages.ts, ui.ts, utils.ts (t/localizedPath), wiki.ts
  content/
    config.ts      # schema Zod
    wiki/<lang>/<category>/<slug>.mdx
  data/
    items.json     # catálogo de ítems (generado, ver tools/locres-import)
    items.ts       # tipos + helpers (ITEMS, itemName, itemsByCategory…)
    server.ts      # info del servidor de comunidad
  components/      # Nav, Footer, Hero, CategoryGrid, ItemsIndexPage, ItemPage…
  layouts/         # BaseLayout
  pages/
    index.astro                  /  [lang]/index.astro          # landings
    wiki/  /  [lang]/wiki/                                       # wiki
    items/  /  [lang]/items/                                     # catálogo de ítems
    404.astro
  styles/global.css
tools/
  locres-import/   # extracción de nombres oficiales de ítems (ver su README)
```

## Catálogo de ítems (regenerar)

Los nombres oficiales salen de la localización del juego (`Game.po` por idioma).
Pipeline reproducible en `tools/locres-import/` (detalles en su `README.md`):

```bash
# con la localización del juego extraída en /tmp/scum-locres
cd tools/locres-import
python3 extract_items.py            # → out/items.json
cp out/items.json ../../src/data/items.json
```

## Añadir un artículo

1. Crea `src/content/wiki/<lang>/<category>/<slug>.mdx`.
2. Frontmatter mínimo:

```mdx
---
title: Título del artículo
description: Resumen para SEO y para la card del listado.
updated: 2026-05-29
---

Contenido MDX...
```

Categorías válidas: `guides`, `mechanics`, `maps`, `items`, `bases`, `server`. Añadir una
nueva implica tocar `src/i18n/wiki.ts`, `src/content/config.ts` y `src/i18n/ui.ts`
(`cat.<nueva>.title` y `.desc`).

## Añadir un idioma

1. Añade el código en `src/i18n/languages.ts` (de ahí se derivan los locales de `astro.config.mjs`).
2. Añade el diccionario en `src/i18n/ui.ts` (los que falten caen a EN → ES).
3. Crea `src/content/wiki/<lang>/...` con los MDX traducidos.

No hace falta tocar páginas: los `getStaticPaths` los recogen automáticamente. El catálogo de
ítems ya cubre los 10 idiomas vía `items.json`.

## Despliegue (Coolify + Cloudflare)

Coolify, build pack **Static**, imagen **nginx:alpine**:

| Campo | Valor |
| --- | --- |
| Build command | `npm ci && npm run build` |
| Output / publish dir | `dist` |
| Puerto expuesto | `80` |
| Dominio | `scumwiki.crintech.pro` |
| HTTPS | Let's Encrypt automático |

- **DNS**: `scumwiki.crintech.pro` → IP del VPS. Mantén el registro en **Cloudflare DNS-only
  (nube gris)** hasta que Coolify emita el certificado Let's Encrypt; después puedes pasar a
  **proxied** (nube naranja) con SSL/TLS *Full (strict)* para tener CDN/edge.
- **Por qué VPS y no Cloudflare Pages**: el sitio genera ~20.000 ficheros estáticos
  (1983 ítems × 10 idiomas + wiki), por encima del límite de 20.000 archivos/deploy de Pages.
  En nginx no hay ese límite.

Headers recomendados (Coolify → "Custom Nginx Configuration"):

```
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "interest-cohort=()" always;
```

## Roadmap corto

- [x] Sitemap automático (`@astrojs/sitemap`).
- [x] Catálogo de ítems multi-idioma con nombres oficiales.
- [ ] Iconos/imágenes de ítems.
- [ ] Buscador global del sitio (Pagefind) — ahora solo hay buscador dentro de `/items`.
- [ ] Ping live del servidor (A2S está roto bajo Wine; alternativa: ping HTTP propio).
- [ ] OG image generada por página (Satori).
