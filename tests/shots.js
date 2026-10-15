const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const out = process.argv[2]; const url = 'file://' + path.resolve(__dirname, '../clep-us-history-ii-study-guide.html');
  const m = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  await m.goto(url); console.log('total hours est:', await m.evaluate(() => totalHours().toFixed(1)), '| hours left fresh:', await m.evaluate(() => hoursLeft().toFixed(1)));
  await m.goto(url + '#/unit/8/quiz'); await m.keyboard.press('Enter'); await m.keyboard.press('2');
  await m.screenshot({ path: out + '/m-quiz.png' });
  await m.goto(url + '#/unit/2/lesson'); await m.evaluate(() => window.scrollTo(0, 900)); await m.screenshot({ path: out + '/m-lesson.png' });
  const d = await b.newPage({ viewport: { width: 1280, height: 860 }, colorScheme: 'dark' });
  await d.goto(url + '#/unit/3/timeline'); await d.screenshot({ path: out + '/d-timeline.png' });
  await d.goto(url + '#/exam/B'); await d.click('#go'); await d.keyboard.press('3'); await d.screenshot({ path: out + '/d-exam.png' });
  await b.close();
})();
