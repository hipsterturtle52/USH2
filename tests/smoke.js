// Headless smoke test: drives the real UI through every view.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const page = await browser.newPage({ viewport: { width: 390, height: 800 } });
  const errs = [];
  page.on('pageerror', e => errs.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  page.on('dialog', d => d.accept());
  const url = 'file://' + path.resolve(__dirname, '../clep-us-history-ii-study-guide.html');
  await page.goto(url);
  for (const h of ['#/', '#/units', '#/unit/1', '#/unit/1/must', '#/unit/1/timeline', '#/unit/1/cards', '#/cards', '#/mistakes', '#/exams', '#/cheatsheet', '#/plan', '#/about']) {
    await page.goto(url + h); await page.waitForTimeout(50);
    const t = await page.textContent('main'); if (!t || t.length < 50) errs.push('empty view ' + h);
  }
  // diagnostic via keyboard
  await page.goto(url + '#/diagnostic'); await page.keyboard.press('Enter');
  let n = 0; while (n < 200 && await page.$('#nx')) { await page.keyboard.press(String(1 + (n % 5))); await page.keyboard.press('Enter'); n++; }
  console.log('diagnostic answered', n, '|', (await page.textContent('main')).slice(0, 60));
  // unit quiz
  await page.goto(url + '#/unit/1/quiz'); await page.keyboard.press('Enter');
  n = 0; while (n < 200 && await page.$('#nx')) { await page.keyboard.press('1'); await page.keyboard.press('Enter'); n++; }
  console.log('quiz answered', n, '|', (await page.textContent('main')).slice(0, 60));
  // flashcards
  await page.goto(url + '#/cards'); for (let i = 0; i < 6; i++) { await page.keyboard.press(' '); await page.keyboard.press(i % 2 ? '1' : '2'); }
  // exam A: answer everything with key 3, submit on last
  await page.goto(url + '#/exam/A'); await page.click('#go');
  n = 0; while (n < 300 && await page.$('#nx')) { await page.keyboard.press('3'); await page.keyboard.press('Enter'); n++; }
  await page.keyboard.press('3'); await page.click('#sb'); await page.waitForTimeout(100);
  console.log('exam answered', n + 1, '|', (await page.textContent('main')).slice(0, 80));
  await page.goto(url + '#/plan'); await page.fill('#pd', '2026-11-20'); await page.click('#gen');
  console.log('plan rows', await page.$$eval('#planOut tr', r => r.length));
  await page.goto(url + '#/'); console.log('home |', (await page.textContent('main')).replace(/\s+/g, ' ').slice(0, 300));
  const st = await page.evaluate(() => localStorage.getItem('clep-ush2-v1'));
  console.log('state bytes', st.length, 'mistakes', Object.keys(JSON.parse(st).mistakes).length);
  // dark mode + blocked storage
  await page.click('#themeBtn');
  const ctx2 = await browser.newContext(); const p2 = await ctx2.newPage();
  await p2.addInitScript(() => { Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } }); });
  p2.on('pageerror', e => errs.push('blocked-storage pageerror: ' + e.message));
  await p2.goto(url); console.log('blocked storage banner:', !!(await p2.textContent('main')).match(/blocking storage/));
  await page.screenshot({ path: process.argv[2] || '/tmp/shot.png', fullPage: false });
  console.log(errs.length ? 'ERRORS:\n' + errs.join('\n') : 'NO JS ERRORS');
  await browser.close();
})();
