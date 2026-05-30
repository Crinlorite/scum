// Sección Controles: lista de acciones del juego + tecla por defecto, por categoría.
// Fuente: DefaultInput.ini (ActionMappings teclado/ratón + AxisMappings de movimiento).
import fs from 'node:fs';
import path from 'node:path';
const HERE = path.resolve(import.meta.dirname);
const ini = fs.readFileSync(path.join(HERE, 'DefaultInput.ini'), 'utf8');

const DISP = {
  LeftMouseButton: ['Clic izq.', 'Left click'], RightMouseButton: ['Clic der.', 'Right click'], MiddleMouseButton: ['Clic central', 'Middle click'],
  MouseScrollUp: ['Rueda ↑', 'Scroll up'], MouseScrollDown: ['Rueda ↓', 'Scroll down'], MouseWheelAxis: ['Rueda', 'Wheel'],
  SpaceBar: ['Espacio', 'Space'], Enter: ['Intro', 'Enter'], Tab: ['Tab', 'Tab'], BackSpace: ['Retroceso', 'Backspace'],
  Up: ['↑', '↑'], Down: ['↓', '↓'], Left: ['←', '←'], Right: ['→', '→'], Escape: ['Esc', 'Esc'],
  LeftShift: ['Mayús', 'Shift'], RightShift: ['Mayús', 'Shift'], LeftControl: ['Ctrl', 'Ctrl'], RightControl: ['Ctrl', 'Ctrl'],
  LeftAlt: ['Alt', 'Alt'], RightAlt: ['Alt', 'Alt'],
  One: ['1', '1'], Two: ['2', '2'], Three: ['3', '3'], Four: ['4', '4'], Five: ['5', '5'], Six: ['6', '6'], Seven: ['7', '7'], Eight: ['8', '8'], Nine: ['9', '9'], Zero: ['0', '0'],
};
const MOD = { Shift: ['Mayús', 'Shift'], Ctrl: ['Ctrl', 'Ctrl'], Alt: ['Alt', 'Alt'] };
const lab = (key, mods, lang) => (mods || []).map((mm) => (MOD[mm] ? MOD[mm][lang === 'es' ? 0 : 1] : mm)).concat([DISP[key] ? DISP[key][lang === 'es' ? 0 : 1] : key]).join(' + ');
const pretty = (n) => n.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/_/g, ' ').replace(/\bTab\b/g, 'menú').trim();

const CATS = [
  ['music', /Music|Octave|^Play[A-G]|Instrument|Pluck|Strum/],
  ['emotes', /FingerGun|FrackYou|GetDown|GetUp|Halt|Heart|HurryUp|Laughing|Point|Salute|Wave|Kick|Cheer|Clap|Dance|Facepalm|Freeze|Emote|Gesture|Surrender|Taunt/],
  ['movement', /Move|Lean|Crouch|Prone|Jump|Dive|Pace|AutoWalk|Sprint|Climb|Swim|Parachute|Grapple/],
  ['combat', /Weapon|Fire|Reload|Aim|Bash|Block|Charge|Bayonet|Throw|Ammo|FiringMode|Melee|Punch|Ball|Grenade|HoldBreath|CombatMode|NextTarget|Holster/],
  ['fishing', /Cast|Reel|Rod|Fish|Bait/],
  ['vehicle', /Airplane|Vehicle|Steer|Throttle|Brake|Engine|Boat|Sail|\bRoll\b|Gear|Horn|Mount|Pedal|Clutch|Wheel(?!Axis)|Anchor|Flaps|Rudder|Handbrake/],
  ['minigame', /Minigame|DialLock|Lockpicking|ATM|DialPad|NoticeBoard|VirtualMouse/],
  ['building', /Placing|Building|Snap|RotatePlacing|WireCutters|Deploy/],
  ['interface', /OpenTab|Chat|\bMap\b|Camera|PhotoMode|Spectator|Scope|Zoom|Brightness|CopyLocation|Exit|Inventory|QuickAccess|Favor|CraftLast|Paste|QuestBook|Flip/],
  ['view', /Focus|FreeLook|ChangeCamera|Interact/],
];
const catOf = (n) => (CATS.find(([, re]) => re.test(n)) || ['other'])[0];

// ActionMappings teclado/ratón (no gamepad), 1 por nombre (prefiere la 1ª = teclado).
const seen = new Set(); const rows = [];
for (const m of ini.matchAll(/\+ActionMappings=\(ActionName="Mapping_([^"]+)"([^)]*)\)/g)) {
  const name = m[1], rest = m[2];
  const key = (rest.match(/Key=([A-Za-z0-9_]+)/) || [])[1];
  if (!key || /^Gamepad/i.test(key) || seen.has(name)) continue;
  seen.add(name);
  const mods = ['bShift', 'bCtrl', 'bAlt'].filter((x) => new RegExp(x + '=True').test(rest)).map((x) => x.slice(1));
  rows.push({ cat: catOf(name), action: pretty(name), key: { es: lab(key, mods, 'es'), en: lab(key, mods, 'en') } });
}
// movimiento por ejes
const AX = [['Move Forward', /MoveForwardOrBackward/, 1], ['Move Backward', /MoveForwardOrBackward/, -1], ['Move Right', /MoveLeftOrRight/, 1], ['Move Left', /MoveLeftOrRight/, -1]];
for (const [label, re, sign] of AX) {
  for (const a of ini.matchAll(/\+AxisMappings=\(AxisName="([^"]+)"([^)]*)\)/g)) {
    if (!re.test(a[1])) continue;
    const key = (a[2].match(/Key=([A-Za-z0-9_]+)/) || [])[1];
    const sc = parseFloat((a[2].match(/Scale=(-?[0-9.]+)/) || [])[1] || '0');
    if (key && !/^Gamepad/i.test(key) && Math.sign(sc) === sign) { rows.push({ cat: 'movement', action: label, key: { es: DISP[key] ? DISP[key][0] : key, en: DISP[key] ? DISP[key][1] : key } }); break; }
  }
}
rows.sort((a, b) => a.cat.localeCompare(b.cat) || a.action.localeCompare(b.action));
fs.writeFileSync(path.join(HERE, '..', '..', 'src', 'data', 'controls.json'), JSON.stringify(rows));
const byCat = {}; for (const r of rows) byCat[r.cat] = (byCat[r.cat] || 0) + 1;
console.error(`controls.json: ${rows.length} controles | por categoría: ${JSON.stringify(byCat)}`);
