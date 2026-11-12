// node render_gen.js <photo.png> <out-name>  -> out/<name>.png (1080x1350 @2x)
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const [photo, name] = process.argv.slice(2);
  const html = fs.readFileSync(path.join(__dirname, 'hand-gen.html'), 'utf8').replace('PHOTO', path.basename(photo));
  const tmp = path.join(__dirname, 'out', '_page.html'); fs.writeFileSync(tmp, html.replace(/\.\.\/fonts\//g, '../../fonts/'));
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 2 });
  await p.goto('file://' + tmp); await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: path.join(__dirname, 'out', name + '.png') }); await b.close(); fs.unlinkSync(tmp);
})();
