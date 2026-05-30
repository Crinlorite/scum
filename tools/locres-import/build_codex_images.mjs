#!/usr/bin/env node
// Ilustraciones del manual (Codex): extrae del zip de texturas las imágenes que
// referencian los artículos (bloques type=image) → webp (máx 800px ancho) en
// public/manual-img/. Manifiesto src/data/codex_images.json.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import sharp from 'sharp';

const SITE = path.resolve(import.meta.dirname, '..', '..');
const ZIP = '/tmp/scum-textures-full.zip';
const icons = JSON.parse(fs.readFileSync('/tmp/tex/_icons_index.json', 'utf8'));
const codex = JSON.parse(fs.readFileSync(path.join(SITE, 'src', 'data', 'codex.json'), 'utf8'));
const EXTRACT = '/tmp/codex-pngs';
const OUT = path.join(SITE, 'public', 'manual-img');

const imgs = new Set();
for (const e of codex) for (const b of e.blocks) if (b.t === 'image' && b.img && icons[b.img]) imgs.add(b.img);
const list = [...imgs];
console.error(`imágenes del códice a procesar: ${list.length}`);

fs.rmSync(EXTRACT, { recursive: true, force: true });
fs.mkdirSync(EXTRACT, { recursive: true });
const zipPaths = list.map((im) => icons[im]);
for (let i = 0; i < zipPaths.length; i += 400) {
  execFileSync('unzip', ['-o', '-q', ZIP, ...zipPaths.slice(i, i + 400), '-d', EXTRACT], { stdio: 'ignore' });
}

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const have = []; let fail = 0;
await Promise.all(list.map((im) => {
  const src = path.join(EXTRACT, icons[im]);
  if (!fs.existsSync(src)) { fail++; return null; }
  have.push(im);
  return sharp(src).resize(800, null, { fit: 'inside', withoutEnlargement: true }).webp({ quality: 80 })
    .toFile(path.join(OUT, `${im}.webp`)).catch((e) => { fail++; console.error('FAIL', im, e.message); });
}).filter(Boolean));

have.sort();
fs.writeFileSync(path.join(SITE, 'src', 'data', 'codex_images.json'), JSON.stringify(have));
const bytes = have.reduce((s, im) => { try { return s + fs.statSync(path.join(OUT, `${im}.webp`)).size; } catch { return s; } }, 0);
console.error(`imágenes escritas: ${have.length} | fallos: ${fail} | tamaño: ${(bytes / 1024 / 1024).toFixed(1)} MB`);
