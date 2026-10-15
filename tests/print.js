const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const p = await b.newPage(); const url = 'file://' + path.resolve(__dirname, '../clep-us-history-ii-study-guide.html');
  await p.goto(url + '#/cheatsheet'); await p.waitForTimeout(200);
  const out = process.argv[2];
  await p.pdf({ path: out + '/cheat.pdf', format: 'Letter', printBackground: false });
  await p.emulateMedia({ media: 'print' }); await p.setViewportSize({ width: 816, height: 1056 });
  await p.screenshot({ path: out + '/cheat.png', fullPage: true });
  await b.close();
})();
