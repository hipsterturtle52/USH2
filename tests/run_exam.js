// End-to-end audit: drives the real UI with the keyboard, using the answer key to verify scoring.
const { chromium } = require('playwright');
const path = require('path');
const url = 'file://' + path.resolve(__dirname, '../clep-us-history-ii-study-guide.html');
const fails = [];
const check = (cond, msg) => { if (!cond) fails.push(msg); console.log((cond ? '  PASS ' : '  FAIL ') + msg); };

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  page.on('pageerror', e => fails.push('JS error: ' + e.message));
  page.on('dialog', d => d.accept());
  await page.goto(url);
  // key of the currently displayed question (matched on stimulus + stem + options)
  const currentKey = () => page.evaluate(() => {
    const stem = document.querySelector('.stem').innerHTML;
    const st = document.querySelector('.stim') ? document.querySelector('.stim').innerHTML : '';
    const opts = [...document.querySelectorAll('.opt')].map(b => b.querySelectorAll('span')[1].innerHTML.replace(/<span class="ex">.*$/s, ''));
    const q = QS.find(q => q.s === stem && q.st === st && q.o.every((o, i) => o === opts[i]));
    return q ? { a: q.a, id: q.id, pool: q.pool, u: q.u } : null;
  });

  console.log('DIAGNOSTIC (answer all 30 correctly with keys 1-5 + Enter)');
  await page.goto(url + '#/diagnostic'); await page.keyboard.press('Enter');
  let n = 0; const seenDiag = new Set();
  while (await page.$('#nx')) {
    const k = await currentKey(); if (!k) { fails.push('diag: could not match question ' + n); break; }
    seenDiag.add(k.id); check(k.pool === 'diag', `diag Q${n + 1} (${k.id}) comes from the diagnostic pool`) || 0;
    await page.keyboard.press(String(k.a + 1)); await page.keyboard.press('Enter'); n++;
  }
  const diagText = await page.textContent('main');
  check(n === 30 && /30 \/ 30/.test(diagText), `diagnostic scored 30/30 over ${n} questions`);
  check(seenDiag.size === 30, 'diagnostic had 30 distinct questions');
  const units = await page.evaluate(() => Object.keys(S.diag.byUnit).length);
  check(units === 10, `diagnostic covered ${units}/10 units`);
  check((await page.$$('.pill.good')).length >= 10, 'every unit marked "Skim" after a perfect diagnostic');

  console.log('UNIT QUIZ (explanations shown for all 5 options after answering)');
  await page.goto(url + '#/unit/5/quiz'); await page.keyboard.press('Enter');
  const k1 = await currentKey(); await page.keyboard.press(String(((k1.a + 1) % 5) + 1)); // answer wrong on purpose
  check((await page.$$('.opt .ex')).length === 5, 'all 5 options show an explanation after answering');
  check((await page.$$('.opt.right')).length === 1 && (await page.$$('.opt.wrong')).length === 1, 'right answer and chosen wrong answer are both marked');
  check(await page.evaluate(id => !!S.mistakes[id], k1.id), 'missed question was added to the mistake log');

  console.log('PRACTICE EXAM 1 (120 Q, miss exactly 10 on purpose)');
  await page.goto(url + '#/exam/A'); await page.click('#go');
  const t0 = await page.textContent('#tm');
  check(/^(90:00|89:5\d)$/.test(t0.trim()), `timer starts at 90:00 (shows ${t0.trim()})`);
  // no pausing: reload mid-exam and confirm clock kept running from the original start time
  await page.waitForTimeout(2100); await page.reload(); await page.goto(url + '#/exam/A'); await page.waitForTimeout(1100);
  const t1 = (await page.textContent('#tm')).trim();
  check(t1 <= '89:58' && t1 >= '89:50', `timer kept running across a reload (now ${t1})`);
  const seenA = new Set(); let missed = 0;
  for (let i = 0; i < 120; i++) {
    const k = await currentKey(); if (!k) { fails.push('exam A: unmatched question ' + i); break; }
    if (k.pool !== 'A') fails.push(`exam A served ${k.id} from pool ${k.pool}`);
    seenA.add(k.id);
    const ans = missed < 10 ? (k.a + 1) % 5 : k.a; if (missed < 10) missed++;
    await page.keyboard.press(String(ans + 1));
    if (i < 119) await page.keyboard.press('Enter');
  }
  await page.click('#sb'); await page.waitForTimeout(150);
  const resA = await page.textContent('main');
  check(seenA.size === 120, `exam 1 served 120 distinct questions (${seenA.size})`);
  check(/92%/.test(resA) && /110 \/ 120/.test(resA), 'exam 1 scored 110/120 = 92%');
  const rows = await page.$$eval('table', ts => ts.map(t => t.querySelectorAll('tbody tr').length));
  check(rows[0] === 10 && rows[1] === 5 && rows[2] === 2, `results broken down by 10 units, 5 themes, 2 periods (${rows.slice(0, 3)})`);

  console.log('PRACTICE EXAM 2 (first fail, then pass) + READINESS RULE');
  const runB = async (correct) => {
    await page.goto(url + '#/exam/B'); await page.click('#go'); const ids = new Set();
    for (let i = 0; i < 120; i++) {
      const k = await currentKey(); ids.add(k.id);
      await page.keyboard.press(String((correct ? k.a : (k.a + 1) % 5) + 1)); if (i < 119) await page.keyboard.press('Enter');
    }
    await page.click('#sb'); await page.waitForTimeout(150); return ids;
  };
  const idsB = await runB(false);
  const overlap = [...idsB].filter(x => seenA.has(x) || seenDiag.has(x)).length;
  check(overlap === 0, `exam 2 shares no questions with exam 1 or the diagnostic (${overlap} overlaps)`);
  const quizOverlap = await page.evaluate(ids => ids.filter(id => QMAP[id].pool === 'quiz').length, [...idsB, ...seenA]);
  check(quizOverlap === 0, 'neither exam repeats unit-quiz questions');
  await page.goto(url + '#/'); check(/Not ready yet/.test(await page.textContent('main')), 'readiness = "Not ready" with exam 2 at 0%');
  await runB(true);
  await page.goto(url + '#/'); check(/Ready to book/.test(await page.textContent('main')), 'readiness = "Ready to book" once both exams ≥ 75%');

  console.log('MISTAKE LOG + FLASHCARDS + PLAN + EXPORT');
  const open = await page.evaluate(() => openMistakes().length);
  check(open >= 11, `mistake log holds the misses (${open})`);
  await page.goto(url + '#/mistakes'); await page.click('#go');
  for (let i = 0; i < open; i++) { const k = await currentKey(); await page.keyboard.press(String(k.a + 1)); await page.keyboard.press('Enter'); }
  check(await page.evaluate(() => openMistakes().length) === 0, 'drilling mistakes correctly clears the log');
  await page.goto(url + '#/cards');
  await page.keyboard.press(' '); await page.keyboard.press('1'); await page.keyboard.press(' '); await page.keyboard.press('2');
  const cs = await page.evaluate(() => Object.values(S.cards));
  check(cs.some(c => c.box === 1 && c.lastMiss) && cs.some(c => c.box === 1 && !c.lastMiss), 'Leitner: missed card → box 1 (flagged), known card → box 1+ scheduled');
  await page.selectOption('#fm', 'missed'); check(/left in session/.test(await page.textContent('#fcwrap')), '"review missed only" mode serves the missed card');
  await page.goto(url + '#/plan'); await page.fill('#pd', '2026-11-05'); await page.click('#gen');
  const planRows = await page.$$eval('#planOut tbody tr', r => r.map(x => x.textContent));
  check(/Practice Exam 1/.test(planRows[planRows.length - 3]) && /Practice Exam 2/.test(planRows[planRows.length - 2]) && /EXAM DAY/.test(planRows[planRows.length - 1]), 'study plan ends with Exam 1, Exam 2, then exam day');
  await page.goto(url + '#/about');
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#exp')]);
  const p = await dl.path(); const exported = JSON.parse(require('fs').readFileSync(p, 'utf8'));
  check(exported.v === 1 && exported.exams.A && exported.exams.B, 'export produces a valid progress JSON');

  console.log(fails.length ? `\n${fails.length} FAILURE(S):\n - ` + fails.join('\n - ') : '\nALL END-TO-END CHECKS PASSED');
  await browser.close(); process.exit(fails.length ? 1 : 0);
})();
