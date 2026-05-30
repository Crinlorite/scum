// Resuelve los placeholders $$Mapping_X$$ del códice a su tecla por defecto
// (DefaultInput.ini del juego). Salida: keybinds.json { Name: {es, en} }.
import fs from 'node:fs';
import path from 'node:path';
const HERE = path.resolve(import.meta.dirname);
const ini = fs.readFileSync(path.join(HERE, 'DefaultInput.ini'), 'utf8');
const codex = JSON.parse(fs.readFileSync(path.join(HERE, '..', '..', 'src', 'data', 'codex.json'), 'utf8'));

const actions = {};
for (const m of ini.matchAll(/\+ActionMappings=\(ActionName="([^"]+)"([^)]*)\)/g)) {
  const key = (m[2].match(/Key=([A-Za-z0-9_]+)/) || [])[1];
  const mods = ['bShift', 'bCtrl', 'bAlt'].filter((x) => new RegExp(x + '=True').test(m[2])).map((x) => x.slice(1));
  if (key && !(m[1] in actions)) actions[m[1]] = { key, mods };
}
const axes = {};
for (const m of ini.matchAll(/\+AxisMappings=\(AxisName="([^"]+)"([^)]*)\)/g)) {
  const key = (m[2].match(/Key=([A-Za-z0-9_]+)/) || [])[1];
  const scale = parseFloat((m[2].match(/Scale=(-?[0-9.]+)/) || [])[1] || '0');
  (axes[m[1]] ??= []).push({ key, scale });
}
const axisKey = (re, sign) => { for (const [n, arr] of Object.entries(axes)) if (re.test(n)) { const h = arr.find((a) => Math.sign(a.scale) === sign); if (h) return h.key; } return null; };
const MOVE = {
  MoveForward: () => axisKey(/MoveForwardOrBackward/, 1), MoveBackward: () => axisKey(/MoveForwardOrBackward/, -1),
  MoveRight: () => axisKey(/MoveLeftOrRight/, 1), MoveLeft: () => axisKey(/MoveLeftOrRight/, -1),
  DiveUp: () => axisKey(/DiveUpOrDown/, 1), DiveDown: () => axisKey(/DiveUpOrDown/, -1),
};
const SPECIAL = { ReelingIn: { es: 'Rueda ↑', en: 'Scroll up' }, ReelingOut: { es: 'Rueda ↓', en: 'Scroll down' } };

const DISP = {
  LeftMouseButton: ['Clic izq.', 'Left click'], RightMouseButton: ['Clic der.', 'Right click'], MiddleMouseButton: ['Clic central', 'Middle click'],
  MouseScrollUp: ['Rueda ↑', 'Scroll up'], MouseScrollDown: ['Rueda ↓', 'Scroll down'], MouseWheelAxis: ['Rueda', 'Wheel'],
  SpaceBar: ['Espacio', 'Space'], Enter: ['Intro', 'Enter'], Tab: ['Tab', 'Tab'], BackSpace: ['Retroceso', 'Backspace'],
  Up: ['↑', '↑'], Down: ['↓', '↓'], Left: ['←', '←'], Right: ['→', '→'],
  LeftShift: ['Mayús', 'Shift'], RightShift: ['Mayús', 'Shift'], LeftControl: ['Ctrl', 'Ctrl'], RightControl: ['Ctrl', 'Ctrl'],
  LeftAlt: ['Alt', 'Alt'], RightAlt: ['Alt', 'Alt'],
  One: ['1', '1'], Two: ['2', '2'], Three: ['3', '3'], Four: ['4', '4'], Five: ['5', '5'], Six: ['6', '6'],
};
const MOD = { Shift: ['Mayús', 'Shift'], Ctrl: ['Ctrl', 'Ctrl'], Alt: ['Alt', 'Alt'] };
const disp = (key, mods, lang) => (mods || []).map((mm) => (MOD[mm] ? MOD[mm][lang === 'es' ? 0 : 1] : mm)).concat([DISP[key] ? DISP[key][lang === 'es' ? 0 : 1] : key]).join(' + ');

// Resuelve TODOS los Mapping_* del ini (no solo los del códice) → robusto y reutilizable.
const out = {};
for (const name of Object.keys(actions)) {
  if (!name.startsWith('Mapping_')) continue;
  const p = name.slice(8);
  out[p] = { es: disp(actions[name].key, actions[name].mods, 'es'), en: disp(actions[name].key, actions[name].mods, 'en') };
}
for (const p of Object.keys(MOVE)) { const k = MOVE[p](); if (k) out[p] = { es: disp(k, [], 'es'), en: disp(k, [], 'en') }; }
for (const [p, v] of Object.entries(SPECIAL)) out[p] = v;
fs.writeFileSync(path.join(HERE, 'keybinds.json'), JSON.stringify(out, null, 1));

// Cobertura sobre el códice (informativo).
const used = new Set();
for (const e of codex) for (const b of e.blocks) { const t = b.text ? Object.values(b.text).join(' ') : ''; for (const m of t.matchAll(/\$\$Mapping_([A-Za-z0-9_]+)\$\$/g)) used.add(m[1]); }
const missing = [...used].filter((p) => !out[p]);
console.error(`keybinds.json: ${Object.keys(out).length} mappings resueltos | usados en códice: ${used.size} | sin resolver del códice: ${missing.join(', ') || 'ninguno'}`);
