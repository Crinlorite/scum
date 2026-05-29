#!/usr/bin/env node
// Maps each item to its official inventory icon and emits optimized webp icons.
//  - icon ref: <Item>_ES.json → Properties.GridInventoryIcon.AssetPathName
//  - PNG path: object name → /tmp/scum-icons/_icons_index.json
//  - output:   public/icons/<slug>.webp (128px) + src/data/icons.json (slug list)
// The icon export is partial (only ~941 of the referenced icons were dumped),
// so only items with an exact, real match get an icon — no guessing.
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

const SITE = path.resolve(import.meta.dirname, '..', '..');
const ES_ROOT = '/tmp/scum-data';
const ICONS_ROOT = '/tmp/scum-icons';
const OUT_DIR = path.join(SITE, 'public', 'icons');
const MANIFEST = path.join(SITE, 'src', 'data', 'icons.json');
const SIZE = 128;

const icons = JSON.parse(fs.readFileSync(path.join(ICONS_ROOT, '_icons_index.json'), 'utf8'));
const items = JSON.parse(fs.readFileSync(path.join(SITE, 'src', 'data', 'items.json'), 'utf8'));
const norm = (a) => a.split('/').pop().split('.')[0].replace(/_C$/, '').replace(/_ES$/, '').toLowerCase();

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('_ES.json')) out.push(p);
  }
  return out;
}

// norm(item base) -> icon object name
const esIcon = {};
for (const fp of walk(ES_ROOT)) {
  let d;
  try { d = JSON.parse(fs.readFileSync(fp, 'utf8')); } catch { continue; }
  const o = Array.isArray(d) ? d.find((x) => x && x.Properties && x.Properties.GridInventoryIcon) : null;
  const ap = o && o.Properties.GridInventoryIcon && o.Properties.GridInventoryIcon.AssetPathName;
  if (ap) esIcon[norm(path.basename(fp).replace(/_ES\.json$/, ''))] = ap.split('.').pop();
}

fs.rmSync(OUT_DIR, { recursive: true, force: true });
fs.mkdirSync(OUT_DIR, { recursive: true });

const have = [];
let missEs = 0, missPng = 0, failed = 0;
const jobs = [];
for (const it of items) {
  const obj = esIcon[norm(it.asset)];
  if (!obj) { missEs++; continue; }
  const rel = icons[obj];
  if (!rel) { missPng++; continue; }
  const src = path.join(ICONS_ROOT, rel);
  if (!fs.existsSync(src)) { missPng++; continue; }
  have.push(it.slug);
  jobs.push(
    sharp(src)
      .resize(SIZE, SIZE, { fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 80 })
      .toFile(path.join(OUT_DIR, `${it.slug}.webp`))
      .catch((e) => { failed++; console.error('FAIL', it.slug, e.message); })
  );
}
await Promise.all(jobs);

have.sort();
fs.writeFileSync(MANIFEST, JSON.stringify(have));
const bytes = have.reduce((s, sl) => { try { return s + fs.statSync(path.join(OUT_DIR, `${sl}.webp`)).size; } catch { return s; } }, 0);
console.error(`iconos escritos: ${have.length}  | sin _ES: ${missEs}  | sin PNG: ${missPng}  | fallos: ${failed}`);
console.error(`tamaño total: ${(bytes / 1024 / 1024).toFixed(2)} MB  → public/icons/  | manifest: src/data/icons.json`);
