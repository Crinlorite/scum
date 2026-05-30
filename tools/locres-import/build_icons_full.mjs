#!/usr/bin/env node
// Iconos de item desde el export COMPLETO de texturas (scum-textures-full.zip).
// Mapea item → GridInventoryIcon (_ES) → ruta en _icons_index.json → extrae del zip
// (STORE, selectivo) → webp 128px en public/icons/. Manifiesto src/data/icons.json.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import sharp from 'sharp';

const SITE = path.resolve(import.meta.dirname, '..', '..');
const ZIP = '/tmp/scum-textures-full.zip';
const INDEX = '/tmp/tex/_icons_index.json';
const ES_ROOT = '/tmp/scum-data';
const EXTRACT = '/tmp/tex-pngs';
const OUT = path.join(SITE, 'public', 'icons');
const norm = (a) => a.split('/').pop().split('.')[0].replace(/_C$/, '').replace(/_ES$/, '').toLowerCase();

const icons = JSON.parse(fs.readFileSync(INDEX, 'utf8'));
const items = JSON.parse(fs.readFileSync(path.join(SITE, 'src', 'data', 'items.json'), 'utf8'));

function walk(d, out = []) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p, out); else if (e.name.endsWith('_ES.json')) out.push(p); } return out; }
const esIcon = {};
for (const fp of walk(ES_ROOT)) {
  let d; try { d = JSON.parse(fs.readFileSync(fp, 'utf8')); } catch { continue; }
  const o = Array.isArray(d) ? d.find((x) => x && x.Properties && x.Properties.GridInventoryIcon) : null;
  const ap = o && o.Properties.GridInventoryIcon && o.Properties.GridInventoryIcon.AssetPathName;
  if (ap) esIcon[norm(path.basename(fp).replace(/_ES\.json$/, ''))] = ap.split('.').pop();
}

// item -> ruta zip
const jobs = []; const zipPaths = new Set();
for (const it of items) {
  const obj = esIcon[norm(it.asset)];
  const zp = obj && icons[obj];
  if (!zp) continue;
  jobs.push({ slug: it.slug, zp });
  zipPaths.add(zp);
}
console.error(`items con icono: ${jobs.length} | PNG distintos a extraer: ${zipPaths.size}`);

// extraer del zip (en lotes para no pasar ARG_MAX)
fs.rmSync(EXTRACT, { recursive: true, force: true });
fs.mkdirSync(EXTRACT, { recursive: true });
const all = [...zipPaths];
for (let i = 0; i < all.length; i += 400) {
  execFileSync('unzip', ['-o', '-q', ZIP, ...all.slice(i, i + 400), '-d', EXTRACT], { stdio: 'ignore' });
}

// convertir a webp 128px
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const have = []; let fail = 0;
const tasks = jobs.map(({ slug, zp }) => {
  const src = path.join(EXTRACT, zp);
  if (!fs.existsSync(src)) { fail++; return null; }
  have.push(slug);
  return sharp(src).resize(128, 128, { fit: 'inside', withoutEnlargement: true }).webp({ quality: 80 })
    .toFile(path.join(OUT, `${slug}.webp`)).catch((e) => { fail++; console.error('FAIL', slug, e.message); });
}).filter(Boolean);
await Promise.all(tasks);

have.sort();
fs.writeFileSync(path.join(SITE, 'src', 'data', 'icons.json'), JSON.stringify(have));
const bytes = have.reduce((s, sl) => { try { return s + fs.statSync(path.join(OUT, `${sl}.webp`)).size; } catch { return s; } }, 0);
console.error(`iconos escritos: ${have.length} | fallos: ${fail} | tamaño: ${(bytes / 1024 / 1024).toFixed(1)} MB`);
