# Scum Codex (scumcodex.com)

Wiki y fuente de información de **SCUM**, sin anuncios, sin tracking, multilingüe.

- Idioma por defecto: **español** (sin prefijo de URL); secundario **inglés** (`/en/...`).
- **10 idiomas** oficiales del juego: es, en, de, ru, zh, fr, pt, zh-tw, th, pl.
- Stack: **Astro 5** + MDX + content collections. JS de cliente mínimo (buscador y mapa).
- Repo: `github.com/Crinlorite/scum` · Despliegue: estático en **Coolify** (nginx), dominio `scumcodex.com`.

## Contenido

1. **Wiki editorial** — artículos MDX en `src/content/wiki/<lang>/<category>/<slug>.mdx`.
2. **Catálogos del juego** — ítems (1983), armas, habilidades, médico, vehículos, misiones,
   recetas, crafteo, controles, caza, mapa interactivo y el **manual/códice** del juego, con
   nombres/descripciones oficiales en los 10 idiomas. Datos en `src/data/`.

## Licencias y alcance del contenido

- **Código**: MIT — ver [LICENSE](./LICENSE).
- **Artículos wiki** (`src/content/`): CC BY-SA 4.0.
- **Datos derivados** (`items.json` y demás): nombres/descripciones de **Gamepires d.o.o.**,
  incluidos bajo la Fan Content Policy de Gamepires, **no relicenciados**.
- **NO** se distribuyen `.locres`/`.po` ni assets extraídos del juego (ver `.gitignore`).

> ⚠️ Reproducir descripciones del juego de forma literal conlleva exposición de copyright que
> este proyecto no elimina; se resuelve con permiso explícito de Gamepires o reescribiendo los textos.

## Atribución

Created using intellectual property belonging to Gamepires d.o.o. under the terms of Gamepires'
Fan Content Policy. This content is not endorsed by or affiliated with Gamepires.

SCUM y el logo de Gamepires son marcas de **Gamepires d.o.o.** (publicado por **Jagex**).
Proyecto de fans no oficial: sin afiliación, patrocinio ni respaldo de Gamepires.

## Desarrollo

Requiere Node 18.17+ / 20.3+ / 22+.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # astro build → dist/
```

## Despliegue

Coolify (build pack Dockerfile, nginx) sirviendo `dist/`, puerto 80, dominio `scumcodex.com`
(cert Let's Encrypt). El panel privado `/panel/` va tras HTTP Basic Auth (Build Args
`PANEL_USER`/`PANEL_PASS`). Sin anuncios ni analítica de terceros.
