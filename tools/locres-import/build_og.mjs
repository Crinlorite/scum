import sharp from 'sharp';
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0f1311"/><stop offset="1" stop-color="#171d19"/>
    </linearGradient>
    <radialGradient id="glow" cx="18%" cy="12%" r="60%">
      <stop offset="0" stop-color="#b04a2a" stop-opacity="0.35"/><stop offset="1" stop-color="#b04a2a" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <rect x="64" y="70" width="72" height="72" rx="10" fill="none" stroke="#e0843f" stroke-width="3"/>
  <text x="100" y="120" font-family="Georgia, 'DejaVu Serif', serif" font-size="34" font-weight="700" fill="#e0843f" text-anchor="middle">SC</text>
  <text x="160" y="120" font-family="Georgia, 'DejaVu Serif', serif" font-size="40" font-weight="700" fill="#e8e3d8">SCUM Codex</text>
  <text x="64" y="300" font-family="Georgia, 'DejaVu Serif', serif" font-size="76" font-weight="700" fill="#e8e3d8">Wiki, ítems, mapa</text>
  <text x="64" y="386" font-family="Georgia, 'DejaVu Serif', serif" font-size="76" font-weight="700" fill="#e8e3d8">y manual del juego</text>
  <text x="66" y="452" font-family="Arial, 'DejaVu Sans', sans-serif" font-size="29" fill="#b9c0b6">Datos extraídos directamente del juego — no inventados.</text>
  <g font-family="Arial, 'DejaVu Sans', sans-serif" font-size="26" fill="#e0843f" font-weight="700">
    <text x="64" y="556">1983 ítems</text>
    <text x="300" y="556" fill="#9aa0a6">·</text>
    <text x="324" y="556">10 idiomas</text>
    <text x="540" y="556" fill="#9aa0a6">·</text>
    <text x="564" y="556">mapa en vivo</text>
    <text x="812" y="556" fill="#9aa0a6">·</text>
    <text x="836" y="556">37 guías</text>
  </g>
  <text x="1136" y="556" font-family="Arial,'DejaVu Sans',sans-serif" font-size="24" fill="#9aa0a6" text-anchor="end">scumcodex.com</text>
  <rect x="0" y="618" width="1200" height="12" fill="#b04a2a"/>
</svg>`;
await sharp(Buffer.from(svg)).png().toFile('public/og.png');
console.log('og.png generado:', (await sharp('public/og.png').metadata()).width + 'x' + (await sharp('public/og.png').metadata()).height);
