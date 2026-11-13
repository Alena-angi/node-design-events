// node render.js <page.html> <name>  -> out/<name>.png and out/<name>-notext.png (1080x1350 @2x)
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const [page, name] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, page)); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(__dirname, 'out', name + '.png') });
  await p.evaluate(() => document.body.classList.add('notext'));
  await p.screenshot({ path: path.join(__dirname, 'out', name + '-notext.png') }); await b.close();
})();
