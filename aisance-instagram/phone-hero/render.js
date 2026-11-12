// node aisance-instagram/phone-hero/render.js  -> out/hero.png (1080x1350, @2x) + out/hero-layer.png (transparent, for Figma)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, 'hero.html'));
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: path.join(__dirname, 'out/hero.png') });
  await p.evaluate(() => document.body.classList.add('no-bg'));
  await p.screenshot({ path: path.join(__dirname, 'out/hero-layer.png'), omitBackground: true });
  await b.close();
})();
