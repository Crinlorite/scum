#!/usr/bin/env node
// Skill icons from the Codex visuals (Manual/Codex/Visuals/AttributesAndSkills/),
// which DID come in scum-icons.zip. Match skill slug → {ATTR}_{Skill} icon.
// Output: public/icons/skills/<slug>.webp + src/data/skill_icons.json.
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

const SITE = path.resolve(import.meta.dirname, '..', '..');
const ICONS_ROOT = '/tmp/scum-icons';
const OUT = path.join(SITE, 'public', 'icons', 'skills');
const icons = JSON.parse(fs.readFileSync(path.join(ICONS_ROOT, '_icons_index.json'), 'utf8'));
const skills = JSON.parse(fs.readFileSync(path.join(SITE, 'src', 'data', 'skills.json'), 'utf8'));
const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

const bySuffix = {};
for (const k of Object.keys(icons)) {
  if (!/AttributesAndSkills/i.test(icons[k]) || /_Intro/i.test(k)) continue;
  bySuffix[norm(k.split('_').slice(1).join(''))] = k;
}
const ALIAS = { camouflage: 'camo', boxing: 'brawling', rifles: 'rifling', handguns: 'handgun' };

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const have = [];
const jobs = [];
for (const s of skills) {
  const cand = [norm(s.slug), ALIAS[norm(s.slug)], norm(s.name?.en)].filter(Boolean);
  const key = cand.map((c) => bySuffix[c]).find(Boolean);
  if (!key) continue;
  const src = path.join(ICONS_ROOT, icons[key]);
  if (!fs.existsSync(src)) continue;
  have.push(s.slug);
  jobs.push(sharp(src).resize(128, 128, { fit: 'inside', withoutEnlargement: true }).webp({ quality: 82 })
    .toFile(path.join(OUT, `${s.slug}.webp`)).catch((e) => console.error('FAIL', s.slug, e.message)));
}
await Promise.all(jobs);
have.sort();
fs.writeFileSync(path.join(SITE, 'src', 'data', 'skill_icons.json'), JSON.stringify(have));
console.error(`iconos de skill: ${have.length}/${skills.length} → public/icons/skills/ | manifest skill_icons.json`);
