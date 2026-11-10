// Renders posts.html -> out/post-N.png (1080x1350) and grid.html -> out/grid.png
// Usage: node aisance-instagram/render.js
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const dir = __dirname;
  const browser = await chromium.launch();

  const page = await browser.newPage({ viewport: { width: 1200, height: 1500 } });
  await page.goto('file://' + path.join(dir, 'posts.html'));
  await page.evaluate(() => document.fonts.ready);
  for (const n of [1, 2, 3]) {
    await page.locator('#p' + n).screenshot({ path: path.join(dir, 'out', `post-${n}.png`) });
  }

  const grid = await browser.newPage({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 3 });
  await grid.goto('file://' + path.join(dir, 'grid.html'));
  await grid.evaluate(() => document.fonts.ready);
  await grid.screenshot({ path: path.join(dir, 'out', 'grid.png'), fullPage: true });

  await browser.close();
})();
